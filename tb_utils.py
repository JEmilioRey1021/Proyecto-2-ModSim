
from __future__ import annotations
import chess
from chess.syzygy import open_tablebase

# WDL: 2 win, 1 draw, 0 loss (for side to move)
def probe_wdl(board: chess.Board, tb) -> int | None:
    try:
        return tb.probe_wdl(board)
    except Exception:
        return None

def probe_dtz(board: chess.Board, tb) -> int | None:
    try:
        return tb.probe_dtz(board)
    except Exception:
        return None

def wdl_to_score(wdl: int | None) -> float | None:
    if wdl is None: return None
    return 1.0 if wdl == 2 else 0.0 if wdl == 1 else -1.0

def best_moves_by_tb(board: chess.Board, tb) -> dict:
    """
    Devuelve dict con 'moves': {uci -> {'wdl', 'dtz'}} y:
      - 'best_set': conjunto de jugadas óptimas según WDL, desempate por DTZ.
      - 'best_wdl': WDL de las mejores.
    """
    legal = list(board.legal_moves)
    scored = {}
    best_wdl = -9
    for mv in legal:
        board.push(mv)
        wdl = probe_wdl(board, tb)
        dtz = probe_dtz(board, tb)
        board.pop()
        scored[mv.uci()] = {'wdl': wdl, 'dtz': dtz}
        if wdl is not None and wdl > best_wdl:
            best_wdl = wdl

    candidates = [uci for uci, v in scored.items() if v['wdl'] == best_wdl]

    def dtz_key(uci):
        v = scored[uci]; dtz = v['dtz']
        if dtz is None:
            return 9999 if best_wdl == 2 else -9999 if best_wdl == 0 else 9999
        if best_wdl == 2:   # ganar rápido
            return dtz
        elif best_wdl == 0: # perder lento
            return -dtz
        else:               # tablas: preferir DTZ=0; luego |DTZ| mínimo
            return 0 if dtz == 0 else abs(dtz)

    if candidates:
        ranked = sorted(candidates, key=dtz_key)
        best_val = dtz_key(ranked[0])
        best_set = set([u for u in ranked if dtz_key(u) == best_val])
    else:
        best_set = set()

    return {'moves': scored, 'best_set': best_set, 'best_wdl': best_wdl}

class TBLite:
    """Context manager para abrir/cerrar Syzygy de forma segura."""
    def __init__(self, path: str | None):
        self.path = path
        self.obj = None
    def __enter__(self):
        if self.path:
            self.obj = open_tablebase(self.path)
        return self
    def __exit__(self, exc_type, exc, tb):
        if self.obj:
            self.obj.close()
        self.obj = None
