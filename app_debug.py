import streamlit as st
import chess
import chess.svg
import base64
import json
from mcts_core import mcts_search
from tb_utils import TBLite

# Endgames famosos
FAMOUS_ENDGAMES = {
    "Mate de pasillo (negras ganan)":"1Q6/p1p2rk1/5q2/2pp2pp/6b1/1PPBR3/P4PPP/RN5K b - - 0 1",
    "Rey y Dama vs Rey": "8/8/8/8/8/7Q/3K4/k7 w - - 0 1",
    "Rey y Torre vs Rey": "8/8/8/8/8/7R/3K4/k7 w - - 0 1",
    "Rey y 2 Torres vs Rey": "8/8/8/8/8/6RR/3K4/k7 w - - 0 1",
    "Rey y Alfil + Caballo vs Rey": "8/8/8/8/8/5BN1/3K4/k7 w - - 0 1",
    "Rey y 2 Alfiles vs Rey": "8/8/8/8/8/6BB/3K4/k7 w - - 0 1",
    "Lucena (Torre)": "1K6/1P1k4/8/8/8/8/r7/2R5 w - - 0 1",
    "Philidor (Defensa Torre)": "3k4/R7/3K4/8/8/8/r7/8 b - - 0 1",
    "Peones enfrentados": "8/4k3/8/3pP3/3K4/8/8/8 w - - 0 1",
    "Final de Alfiles de distinto color": "8/5k2/4b3/3pP3/3K1B2/8/8/8 w - - 0 1",
    "Rey y Peón vs Rey": "8/8/8/8/3k4/3P4/3K4/8 w - - 0 1"
}

def initialize_session_state():
    """Inicializa el estado de la sesión"""
    if 'board' not in st.session_state:
        default_fen = FAMOUS_ENDGAMES["Mate de pasillo (negras ganan)"]
        st.session_state.board = chess.Board(default_fen)
        st.session_state.game_over = False
        st.session_state.move_history = []
        st.session_state.status_message = "¡Juego iniciado! Blancas (MCTS) mueven primero."
        st.session_state.user_color = chess.BLACK
        st.session_state.mcts_time = 2.0
        st.session_state.selected_endgame = "Mate de pasillo (negras ganan)"
        st.session_state.tb_path = None
        st.session_state.debug_mode = True
        st.session_state.last_mcts_debug = []
        st.session_state.last_mcts_stats = {}

def display_board():
    """Muestra el tablero de ajedrez"""
    last_move = st.session_state.board.peek() if st.session_state.board.move_stack else None
    
    board_svg = chess.svg.board(
        board=st.session_state.board, 
        lastmove=last_move,
        size=450,
        orientation=st.session_state.user_color
    )
    
    b64 = base64.b64encode(board_svg.encode('utf-8')).decode('utf-8')
    html = f'<div style="text-align: center;"><img src="data:image/svg+xml;base64,{b64}"></div>'
    st.markdown(html, unsafe_allow_html=True)

def check_game_over():
    """Verifica si el juego terminó"""
    board = st.session_state.board
    
    if board.is_game_over():
        st.session_state.game_over = True
        result = board.result()
        if result == "1-0":
            st.session_state.status_message = "🎉 ¡Ganan las Blancas (MCTS)!"
        elif result == "0-1":
            st.session_state.status_message = "🥳 ¡Ganan las Negras (Tú)!"
        else:
            st.session_state.status_message = "⚖️ Tablas"
        return True
    return False

def debug_callback(iter_num, debug_data):
    """Callback para capturar información de debugging"""
    st.session_state.last_mcts_debug.append(debug_data)

