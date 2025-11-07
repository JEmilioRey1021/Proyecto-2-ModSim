import math, random, time
from dataclasses import dataclass, field
import chess
from tb_utils import probe_wdl, wdl_to_score

C_PUCT = 2.5
ROLLOUT_MAX_PLIES = 30

@dataclass
class Node:
    board: chess.Board
    parent: 'Node|None' = None
    move: chess.Move|None = None
    children: dict = field(default_factory=dict)
    N: int = 0
    W: float = 0.0
    Q: float = 0.0
    depth: int = 0
    is_mate: bool = False  # Nueva bandera

    def is_terminal(self):
        return self.board.is_checkmate() or self.board.is_stalemate() or \
               self.board.is_insufficient_material() or self.board.halfmove_clock >= 100

def uct_value(child: 'Node', parent_N: int) -> float:
    """UCT con bonus enorme para mates y penalización por profundidad excesiva"""
    if child.N == 0:
        return float('inf')
    
    # Si es mate, darle prioridad máxima
    if child.is_mate:
        return float('inf') - child.depth  # Preferir mates más rápidos
    
    # Penalización por profundidad para evitar ciclos
    depth_penalty = child.depth * 0.05
    
    return child.Q + C_PUCT * math.sqrt(math.log(parent_N + 1) / child.N) - depth_penalty

def select(node: 'Node') -> tuple['Node', list[tuple[str, any]]]:
    """Selecciona el nodo hoja más prometedor"""
    debug_path = []
    cur = node
    
    while cur.children and not cur.is_terminal():
        uct_values = {
            move: uct_value(child, cur.N) 
            for move, child in cur.children.items()
        }
        
        best_move = max(uct_values.items(), key=lambda x: x[1])[0]
        best_child = cur.children[best_move]
        
        debug_path.append({
            'phase': 'select',
            'move': best_move.uci(),
            'N': best_child.N,
            'Q': round(best_child.Q, 3),
            'W': round(best_child.W, 2),
            'uct': round(uct_values[best_move], 3) if uct_values[best_move] != float('inf') else 'INF',
            'depth': best_child.depth,
            'is_mate': best_child.is_mate
        })
        
        cur = best_child
    
    return cur, debug_path

PRIOR_N = 10
PRIOR_W_MATE = 10000.0  # Aumentado dramáticamente
PRIOR_W_CHECK = 100.0
PRIOR_W_WIN = 5.0
PRIOR_W_DRAW = 0.5
PRIOR_W_LOSS = -5.0

