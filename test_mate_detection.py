"""
Script de diagnóstico para entender por qué el MCTS no detecta mates
"""

import chess

def test_position_manually(fen, name):
    """Verifica manualmente si hay mates en una posición"""
    print("="*70)
    print(f"🔍 DIAGNÓSTICO: {name}")
    print("="*70)
    print(f"FEN: {fen}")
    
    board = chess.Board(fen)
    print(f"\nTurno: {'Blancas' if board.turn == chess.WHITE else 'Negras'}")
    print("\nTablero:")
    print(board)
    print()
    
    # Verificar TODOS los movimientos legales
    print("📋 Analizando movimientos legales:")
    print("-" * 70)
    
    mate_moves = []
    check_moves = []
    normal_moves = []
    
    for move in board.legal_moves:
        test_board = board.copy()
        test_board.push(move)
        
        status = ""
        category = "normal"
        
        if test_board.is_checkmate():
            status = "✅ JAQUE MATE"
            category = "mate"
            mate_moves.append(move)
        elif test_board.is_check():
            status = "⚠️  Jaque"
            category = "check"
            check_moves.append(move)
        else:
            status = "○ Normal"
            category = "normal"
            normal_moves.append(move)
        
        # Mostrar info del movimiento
        piece = board.piece_at(move.from_square)
        piece_name = piece.symbol() if piece else "?"
        
        print(f"{move.uci():6s} | {piece_name:2s} | {status:15s}")
    
    print("-" * 70)
    print(f"\n📊 RESUMEN:")
    print(f"  • Mates disponibles: {len(mate_moves)}")
    print(f"  • Jaques: {len(check_moves)}")
    print(f"  • Movimientos normales: {len(normal_moves)}")
    
    if mate_moves:
        print(f"\n✅ MATES ENCONTRADOS:")
        for move in mate_moves:
            print(f"  → {move.uci()}")
    else:
        print(f"\n❌ NO HAY MATES EN 1")
    
    print()
    return len(mate_moves) > 0

def main():
    print("🧪 SCRIPT DE DIAGNÓSTICO - DETECCIÓN DE MATES")
    print()
    
    positions = [
        ("7k/5Q2/6K1/8/8/8/8/8 w - - 0 1", "Rey y Dama vs Rey"),
        ("8/8/8/8/8/6RR/3K4/k7 w - - 0 1", "Rey y 2 Torres vs Rey"),
        ("6k1/5R2/6K1/8/8/8/8/8 w - - 0 1", "Torre en Séptima"),
        ("8/8/8/8/8/7R/3K4/k7 w - - 0 1", "Rey y Torre vs Rey"),
        ("8/8/8/8/3k4/8/2Q5/2K5 w - - 0 1", "Dama en Centro"),
    ]
    
    results = []
    for fen, name in positions:
        has_mate = test_position_manually(fen, name)
        results.append((name, has_mate))
    
    print("="*70)
    print("📋 RESUMEN FINAL")
    print("="*70)
    for name, has_mate in results:
        status = "✅ Tiene mate en 1" if has_mate else "❌ NO tiene mate en 1"
        print(f"{name:30s} | {status}")
    
    print("\n💡 IMPORTANTE:")
    print("Si alguna posición NO tiene mate en 1, entonces el MCTS")
    print("NO debería detectar 'immediate_mate'. El problema podría")
    print("ser que las posiciones en TEST_POSITIONS no tienen mate inmediato.")

if __name__ == "__main__":
    main()