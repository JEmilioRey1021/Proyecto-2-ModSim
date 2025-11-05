import math, random, time
from dataclasses import dataclass, field
import chess
from tb_utils import probe_wdl, wdl_to_score

C_PUCT = 2.5  # Más exploración
ROLLOUT_MAX_PLIES = 30

# --- Heurística de Endgame ---
PRIOR_N = 10
PRIOR_W_MATE = 1000.0
PRIOR_W_CHECK = 200.0
PRIOR_W_WIN = 5.0
PRIOR_W_DRAW = 0.5
PRIOR_W_LOSS = -5.0

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

    def is_terminal(self):
        # NO considerar repetición como terminal en el árbol
        return self.board.is_checkmate() or self.board.is_stalemate() or \
               self.board.is_insufficient_material() or self.board.halfmove_clock >= 100

def uct_value(child: 'Node', parent_N: int) -> float:
    """UCT con bonus por profundidad (preferir avanzar)"""
    if child.N == 0:
        return float('inf')
    
    # Bonus por profundidad para evitar ciclos
    depth_bonus = 0.1 / (1 + child.depth)
    
    return child.Q + C_PUCT * math.sqrt(math.log(parent_N + 1) / child.N) + depth_bonus

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
            'uct': round(uct_values[best_move], 3),
            'depth': best_child.depth
        })
        
        cur = best_child
    
    return cur, debug_path

def expand(node: 'Node', tb=None, root_turn=None) -> tuple['Node', dict]:
    """Expande con heurística de endgame que considera TODAS las piezas"""
    debug_info = {'phase': 'expand', 'expanded': False}
    
    if node.is_terminal():
        return node, debug_info
    
    tried = set(node.children.keys())
    legal_moves = list(node.board.legal_moves)
    piece_values = {1: 1, 2: 3, 3: 3, 4: 5, 5: 9, 6: 0}
    
    def move_priority(mv):
        score = 0
        b = node.board
        moved_piece = b.piece_at(mv.from_square)
        moved_value = piece_values.get(moved_piece.piece_type if moved_piece else 0, 0)
        is_king = moved_piece and moved_piece.piece_type == chess.KING
        
        b.push(mv)
        is_checkmate = b.is_checkmate()
        is_check = b.is_check()
        
        if is_checkmate:
            b.pop()
            return 100000  # Retornar inmediatamente con score máximo
        
        if is_check:
            score += 100
        
        if not is_checkmate and is_piece_hanging(b, mv.to_square):
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
                    score += (from_dist - to_dist) * 40
                
                if to_dist <= 3:
                    score += 30
                elif to_dist == 4:
                    score += 15
                
                controlled_squares = 0
                for sq in chess.SQUARES:
                    if chess.square_distance(sq, enemy_king) <= 2:
                        if chess.square_distance(mv.to_square, sq) <= 1:
                            controlled_squares += 1
                score += controlled_squares * 5
        
        elif moved_piece and moved_piece.piece_type in [4, 5]:
            enemy_king = b.king(not b.turn)
            if enemy_king:
                from_dist = chess.square_distance(mv.from_square, enemy_king)
                to_dist = chess.square_distance(mv.to_square, enemy_king)
                score += (from_dist - to_dist) * 15
        
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
            
            if nb.is_checkmate():
                child.N = PRIOR_N * 5
                child.W = PRIOR_W_MATE * child.N
                child.Q = PRIOR_W_MATE
                prior_q = PRIOR_W_MATE
            elif nb.is_check():
                child.N = PRIOR_N
                child.W = PRIOR_W_CHECK * child.N
                child.Q = PRIOR_W_CHECK
                prior_q = PRIOR_W_CHECK
            elif tb is not None and tb.obj is not None and root_turn is not None:
                wdl = probe_wdl(nb, tb.obj)
                if wdl is not None:
                    s = wdl_to_score(wdl)
                    s = s if nb.turn == root_turn else -s
                    child.N = PRIOR_N
                    child.W = s * PRIOR_N * 3
                    child.Q = s * 3
                    prior_q = s * 3

            node.children[mv] = child
            
            debug_info.update({
                'expanded': True,
                'move': mv.uci(),
                'prior_Q': round(prior_q, 3),
                'depth': child.depth
            })
            
            return child, debug_info
    
    return node, debug_info

def compare_moves_with_theoretical(board, theoretical_moves):
    """Compara los movimientos generados con los movimientos teóricos correctos."""
    moves = list(board.legal_moves)
    theoretical_count = 0
    correct_moves = []
    
    for mv in moves:
        if mv.uci() in theoretical_moves:
            theoretical_count += 1
            correct_moves.append(mv.uci())
    
    total_moves = len(moves)
    accuracy = (theoretical_count / total_moves) * 100 if total_moves > 0 else 0
    
    return {
        'theoretical_count': theoretical_count,
        'total_moves': total_moves,
        'accuracy': accuracy,
        'correct_moves': correct_moves
    }

def print_comparison_stats(stats):
    """Muestra las estadísticas de comparación entre los movimientos teóricos y los generados"""
    print(f"Total de movimientos: {stats['total_moves']}")
    print(f"Movimientos teóricos correctos: {stats['theoretical_count']}")
    print(f"Precisión de los movimientos: {stats['accuracy']:.2f}%")
    print(f"Movimientos correctos: {', '.join(stats['correct_moves'])}")

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

def mcts_search(root_board, theoretical_moves, time_limit=1.0, seed=None, tb=None, debug_callback=None):
    """Búsqueda MCTS mejorada con comparación de movimientos teóricos"""
    if seed is not None:
        random.seed(seed)
    
    root = Node(root_board.copy())
    root_turn = root_board.turn
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
    
    # Comparación con los movimientos teóricos
    stats = compare_moves_with_theoretical(root.board, theoretical_moves)
    print_comparison_stats(stats)

    if not root.children:
        return None, {'iters': iters, 'root_N': root.N}
    
    for move, child in root.children.items():
        if child.board.is_checkmate():
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
                        'is_mate': c.board.is_checkmate()
                    }
                    for m, c in sorted(root.children.items(), key=lambda x: x[1].N, reverse=True)
                }
            }
            return move, stats
    
    move_scores = {}
    for move, child in root.children.items():
        score = child.N
        if child.N > root.N * 0.05:
            score += child.Q * 100
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
                'is_mate': child.board.is_checkmate()
            }
            for move, child in sorted(root.children.items(), key=lambda x: x[1].N, reverse=True)
        }
    }
    
    return best_move, stats