def expand(node: 'Node', tb=None, root_turn=None) -> tuple['Node', dict]:
    """Expande con detección mejorada de mates"""
    debug_info = {'phase': 'expand', 'expanded': False}
    
    if node.is_terminal():
        return node, debug_info
    
    tried = set(node.children.keys())
    legal_moves = list(node.board.legal_moves)
    piece_values = {1: 1, 2: 3, 3: 3, 4: 5, 5: 9, 6: 0}
    
    # Primero: buscar mates inmediatos
    mate_moves = []
    for mv in legal_moves:
        if mv not in tried:
            nb = node.board.copy()
            nb.push(mv)
            if nb.is_checkmate():
                mate_moves.append(mv)
    
    # Si hay mates, expandir TODOS y retornar el primero
    if mate_moves:
        for mv in mate_moves:
            nb = node.board.copy()
            nb.push(mv)
            child = Node(nb, parent=node, move=mv, depth=node.depth + 1, is_mate=True)
            child.N = PRIOR_N * 10
            child.W = PRIOR_W_MATE * child.N
            child.Q = PRIOR_W_MATE
            node.children[mv] = child
        
        first_mate = mate_moves[0]
        debug_info.update({
            'expanded': True,
            'move': first_mate.uci(),
            'prior_Q': PRIOR_W_MATE,
            'depth': node.children[first_mate].depth,
            'is_mate': True,
            'total_mates_found': len(mate_moves)
        })
        return node.children[first_mate], debug_info
    
    def move_priority(mv):
        score = 0
        b = node.board
        moved_piece = b.piece_at(mv.from_square)
        moved_value = piece_values.get(moved_piece.piece_type if moved_piece else 0, 0)
        is_king = moved_piece and moved_piece.piece_type == chess.KING
        
        b.push(mv)
        is_check = b.is_check()
        
        if is_check:
            score += 200  # Aumentado
        
        if not b.is_checkmate() and is_piece_hanging(b, mv.to_square):
            score -= moved_value * 200
        
        b.pop()
        
        if b.is_capture(mv):
            captured = b.piece_at(mv.to_square)
            if captured:
                captured_value = piece_values.get(captured.piece_type, 0)
                score += captured_value * 30
                if captured_value > moved_value:
                    score += 50
        
        if is_king:
            enemy_king = b.king(not b.turn)
            if enemy_king:
                from_dist = chess.square_distance(mv.from_square, enemy_king)
                to_dist = chess.square_distance(mv.to_square, enemy_king)
                
                if to_dist < from_dist:
                    score += (from_dist - to_dist) * 50
                
                if to_dist <= 2:
                    score += 60
                elif to_dist == 3:
                    score += 30
                
                controlled_squares = 0
                for sq in chess.SQUARES:
                    if chess.square_distance(sq, enemy_king) <= 2:
                        if chess.square_distance(mv.to_square, sq) <= 1:
                            controlled_squares += 1
                score += controlled_squares * 8
        
        elif moved_piece and moved_piece.piece_type in [4, 5]:
            enemy_king = b.king(not b.turn)
            if enemy_king:
                from_dist = chess.square_distance(mv.from_square, enemy_king)
                to_dist = chess.square_distance(mv.to_square, enemy_king)
                score += (from_dist - to_dist) * 20
        
        if mv.promotion:
            score += 200
        
        return score
    
    legal_moves.sort(key=move_priority, reverse=True)
    
    for mv in legal_moves:
        if mv not in tried:
            nb = node.board.copy()
            nb.push(mv)
            child = Node(nb, parent=node, move=mv, depth=node.depth + 1)

            prior_q = 0.0
            
            if nb.is_check():
                child.N = PRIOR_N * 2
                child.W = PRIOR_W_CHECK * child.N
                child.Q = PRIOR_W_CHECK
                prior_q = PRIOR_W_CHECK
            elif tb is not None and tb.obj is not None and root_turn is not None:
                wdl = probe_wdl(nb, tb.obj)
                if wdl is not None:
                    s = wdl_to_score(wdl)
                    s = s if nb.turn == root_turn else -s
                    child.N = PRIOR_N
                    child.W = s * PRIOR_N * 5
                    child.Q = s * 5
                    prior_q = s * 5

            node.children[mv] = child
            
            debug_info.update({
                'expanded': True,
                'move': mv.uci(),
                'prior_Q': round(prior_q, 3),
                'depth': child.depth,
                'is_mate': False
            })
            
            return child, debug_info
    
    return node, debug_info

def is_piece_hanging(board: chess.Board, square: int) -> bool:
    piece = board.piece_at(square)
    if not piece:
        return False
    
    attackers = board.attackers(not piece.color, square)
    if not attackers:
        return False
    
    defenders = board.attackers(piece.color, square)
    
    if not defenders:
        return True
    
    piece_values = {1: 1, 2: 3, 3: 3, 4: 5, 5: 9, 6: 0}
    piece_value = piece_values.get(piece.piece_type, 0)
    
    min_attacker_value = min(piece_values.get(board.piece_type_at(sq), 10) for sq in attackers)
    if min_attacker_value < piece_value:
        return True
    
    return False

