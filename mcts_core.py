
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

def expand(node: 'Node') -> 'Node':
    if node.is_terminal(): return node
    tried = set(node.children.keys())
    for mv in node.board.legal_moves:
        if mv not in tried:
            nb = node.board.copy(); nb.push(mv)
            child = Node(nb, parent=node, move=mv)
            node.children[mv] = child
            return child
    return node

def rollout_policy(board: chess.Board) -> chess.Move|None:
    moves = list(board.legal_moves)
    if not moves: return None
    def score(m):
        s = 0
        if board.is_capture(m): s += 2
        board.push(m)
        if board.is_check(): s += 1
        board.pop()
        return s
    moves.sort(key=score, reverse=True)
    return moves[0]

def simulate(board: chess.Board, max_plies: int = ROLLOUT_MAX_PLIES, tb=None) -> float:
    # Si TB aplica, devolvemos score exacto (WDL->score)
    if tb is not None and tb.obj is not None:
        wdl = probe_wdl(board, tb.obj)
        if wdl is not None:
            return wdl_to_score(wdl)

    plies = 0
    while not board.is_game_over(claim_draw=True) and plies < max_plies:
        if tb is not None and tb.obj is not None:
            wdl_mid = probe_wdl(board, tb.obj)
            if wdl_mid is not None:
                return wdl_to_score(wdl_mid)
        mv = rollout_policy(board)
        if mv is None: break
        board.push(mv); plies += 1

    res = board.result(claim_draw=True)
    return 1.0 if res == '1-0' else -1.0 if res == '0-1' else 0.0

def backpropagate(node: 'Node', value: float) -> None:
    cur = node; v = value
    while cur is not None:
        cur.N += 1
        cur.W += v
        cur.Q = cur.W / cur.N
        v = -v
        cur = cur.parent

def mcts_search(root_board: chess.Board, time_limit: float = 1.0, seed: int|None=None, tb=None):
    if seed is not None: random.seed(seed)
    root = Node(root_board.copy())
    end = time.time() + max(0.05, time_limit)
    iters = 0
    while time.time() < end:
        leaf = select(root)
        child = expand(leaf)
        value = simulate(child.board.copy(), tb=tb)
        backpropagate(child, value)
        iters += 1
    if not root.children:
        return None, {'iters': iters, 'root_N': root.N}
    best_move, best_child = max(root.children.items(), key=lambda kv: kv[1].N)
    return best_move, {'iters': iters, 'root_N': root.N, 'best_visits': best_child.N, 'best_Q': round(best_child.Q,3)}