def make_mcts_move():
    """Ejecuta el movimiento del MCTS"""
    if st.session_state.game_over:
        return
    
    board = st.session_state.board
    
    if board.turn != chess.WHITE:
        return
    
    # Resetear debug info
    st.session_state.last_mcts_debug = []
    
    with st.spinner(f'MCTS pensando ({st.session_state.mcts_time}s)...'):
        try:
            with TBLite(st.session_state.tb_path) as tb:
                best_move, stats = mcts_search(
                    board, 
                    time_limit=st.session_state.mcts_time,
                    tb=tb,
                    debug_callback=debug_callback if st.session_state.debug_mode else None
                )
            
            st.session_state.last_mcts_stats = stats
            
            if best_move:
                board.push(best_move)
                st.session_state.move_history.append({
                    'move': best_move.uci(),
                    'player': 'MCTS',
                    'stats': stats
                })
                st.session_state.status_message = f"MCTS jugó: {best_move.uci()}"
                
                if not check_game_over():
                    st.session_state.status_message += " - ¡Tu turno!"
            else:
                st.session_state.status_message = "MCTS no encontró movimiento legal"
                st.session_state.game_over = True
                
        except Exception as e:
            st.error(f"Error en MCTS: {e}")
            st.session_state.status_message = "Error al calcular movimiento"

def handle_user_move(move_uci):
    """Procesa el movimiento del usuario"""
    board = st.session_state.board
    
    if st.session_state.game_over:
        st.warning("El juego ya terminó")
        return False
    
    if board.turn != st.session_state.user_color:
        st.warning("No es tu turno")
        return False
    
    try:
        move = chess.Move.from_uci(move_uci.strip().lower())
        if move in board.legal_moves:
            board.push(move)
            st.session_state.move_history.append({
                'move': move.uci(),
                'player': 'Usuario',
                'stats': None
            })
            st.session_state.status_message = f"Jugaste: {move.uci()}"
            
            if not check_game_over():
                make_mcts_move()
            
            return True
        else:
            st.warning(f"Movimiento ilegal: {move_uci}")
            return False
    except ValueError:
        st.warning(f"Formato inválido: {move_uci}. Usa formato UCI (ej: e2e4)")
        return False

def reset_game(endgame_name, mcts_time):
    """Reinicia el juego"""
    fen = FAMOUS_ENDGAMES[endgame_name]
    st.session_state.board = chess.Board(fen)
    st.session_state.game_over = False
    st.session_state.move_history = []
    st.session_state.mcts_time = mcts_time
    st.session_state.selected_endgame = endgame_name
    st.session_state.last_mcts_debug = []
    st.session_state.last_mcts_stats = {}
    
    if st.session_state.board.turn == chess.WHITE:
        st.session_state.status_message = "MCTS (Blancas) está pensando..."
        st.rerun()
    else:
        st.session_state.status_message = "¡Tu turno!"

# Configuración
st.set_page_config(layout="wide", page_title="MCTS Ajedrez - Debug")
initialize_session_state()

# Título
st.title("♟️ MCTS para Endgames - Con Debugging")
st.markdown("Juega como **Negras** contra MCTS (**Blancas**) y observa su proceso de decisión")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuración")
    
    endgame_choice = st.selectbox(
        "Selecciona un endgame:",
        options=list(FAMOUS_ENDGAMES.keys()),
        index=list(FAMOUS_ENDGAMES.keys()).index(st.session_state.selected_endgame)
    )
    
    mcts_time = st.slider(
        "Tiempo MCTS (segundos):",
        min_value=0.5,
        max_value=10.0,
        value=st.session_state.mcts_time,
        step=0.5
    )
    
    st.session_state.debug_mode = st.checkbox(
        "🐛 Modo Debug (captura detalles)",
        value=st.session_state.debug_mode
    )
    
    st.divider()
    
    # Herramienta de override para debugging
    st.subheader("🔧 Override (Debug)")
    st.caption("Forzar un movimiento específico")
    
    if st.session_state.board.turn == chess.WHITE and not st.session_state.game_over:
        override_move = st.text_input(
            "Movimiento UCI para MCTS:",
            placeholder="ej: h3h4",
            key="override_input"
        )
        
        if st.button("⚡ Forzar Movimiento", use_container_width=True):
            if override_move:
                try:
                    move = chess.Move.from_uci(override_move.strip().lower())
                    if move in st.session_state.board.legal_moves:
                        st.session_state.board.push(move)
                        st.session_state.move_history.append({
                            'move': move.uci(),
                            'player': 'MCTS (manual)',
                            'stats': {'manual': True}
                        })
                        st.session_state.status_message = f"Movimiento forzado: {move.uci()}"
                        if not check_game_over():
                            st.session_state.status_message += " - ¡Tu turno!"
                        st.rerun()
                    else:
                        st.error("Movimiento ilegal")
                except:
                    st.error("Formato inválido")
    
    if st.button("🔄 Reiniciar Juego", use_container_width=True):
        reset_game(endgame_choice, mcts_time)
        st.rerun()
    
    st.divider()
    
    st.subheader("📋 Información")
    st.markdown(f"**Endgame:** {st.session_state.selected_endgame}")
    st.markdown(f"**FEN:** `{st.session_state.board.fen()}`")
    st.markdown(f"**Movimientos:** {st.session_state.board.fullmove_number}")
    
    if st.session_state.move_history:
        st.divider()
        st.subheader("📜 Historial")
        for move_info in reversed(st.session_state.move_history[-10:]):
            icon = "🤖" if move_info['player'] == 'MCTS' else "👤"
            st.text(f"{icon} {move_info['move']}")