def rollout_policy(board: chess.Board, visited_positions: set) -> chess.Move | None:
    moves = list(board.legal_moves)
    if not moves:
        return None

    # Primero buscar mates
    for m in moves:
        board.push(m)
        if board.is_checkmate():
            board.pop()
            return m
        board.pop()

    scored_moves = []
    piece_values = {1: 1, 2: 3, 3: 3, 4: 5, 5: 9, 6: 0}
    
    for m in moves:
        score = 0
        moved_piece = board.piece_at(m.from_square)
        moved_piece_value = piece_values.get(moved_piece.piece_type if moved_piece else 0, 0)
        
        board.push(m)
        
        pos_key = board.fen().split(' ')[0]
        if pos_key in visited_positions:
            score -= 2000  # Penalización más fuerte
        
        if board.is_check():
            score += 250  # Aumentado
        
        if is_piece_hanging(board, m.to_square):
            penalty = moved_piece_value * 100
            score -= penalty
        
        if board.is_capture(board.peek()):
            captured_value = piece_values.get(board.piece_type_at(m.to_square), 0)
            score += captured_value * 25
            
            if captured_value > moved_piece_value:
                score += 60
        
        if moved_piece and moved_piece.piece_type in [4, 5]:
            enemy_king = board.king(not board.turn)
            if enemy_king:
                dist = chess.square_distance(m.to_square, enemy_king)
                score += (8 - dist) * 12
        
        if moved_piece and moved_piece.piece_type == 6:
            enemy_king = board.king(not board.turn)
            if enemy_king:
                dist = chess.square_distance(m.to_square, enemy_king)
                score += (8 - dist) * 15
        
        if board.is_stalemate() or board.is_insufficient_material():
            score -= 1000
        
        board.pop()
        scored_moves.append((m, score))
    
    scored_moves.sort(key=lambda x: x[1], reverse=True)
    
    if not scored_moves:
        return None
    
    top_moves = [m for m, s in scored_moves[:3] if s >= scored_moves[0][1] - 30]
    return random.choice(top_moves) if top_moves else scored_moves[0][0]

def evaluate_endgame_position(board: chess.Board, root_turn: chess.Color) -> float:
    if board.is_checkmate():
        return 1.0 if board.turn != root_turn else -1.0
    
    if board.is_stalemate() or board.is_insufficient_material():
        return 0.0
    
    piece_values = {1: 1, 2: 3, 3: 3, 4: 5, 5: 9}
    
    our_material = sum(
        piece_values.get(board.piece_type_at(sq), 0)
        for sq in board.pieces(chess.PAWN, root_turn)
    ) + sum(
        piece_values.get(board.piece_type_at(sq), 0)
        for sq in board.pieces(chess.KNIGHT, root_turn)
    ) + sum(
        piece_values.get(board.piece_type_at(sq), 0)
        for sq in board.pieces(chess.BISHOP, root_turn)
    ) + sum(
        piece_values.get(board.piece_type_at(sq), 0)
        for sq in board.pieces(chess.ROOK, root_turn)
    ) + sum(
        piece_values.get(board.piece_type_at(sq), 0)
        for sq in board.pieces(chess.QUEEN, root_turn)
    )
    
    their_material = sum(
        piece_values.get(board.piece_type_at(sq), 0)
        for sq in board.pieces(chess.PAWN, not root_turn)
    ) + sum(
        piece_values.get(board.piece_type_at(sq), 0)
        for sq in board.pieces(chess.KNIGHT, not root_turn)
    ) + sum(
        piece_values.get(board.piece_type_at(sq), 0)
        for sq in board.pieces(chess.BISHOP, not root_turn)
    ) + sum(
        piece_values.get(board.piece_type_at(sq), 0)
        for sq in board.pieces(chess.ROOK, not root_turn)
    ) + sum(
        piece_values.get(board.piece_type_at(sq), 0)
        for sq in board.pieces(chess.QUEEN, not root_turn)
    )
    
    material_diff = our_material - their_material
    
    if material_diff < 0:
        return -0.8
    
    if our_material > their_material:
        their_king = board.king(not root_turn)
        our_king = board.king(root_turn)
        
        if their_king and our_king:
            file = chess.square_file(their_king)
            rank = chess.square_rank(their_king)
            center_dist = max(abs(file - 3.5), abs(rank - 3.5))
            
            king_dist = chess.square_distance(our_king, their_king)
            
            material_score = min(material_diff / 10.0, 0.5)
            position_score = (center_dist / 8.0) - (king_dist / 15.0)
            
            return min(material_score + position_score, 0.95)
    
    return 0.1

