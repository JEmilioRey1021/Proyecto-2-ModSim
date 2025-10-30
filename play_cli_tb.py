
import argparse, json, os, time
from datetime import datetime
import chess
from mcts_core import mcts_search
from tb_utils import TBLite, probe_wdl, probe_dtz, best_moves_by_tb, wdl_to_score

HELP = """Comandos:
- UCI: e2e4, g1f3, e7e8q
- moves : muestra jugadas legales
- undo  : deshacer última jugada
- fen   : imprime FEN actual
- help  : muestra esta ayuda
- ENTER vacío para salir
"""

def print_board(board):
    print(board)
    print(f"Turno: {'BLANCAS' if board.turn else 'NEGRAS'}  | FEN: {board.board_fen()}  | Halfmove: {board.halfmove_clock}\n")

def describe_tb(board, tb):
    if tb is None or tb.obj is None: return None
    wdl = probe_wdl(board, tb.obj)
    dtz = probe_dtz(board, tb.obj)
    return {"wdl": wdl, "dtz": dtz, "score": wdl_to_score(wdl)}

def eval_move(board_before, move, tb):
    if tb is None or tb.obj is None: return None
    info_before = describe_tb(board_before, tb)
    b_after = board_before.copy(); b_after.push(move)
    info_after = describe_tb(b_after, tb)
    ranking = best_moves_by_tb(board_before, tb.obj)
    best_set = ranking.get('best_set', set())
    is_opt = move.uci() in best_set
    return {"before": info_before, "after": info_after, "is_optimal": is_opt, "best_wdl": ranking.get('best_wdl')}

def main():
    parser = argparse.ArgumentParser(description="Paso 3: MCTS + Syzygy (CLI)")
    parser.add_argument("--fen", type=str, default=None, help="FEN inicial (si no se indica, startpos)")
    parser.add_argument("--mcts-time", type=float, default=1.0, help="Tiempo (s) por jugada del bot")
    parser.add_argument("--you-play", choices=["white","black"], default="white", help="Tu color")
    parser.add_argument("--syzygy-dir", type=str, default=None, help="Ruta a tablebases Syzygy (3–5 piezas)")
    parser.add_argument("--seed", type=int, default=42, help="Semilla")
    args = parser.parse_args()

    board = chess.Board(args.fen) if args.fen else chess.Board()
    human_white = (args.you_play == "white")

    print("=== Paso 3: MCTS + Syzygy ===")
    print("Escribe 'help' para ver comandos.\n")
    print_board(board)

    os.makedirs("logs", exist_ok=True)
    log_path = os.path.join("logs", f"game_tb_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl")
    def log(ev):
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    with TBLite(args.syzygy_dir) as tb:
        log({"type":"start","fen":board.fen(),"human_color":args.you_play,"mcts_time":args.mcts_time,"syzygy_dir":args.syzygy_dir})
        while not board.is_game_over(claim_draw=True):
            # Mostrar evaluación TB del estado actual
            tb_eval = describe_tb(board, tb)
            if tb_eval:
                print(f"TB -> WDL={tb_eval['wdl']}  DTZ={tb_eval['dtz']}  score={tb_eval['score']}")

            if (board.turn and human_white) or ((not board.turn) and (not human_white)):
                cmd = input("Tu comando/jugada: ").strip().lower()
                if cmd == "": print("Saliendo..."); break
                if cmd == "help": print(HELP); continue
                if cmd == "moves": print("Legales:", " ".join([m.uci() for m in board.legal_moves])); continue
                if cmd == "undo":
                    if board.move_stack: board.pop(); print_board(board)
                    else: print("No hay jugadas para deshacer.")
                    continue
                if cmd == "fen": print(board.fen()); continue
                try:
                    mv = chess.Move.from_uci(cmd)
                except ValueError:
                    print("Formato UCI inválido."); continue
                if mv not in board.legal_moves:
                    print("Jugada ilegal."); continue
                evalm = eval_move(board, mv, tb)
                san = board.san(mv); board.push(mv)
                print(f"Humano: {san} ({mv.uci()})")
                if evalm:
                    print(f"  -> {'ÓPTIMA ✅' if evalm['is_optimal'] else 'Subóptima ❌'} | ANTES WDL={evalm['before']['wdl']} DTZ={evalm['before']['dtz']} | DESPUÉS WDL={evalm['after']['wdl']} DTZ={evalm['after']['dtz']}")
                print_board(board)
                log({"type":"human_move","uci":mv.uci(),"san":san,"fen":board.fen(),"tb_eval":evalm})
            else:
                t0 = time.time()
                best, stats = mcts_search(board, time_limit=args.mcts_time, seed=args.seed, tb=tb)
                if best is None:
                    print("MCTS no encontró jugada."); break
                evalm = eval_move(board, best, tb)
                san = board.san(best); board.push(best)
                elapsed = time.time() - t0
                print(f"MCTS: {san} ({best.uci()}) | {elapsed:.2f}s | stats={stats}")
                if evalm:
                    print(f"  -> {'ÓPTIMA ✅' if evalm['is_optimal'] else 'Subóptima ❌'} | ANTES WDL={evalm['before']['wdl']} DTZ={evalm['before']['dtz']} | DESPUÉS WDL={evalm['after']['wdl']} DTZ={evalm['after']['dtz']}")
                print_board(board)
                log({"type":"mcts_move","uci":best.uci(),"san":san,"fen":board.fen(),"stats":stats,"tb_eval":evalm})

        res = board.result(claim_draw=True)
        print("Resultado:", res)
        log({"type":"final","result":res,"final_fen":board.fen()})

if __name__ == "__main__":
    main()
