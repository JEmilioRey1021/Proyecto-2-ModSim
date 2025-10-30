
import argparse
import chess

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
    parser = argparse.ArgumentParser(description="Paso 1: CLI de ajedrez (sin MCTS)")
    parser.add_argument("--fen", type=str, default=None, help="FEN inicial (si no se indica, startpos)")
    args = parser.parse_args()

    board = chess.Board(args.fen) if args.fen else chess.Board()
    print("=== Paso 1: CLI de ajedrez ===")
    print("Escribe 'help' para ver comandos.\n")
    print_board(board)

    while True:
        if board.is_game_over(claim_draw=True):
            print("Juego terminado. Resultado:", board.result(claim_draw=True))
            break

        cmd = input("Tu comando/jugada: ").strip().lower()
        if cmd == "":
            print("Saliendo..."); break
        if cmd == "help":
            print(HELP); continue
        if cmd == "moves":
            print("Legales:", " ".join([m.uci() for m in board.legal_moves])); continue
        if cmd == "undo":
            if board.move_stack:
                board.pop(); print_board(board)
            else:
                print("No hay jugadas para deshacer.")
            continue
        if cmd == "fen":
            print(board.fen()); continue

        # Interpretar como jugada UCI
        try:
            mv = chess.Move.from_uci(cmd)
        except ValueError:
            print("Formato UCI inválido. Ej: e2e4, g1f3, e7e8q"); continue

        if mv not in board.legal_moves:
            print("Jugada ilegal en esta posición."); continue

        san = board.san(mv)
        board.push(mv)
        print(f"Jugaste: {san} ({mv.uci()})\n")
        print_board(board)

if __name__ == "__main__":
    main()