def simulate(board, max_plies=ROLLOUT_MAX_PLIES, tb=None, root_turn=None) -> tuple[float, dict]:
    debug_info = {
        'phase': 'simulate',
        'plies': 0,
        'moves': [],
        'tb_hit': False,
        'outcome': None
    }
    
    if root_turn is None:
        root_turn = board.turn

    if tb is not None and tb.obj is not None:
        wdl = probe_wdl(board, tb.obj)
        if wdl is not None:
            s = wdl_to_score(wdl)
            result = s if board.turn == root_turn else -s
            debug_info['tb_hit'] = True
            debug_info['outcome'] = f'TB_immediate_{wdl}'
            return result, debug_info

    plies = 0
    sim_board = board.copy()
    visited_positions = set()
    
    while plies < max_plies:
        if sim_board.is_checkmate() or sim_board.is_stalemate() or \
           sim_board.is_insufficient_material() or sim_board.halfmove_clock >= 100:
            break
        
        if tb is not None and tb.obj is not None:
            wdl_mid = probe_wdl(sim_board, tb.obj)
            if wdl_mid is not None:
                s = wdl_to_score(wdl_mid)
                result = s if sim_board.turn == root_turn else -s
                debug_info['tb_hit'] = True
                debug_info['plies'] = plies
                debug_info['outcome'] = f'TB_mid_{wdl_mid}'
                return result, debug_info
        
        pos_key = sim_board.fen().split(' ')[0]
        if pos_key in visited_positions:
            result = evaluate_endgame_position(sim_board, root_turn)
            debug_info['plies'] = plies
            debug_info['outcome'] = 'cycle_detected'
            return result * 0.2, debug_info  # Penalización más fuerte
        
        visited_positions.add(pos_key)
        
        mv = rollout_policy(sim_board, visited_positions)
        if mv is None:
            break
        
        debug_info['moves'].append(mv.uci())
        sim_board.push(mv)
        plies += 1

    debug_info['plies'] = plies
    
    if sim_board.is_checkmate():
        result = 1.0 if sim_board.turn != root_turn else -1.0
        debug_info['outcome'] = 'checkmate'
    elif sim_board.is_stalemate() or sim_board.is_insufficient_material():
        result = 0.0
        debug_info['outcome'] = 'draw'
    else:
        result = evaluate_endgame_position(sim_board, root_turn)
        debug_info['outcome'] = f'heuristic_{result:.2f}'
    
    return result, debug_info

def backpropagate(node, value):
    cur = node
    sign = 1
    
    while cur is not None:
        cur.N += 1
        cur.W += value * sign
        cur.Q = cur.W / cur.N
        sign *= -1
        cur = cur.parent

