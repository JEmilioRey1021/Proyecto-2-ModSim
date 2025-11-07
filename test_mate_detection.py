"""
Script para verificar que el MCTS detecta mates correctamente
Ejecuta esto en la terminal para probar sin la interfaz
"""

import chess
from mcts_core import mcts_search

def test_mate_in_1():
    """Test 1: Rey y Dama vs Rey - Mate en 1"""
    print("="*60)
    print("TEST 1: Rey y Dama vs Rey (Mate en 1)")
    print("="*60)
    
    # Posición: Rey blanco a1, Dama h3, Rey negro a3
    fen = "8/8/8/8/8/k6Q/8/K7 w - - 0 1"
    board = chess.Board(fen)
    
    print(f"FEN: {fen}")
    print(f"\nTablero:")
    print(board)
    
    # Verificar manualmente qué movimientos son mate
    print("\n🔍 Verificando movimientos legales...")
    mates_found = []
    for move in board.legal_moves:
        test_board = board.copy()
        test_board.push(move)
        if test_board.is_checkmate():
            mates_found.append(move.uci())
            print(f"  ✅ {move.uci()} - JAQUE MATE!")
        else:
            print(f"  ❌ {move.uci()} - No es mate")
    
    print(f"\n📊 Mates disponibles: {mates_found}")
    
    # Probar MCTS con diferentes tiempos
    for time_limit in [0.5, 1.0, 2.0, 5.0]:
        print(f"\n⏱️  Probando MCTS con {time_limit}s...")
        best_move, stats = mcts_search(board, time_limit=time_limit)
        
        print(f"  Movimiento elegido: {best_move.uci() if best_move else 'NINGUNO'}")
        print(f"  ¿Es mate?: {best_move.uci() in mates_found if best_move else False}")
        print(f"  Mate detectado: {stats.get('mate_found', False)}")
        print(f"  Iteraciones: {stats.get('iters', 0)}")
        
        if stats.get('immediate_mate'):
            print(f"  ✅ MATE INMEDIATO DETECTADO (sin búsqueda)")
        
        if best_move and best_move.uci() in mates_found:
            print(f"  ✅✅✅ ¡ÉXITO! MCTS jugó mate")
            break
        else:
            print(f"  ❌ FALLO: No jugó mate")

def test_mate_in_1_two_rooks():
    """Test 2: Rey y 2 Torres vs Rey"""
    print("\n" + "="*60)
    print("TEST 2: Rey y 2 Torres vs Rey (Mate en 1)")
    print("="*60)
    
    fen = "8/8/8/8/8/6RR/3K4/k7 w - - 0 1"
    board = chess.Board(fen)
    
    print(f"FEN: {fen}")
    print(f"\nTablero:")
    print(board)
    
    print("\n🔍 Verificando movimientos legales...")
    mates_found = []
    for move in board.legal_moves:
        test_board = board.copy()
        test_board.push(move)
        if test_board.is_checkmate():
            mates_found.append(move.uci())
            print(f"  ✅ {move.uci()} - JAQUE MATE!")
    
    print(f"\n📊 Mates disponibles: {mates_found}")
    
    print(f"\n⏱️  Probando MCTS con 2s...")
    best_move, stats = mcts_search(board, time_limit=2.0)
    
    print(f"  Movimiento elegido: {best_move.uci() if best_move else 'NINGUNO'}")
    print(f"  ¿Es mate?: {best_move.uci() in mates_found if best_move else False}")
    print(f"  Mate detectado: {stats.get('mate_found', False)}")
    
    if best_move and best_move.uci() in mates_found:
        print(f"  ✅✅✅ ¡ÉXITO! MCTS jugó mate")
    else:
        print(f"  ❌ FALLO: No jugó mate")

def test_no_mate_position():
    """Test 3: Posición sin mate inmediato"""
    print("\n" + "="*60)
    print("TEST 3: Rey y Torre vs Rey (No hay mate en 1)")
    print("="*60)
    
    fen = "8/8/8/8/8/7R/3K4/k7 w - - 0 1"
    board = chess.Board(fen)
    
    print(f"FEN: {fen}")
    print(f"\nTablero:")
    print(board)
    
    print("\n🔍 Verificando movimientos legales...")
    mates_found = []
    for move in board.legal_moves:
        test_board = board.copy()
        test_board.push(move)
        if test_board.is_checkmate():
            mates_found.append(move.uci())
    
    print(f"📊 Mates disponibles: {mates_found if mates_found else 'NINGUNO (correcto)'}")
    
    print(f"\n⏱️  Probando MCTS con 2s...")
    best_move, stats = mcts_search(board, time_limit=2.0)
    
    print(f"  Movimiento elegido: {best_move.uci() if best_move else 'NINGUNO'}")
    print(f"  Mate detectado: {stats.get('mate_found', False)}")
    print(f"  Iteraciones: {stats.get('iters', 0)}")
    
    if not mates_found and not stats.get('immediate_mate'):
        print(f"  ✅ Correcto: No hay mate inmediato y MCTS lo reconoce")
    elif mates_found:
        print(f"  ⚠️  Hay mate pero no se esperaba en esta posición")

def debug_expand_function():
    """Test 4: Verificar que expand() detecta mates"""
    print("\n" + "="*60)
    print("TEST 4: Verificar función expand()")
    print("="*60)
    
    from mcts_core import Node, expand
    
    fen = "8/8/8/8/8/k6Q/8/K7 w - - 0 1"
    board = chess.Board(fen)
    
    print(f"Creando nodo raíz con FEN: {fen}")
    root = Node(board.copy())
    
    print("\nExpandiendo nodo raíz...")
    child, debug_info = expand(root, tb=None, root_turn=chess.WHITE)
    
    print(f"\nResultado de expand():")
    print(f"  Expandido: {debug_info.get('expanded')}")
    print(f"  Movimiento: {debug_info.get('move')}")
    print(f"  Es mate: {debug_info.get('is_mate')}")
    print(f"  Prior Q: {debug_info.get('prior_Q')}")
    print(f"  Mates totales encontrados: {debug_info.get('total_mates_found', 0)}")
    
    print(f"\nHijos creados en root: {len(root.children)}")
    for move, child_node in root.children.items():
        print(f"  {move.uci()}: is_mate={child_node.is_mate}, N={child_node.N}, Q={child_node.Q}")
    
    if any(c.is_mate for c in root.children.values()):
        print("\n  ✅ expand() detectó mates correctamente")
    else:
        print("\n  ❌ expand() NO detectó mates")

if __name__ == "__main__":
    print("🧪 TEST SUITE PARA DETECCIÓN DE MATES\n")
    
    try:
        test_mate_in_1()
        test_mate_in_1_two_rooks()
        test_no_mate_position()
        debug_expand_function()
        
        print("\n" + "="*60)
        print("✅ TODOS LOS TESTS COMPLETADOS")
        print("="*60)
        print("\nSi los tests 1 y 2 fallan, hay un problema en el código.")
        print("Si el test 4 muestra que expand() detecta mates pero")
        print("mcts_search() no los juega, el problema está en la")
        print("función de selección final.\n")
        
    except Exception as e:
        print(f"\n❌ ERROR DURANTE LOS TESTS:")
        print(f"{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()