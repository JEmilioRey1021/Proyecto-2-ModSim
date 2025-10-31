
import math, random, time
from dataclasses import dataclass, field
import chess
from tb_utils import probe_wdl, wdl_to_score

C_PUCT = 1.4
ROLLOUT_MAX_PLIES = 40

@dataclass
class Node:
    board: chess.Board
    parent: 'Node|None' = None
    move: chess.Move|None = None
    children: dict = field(default_factory=dict)  # move -> Node
    N: int = 0
    W: float = 0.0
    Q: float = 0.0

    def is_terminal(self):
        return self.board.is_game_over(claim_draw=True)

def uct_value(child: 'Node', parent_N: int) -> float:
    return child.Q + C_PUCT * math.sqrt(math.log(parent_N + 1) / (1 + child.N))

def select(node: 'Node') -> 'Node':
    cur = node
    while cur.children:
        cur = max(cur.children.values(), key=lambda ch: uct_value(ch, cur.N))
        if cur.is_terminal(): break
    return cur
from tb_utils import probe_wdl, wdl_to_score

PRIOR_N = 2   # pequeño
PRIOR_W = 2.0 # se ajusta según signo

def expand(node: 'Node', tb=None, root_turn=None) -> 'Node':
    if node.is_terminal():
        return node
    tried = set(node.children.keys())
    for mv in node.board.legal_moves:
        if mv not in tried:
            nb = node.board.copy(); nb.push(mv)
            child = Node(nb, parent=node, move=mv)

            # Prior guiado por TB si existe
            if tb is not None and tb.obj is not None and root_turn is not None:
                wdl = probe_wdl(nb, tb.obj)
                if wdl is not None:
                    s = wdl_to_score(wdl)
                    s = s if nb.turn == root_turn else -s
                    child.N = PRIOR_N
                    child.W = PRIOR_W * s
                    child.Q = child.W / child.N

            node.children[mv] = child
            return child
    return node

def rollout_policy(board: chess.Board) -> chess.Move | None:
    moves = list(board.legal_moves)
    if not moves:
        return None

    last = board.peek() if board.move_stack else None

    def score(m: chess.Move) -> int:
        s = 0
        # preferir progreso básico
        if board.is_capture(m): s += 3
        board.push(m)

        # bonus: jaque
        if board.is_check(): s += 1

        # penalizar “deshacer” la última jugada (ping-pong)
        if last is not None:
            if (m.from_square == last.to_square) and (m.to_square == last.from_square):
                s -= 4

        # penalizar repetición (o inminente 3-fold)
        if board.is_repetition(3) or board.can_claim_threefold_repetition():
            s -= 3

        # penalizar acercarse a regla de 50 movimientos si no hay captura/peón
        # (el halfmove_clock ya subió por el push)
        if board.halfmove_clock >= 90:   # umbral “temprano”
            s -= 1
        if board.halfmove_clock >= 95:   # umbral “crítico”
            s -= 2

        board.pop()
        return s

    moves.sort(key=score, reverse=True)
    return moves[0]

def simulate(board, max_plies=ROLLOUT_MAX_PLIES, tb=None, root_turn=None) -> float:
    if root_turn is None:
        root_turn = chess.WHITE

    # Atajo con TB: WDL está en perspectiva del lado que mueve → re-referenciar a root
    if tb is not None and tb.obj is not None:
        wdl = probe_wdl(board, tb.obj)
        if wdl is not None:
            s = wdl_to_score(wdl)
            return s if board.turn == root_turn else -s

    plies = 0
    while not board.is_game_over(claim_draw=True) and plies < max_plies:
        if tb is not None and tb.obj is not None:
            wdl_mid = probe_wdl(board, tb.obj)
            if wdl_mid is not None:
                s = wdl_to_score(wdl_mid)
                return s if board.turn == root_turn else -s
        mv = rollout_policy(board)
        if mv is None: break
        board.push(mv); plies += 1

    res = board.result(claim_draw=True)
    if res == "1-0":
        return +1.0 if root_turn == chess.WHITE else -1.0
    if res == "0-1":
        return +1.0 if root_turn == chess.BLACK else -1.0
    return 0.0

def backpropagate(node, value):
    cur = node
    while cur is not None:
        cur.N += 1
        cur.W += value          # ¡sin cambiar signo!
        cur.Q = cur.W / cur.N
        cur = cur.parent

def mcts_search(root_board, time_limit=1.0, seed=None, tb=None):
    if seed is not None: random.seed(seed)
    root = Node(root_board.copy())

    root_turn = root_board.turn  # <- color del jugador raíz
    end = time.time() + max(0.05, time_limit)
    iters = 0

    while time.time() < end:
        leaf = select(root)
        child = expand(leaf, tb = tb, root_turn = root_turn)
        value = simulate(child.board.copy(), tb=tb, root_turn=root_turn)  # <- aquí
        backpropagate(child, value)
        iters += 1
        
    if not root.children:
        return None, {'iters': iters, 'root_N': root.N}
    best_move, best_child = max(root.children.items(), key=lambda kv: kv[1].N)
    return best_move, {'iters': iters, 'root_N': root.N, 'best_visits': best_child.N, 'best_Q': round(best_child.Q,3)}