def mcts_search(root_board, time_limit=1.0, seed=None, tb=None, debug_callback=None):
    if seed is not None:
        random.seed(seed)
    
    root = Node(root_board.copy())
    root_turn = root_board.turn
    
    # PRIMERO: Buscar mates inmediatos ANTES de iniciar MCTS
    immediate_mates = []
    for move in root_board.legal_moves:
        test_board = root_board.copy()
        test_board.push(move)
        if test_board.is_checkmate():
            immediate_mates.append(move)
    
    # Si hay mate inmediato, retornarlo directamente
    if immediate_mates:
        best_mate = immediate_mates[0]  # Tomar el primero
        stats = {
            'iters': 0,
            'root_N': 0,
            'best_visits': 0,
            'best_Q': 10000.0,
            'mate_found': True,
            'immediate_mate': True,
            'all_moves': {
                m.uci(): {
                    'N': 0,
                    'Q': 10000.0 if m in immediate_mates else 0.0,
                    'W': 0,
                    'is_mate': m in immediate_mates
                }
                for m in root_board.legal_moves
            }
        }
        return best_mate, stats
    
    # Si no hay mate inmediato, proceder con MCTS normal
    end = time.time() + max(0.05, time_limit)
    iters = 0

    while time.time() < end:
        iter_debug = {'iteration': iters + 1}
        
        leaf, select_path = select(root)
        iter_debug['select_path'] = select_path
        
        child, expand_info = expand(leaf, tb=tb, root_turn=root_turn)
        iter_debug['expand'] = expand_info
        
        value, sim_info = simulate(child.board.copy(), tb=tb, root_turn=root_turn)
        iter_debug['simulate'] = sim_info
        iter_debug['value'] = round(value, 3)
        
        backpropagate(child, value)
        iter_debug['backprop_node'] = child.move.uci() if child.move else 'root'
        
        iters += 1
        
        if debug_callback:
            debug_callback(iters, iter_debug)
        
        # Early exit si encontramos mate durante la búsqueda
        if iters > 50:  # Después de algunas iteraciones
            for move, child in root.children.items():
                if child.is_mate and child.N > 0:
                    stats = {
                        'iters': iters,
                        'root_N': root.N,
                        'best_visits': child.N,
                        'best_Q': round(child.Q, 3),
                        'mate_found': True,
                        'all_moves': {
                            m.uci(): {
                                'N': c.N, 
                                'Q': round(c.Q, 3), 
                                'W': round(c.W, 2),
                                'is_mate': c.is_mate
                            }
                            for m, c in sorted(root.children.items(), key=lambda x: x[1].N, reverse=True)
                        }
                    }
                    return move, stats
    
    if not root.children:
        return None, {'iters': iters, 'root_N': root.N}
    
    # PRIORIDAD ABSOLUTA: Si hay un mate, jugarlo
    mate_moves = [(move, child) for move, child in root.children.items() if child.is_mate]
    if mate_moves:
        # Elegir el mate con más visitas (más explorado = más confiable)
        best_mate_move, best_mate_child = max(mate_moves, key=lambda x: x[1].N)
        stats = {
            'iters': iters,
            'root_N': root.N,
            'best_visits': best_mate_child.N,
            'best_Q': round(best_mate_child.Q, 3),
            'mate_found': True,
            'all_moves': {
                m.uci(): {
                    'N': c.N, 
                    'Q': round(c.Q, 3), 
                    'W': round(c.W, 2),
                    'is_mate': c.is_mate
                }
                for m, c in sorted(root.children.items(), key=lambda x: x[1].N, reverse=True)
            }
        }
        return best_mate_move, stats
    
    # Si no hay mate, elegir el mejor por visitas y Q
    move_scores = {}
    for move, child in root.children.items():
        score = child.N + (child.Q * 200 if child.N > root.N * 0.03 else 0)
        move_scores[move] = (score, child)
    
    best_move = max(move_scores.items(), key=lambda x: x[1][0])[0]
    best_child = root.children[best_move]
    
    stats = {
        'iters': iters,
        'root_N': root.N,
        'best_visits': best_child.N,
        'best_Q': round(best_child.Q, 3),
        'mate_found': False,
        'all_moves': {
            move.uci(): {
                'N': child.N, 
                'Q': round(child.Q, 3), 
                'W': round(child.W, 2),
                'score': round(move_scores[move][0], 2),
                'is_mate': child.is_mate
            }
            for move, child in sorted(root.children.items(), key=lambda x: x[1].N, reverse=True)
        }
    }
    
    return best_move, stats