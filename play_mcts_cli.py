
import argparse, json, os, time
from datetime import datetime
import chess
from mcts_core_anterior import mcts_search  # noqa

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

def main():
    parser = argparse.ArgumentParser(description="Paso 2: Jugar contra MCTS (CLI)")
    parser.add_argument("--fen", type=str, default=None, help="FEN inicial (si no se indica, startpos)")
    parser.add_argument("--mcts-time", type=float, default=1.0, help="Tiempo (s) por jugada del bot")
    parser.add_argument("--you-play", choices=["white","black"], default="white", help="Tu color")
    parser.add_argument("--seed", type=int, default=42, help="Semilla")
    args = parser.parse_args()

    board = chess.Board(args.fen) if args.fen else chess.Board()
    human_white = (args.you_play == "white")

    print("=== Paso 2: Jugar contra MCTS ===")
    print("Escribe 'help' para ver comandos.\n")
    print_board(board)

    os.makedirs("logs", exist_ok=True)
    log_path = os.path.join("logs", f"mcts_game_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl")
    def log(ev):
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    log({"type":"start","fen":board.fen(),"human_color":args.you_play,"mcts_time":args.mcts_time})

    while not board.is_game_over(claim_draw=True):
        if (board.turn and human_white) or ((not board.turn) and (not human_white)):
            # HUMANO
            cmd = input("Tu comando/jugada: ").strip().lower()
            if cmd == "": print("Saliendo..."); break
            if cmd == "help": print(HELP); continue
            if cmd == "moves": print("Legales:", " ".join([m.uci() for m in board.legal_moves])); continue
            if cmd == "undo":
                if board.move_stack: board.pop(); print_board(board)
                else: print("No hay jugadas para deshacer.")
                continue
            if cmd == "fen": print(board.fen()); continue
            # Interpretar como UCI
            try:
                mv = chess.Move.from_uci(cmd)
            except ValueError:
                print("Formato UCI inválido."); continue
            if mv not in board.legal_moves:
                print("Jugada ilegal."); continue
            san = board.san(mv)
            board.push(mv)
            print(f"Humano: {san} ({mv.uci()})\n")
            print_board(board)
            log({"type":"human_move","uci":mv.uci(),"san":san,"fen":board.fen()})
        else:
            # BOT MCTS
            t0 = time.time()
            best, stats = mcts_search(board, time_limit=args.mcts_time, seed=args.seed)
            if best is None:
                print("MCTS no encontró jugada."); break
            san = board.san(best)
            board.push(best)
            elapsed = time.time() - t0
            print(f"MCTS: {san} ({best.uci()}) | {elapsed:.2f}s | stats={stats}\n")
            print_board(board)
            log({"type":"mcts_move","uci":best.uci(),"san":san,"fen":board.fen(),"stats":stats})

    res = board.result(claim_draw=True)
    print("Resultado:", res)
    log({"type":"final","result":res,"final_fen":board.fen()})

if __name__ == "__main__":
    main()