# Layout principal
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Tablero")
    display_board()
    
    if st.session_state.game_over:
        st.success(st.session_state.status_message)
    else:
        st.info(st.session_state.status_message)

with col2:
    st.subheader("Controles")
    
    if st.session_state.game_over:
        st.warning("¡Juego terminado!")
        if st.button("🎮 Nueva Partida", use_container_width=True):
            reset_game(st.session_state.selected_endgame, st.session_state.mcts_time)
            st.rerun()
    
    elif st.session_state.board.turn == st.session_state.user_color:
        st.markdown("**🎯 Tu turno (Negras)**")
        
        move_input = st.text_input(
            "Movimiento UCI:",
            placeholder="ej: a7a8",
            key="move_input_field",
            label_visibility="collapsed"
        )
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("✅ Mover", use_container_width=True):
                if move_input:
                    if handle_user_move(move_input):
                        st.rerun()
        
        with col_b:
            if st.button("❌ Limpiar", use_container_width=True):
                st.rerun()
        
        st.markdown("**Movimientos legales:**")
        legal_moves = [m.uci() for m in st.session_state.board.legal_moves]
        st.text(", ".join(legal_moves[:10]))
        if len(legal_moves) > 10:
            st.text(f"... y {len(legal_moves) - 10} más")
    
    else:
        st.markdown("**🤖 Turno de MCTS (Blancas)**")
        st.info("El motor está calculando...")
        make_mcts_move()
        st.rerun()

# Panel de debugging (debajo del tablero)
if st.session_state.last_mcts_stats:
    st.divider()
    st.subheader("🔍 Análisis del Último Movimiento MCTS")
    
    tab1, tab2, tab3 = st.tabs(["📊 Estadísticas", "🌳 Árbol de Decisión", "🎲 Últimas Iteraciones"])
    
    with tab1:
        stats = st.session_state.last_mcts_stats
        
        # Mostrar si encontró mate
        if stats.get('mate_found'):
            st.success("🎯 ¡JAQUE MATE ENCONTRADO!")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Iteraciones", stats.get('iters', 0))
        with col2:
            st.metric("Visitas Raíz", stats.get('root_N', 0))
        with col3:
            st.metric("Visitas Mejor", stats.get('best_visits', 0))
        with col4:
            st.metric("Q Mejor", stats.get('best_Q', 0))
        
        if 'all_moves' in stats:
            st.markdown("**Todos los movimientos evaluados:**")
            moves_data = stats['all_moves']
            
            for move_uci, move_stats in list(moves_data.items())[:10]:
                col_mv, col_n, col_q, col_w = st.columns([2, 1, 1, 1])
                with col_mv:
                    st.text(f"📍 {move_uci}")
                with col_n:
                    st.text(f"N: {move_stats['N']}")
                with col_q:
                    q_val = move_stats['Q']
                    color = "green" if q_val > 0.5 else "red" if q_val < -0.5 else "gray"
                    st.markdown(f"Q: <span style='color:{color}'>{q_val}</span>", 
                              unsafe_allow_html=True)
                with col_w:
                    st.text(f"W: {move_stats['W']}")
            
            # Advertencia solo si REALMENTE todos son 0 Y hay muchas iteraciones
            all_q_zero = all(abs(m['Q']) < 0.01 for m in moves_data.values())
            if all_q_zero and stats.get('iters', 0) > 50:
                st.warning("⚠️ Todos los Q son ~0 después de muchas iteraciones.")
                st.info("💡 La posición puede estar cerca de tablas o en equilibrio perfecto.")
    
    with tab2:
        st.markdown("**Árbol de exploración (top movimientos):**")
        
        if 'all_moves' in stats:
            moves_sorted = sorted(
                stats['all_moves'].items(), 
                key=lambda x: x[1]['N'], 
                reverse=True
            )[:5]
            
            for i, (move_uci, move_stats) in enumerate(moves_sorted, 1):
                n_pct = (move_stats['N'] / stats['root_N'] * 100) if stats['root_N'] > 0 else 0
                
                expander_label = f"{i}. {move_uci} - {move_stats['N']} visitas ({n_pct:.1f}%)"
                with st.expander(expander_label):
                    st.markdown(f"**Estadísticas:**")
                    st.markdown(f"- Visitas (N): {move_stats['N']}")
                    st.markdown(f"- Valor (Q): {move_stats['Q']}")
                    st.markdown(f"- Ganadas (W): {move_stats['W']}")
                    st.markdown(f"- % Exploración: {n_pct:.2f}%")
                    
                    # Barra de progreso (clamp entre 0 y 1, arreglar casos donde n_pct > 100)
                    if n_pct <= 100:
                        progress_val = max(n_pct / 100, 0.0)
                        st.progress(min(progress_val, 1.0))
    
    with tab3:
        if st.session_state.last_mcts_debug:
            st.markdown(f"**Últimas {min(10, len(st.session_state.last_mcts_debug))} iteraciones:**")
            
            num_to_show = st.slider(
                "Número de iteraciones a mostrar:",
                min_value=1,
                max_value=min(20, len(st.session_state.last_mcts_debug)),
                value=min(5, len(st.session_state.last_mcts_debug))
            )
            
            debug_data = st.session_state.last_mcts_debug[-num_to_show:]
            
            for iter_info in reversed(debug_data):
                iter_num = iter_info.get('iteration', '?')
                value = iter_info.get('value', 0)
                
                with st.expander(f"Iteración #{iter_num} - Valor: {value}"):
                    # Selección
                    if 'select_path' in iter_info and iter_info['select_path']:
                        st.markdown("**🎯 Selección:**")
                        for step in iter_info['select_path']:
                            st.text(f"  → {step['move']} (N:{step['N']}, Q:{step['Q']}, W:{step.get('W',0)}, UCT:{step['uct']}, depth:{step.get('depth',0)})")
                    
                    # Expansión
                    if 'expand' in iter_info:
                        exp = iter_info['expand']
                        st.markdown("**🌱 Expansión:**")
                        if exp.get('expanded'):
                            st.text(f"  ✓ Expandido: {exp.get('move', '?')} con prior_Q={exp.get('prior_Q', 0)}")
                        else:
                            st.text(f"  ✗ No expandido (terminal o ya expandido)")
                    
                    # Simulación
                    if 'simulate' in iter_info:
                        sim = iter_info['simulate']
                        st.markdown("**🎲 Simulación:**")
                        st.text(f"  Plies: {sim.get('plies', 0)}")
                        st.text(f"  Resultado: {sim.get('outcome', '?')}")
                        if sim.get('tb_hit'):
                            st.text(f"  ✓ Tablebase hit!")
                        if sim.get('moves'):
                            moves_str = ' '.join(sim['moves'][:8])
                            st.text(f"  Movidas: {moves_str}")
                            if len(sim['moves']) > 8:
                                st.text(f"  ... ({len(sim['moves'])} total)")
        else:
            st.info("No hay datos de debugging. Activa el modo debug y espera al próximo movimiento MCTS.")

# Footer
st.divider()
st.caption("Motor MCTS mejorado con visualización completa del proceso de decisión")