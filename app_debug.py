import streamlit as st
import chess
import chess.svg
import base64
import json
from mcts_core import mcts_search
from tb_utils import TBLite
import plotly.graph_objects as go
import plotly.express as px

# Endgames famosos con soluciones teóricas
FAMOUS_ENDGAMES = {
    "Mate de pasillo (negras ganan)": {
        "fen": "1Q6/p1p2rk1/5q2/2pp2pp/6b1/1PPBR3/P4PPP/RN5K b - - 0 1",
        "theoretical_moves": ["f6f1", "h1g2", "f1f2"],  # Ejemplo simplificado
        "description": "Las negras tienen ventaja material decisiva",
        "difficulty": "Fácil",
        "expected_moves": 3
    },
    "Rey y Dama vs Rey": {
        "fen": "7k/5Q2/6K1/8/8/8/8/8 w - - 0 1",
        "theoretical_moves": ["f7f8"],  # Mate en 1
        "description": "Mate básico con dama - mate en 1",
        "difficulty": "Muy Fácil",
        "expected_moves": 1
    },
    "Rey y Torre vs Rey": {
        "fen": "8/8/8/8/8/7R/3K4/k7 w - - 0 1",
        "theoretical_moves": ["h3a3", "a1b1", "a3a1"],  # Mate en 2
        "description": "Mate básico con torre - escalera hacia la banda",
        "difficulty": "Fácil",
        "expected_moves": 3
    },
    "La posición de Lucena": {
        "fen": "4K3/1k2P3/8/8/8/8/6R1/5r2 w - - 0 1", 
        "theoretical_moves": [],  # Mate en 2
        "description": "Construir el puente",
        "difficulty": "Fácil",
        "expected_moves": 3
    },

    "Rey y 2 Torres vs Rey": {
        "fen": "8/8/8/8/8/6RR/3K4/k7 w - - 0 1",
        "theoretical_moves": ["g3a3"],  # Mate en 1
        "description": "Mate rápido con dos torres",
        "difficulty": "Muy Fácil",
        "expected_moves": 1
    },
    "Rey y Alfil + Caballo vs Rey": {
        "fen": "8/8/8/8/8/5BN1/3K4/k7 w - - 0 1",
        "theoretical_moves": ["g3e2", "a1b1", "f3e4", "b1c1", "e2c3"],
        "description": "Uno de los mates más difíciles - requiere coordinación perfecta",
        "difficulty": "Muy Difícil",
        "expected_moves": 20
    },
    "Rey y 2 Alfiles vs Rey": {
        "fen": "8/8/8/8/8/6BB/3K4/k7 w - - 0 1",
        "theoretical_moves": ["g3e1", "a1b2", "h3f1"],
        "description": "Mate con dos alfiles - acorralar al rey",
        "difficulty": "Difícil",
        "expected_moves": 10
    },
    "Lucena (Torre)": {
        "fen": "1K6/1P1k4/8/8/8/8/r7/2R5 w - - 0 1",
        "theoretical_moves": ["c1c4", "a2a1", "b8b7", "a1b1", "b7c7"],
        "description": "Posición ganadora clásica con torre",
        "difficulty": "Medio",
        "expected_moves": 8
    },
    "Philidor (Defensa Torre)": {
        "fen": "3k4/R7/3K4/8/8/8/r7/8 b - - 0 1",
        "theoretical_moves": ["a2a6", "d6d7", "a6a7"],
        "description": "Defensa de tablas con torre - posición pasiva",
        "difficulty": "Medio",
        "expected_moves": 15
    },
    "Rey y Peón vs Rey (ganador)": {
        "fen": "8/8/8/8/3k4/3P4/3K4/8 w - - 0 1",
        "theoretical_moves": ["d2c3", "d4e5", "c3c4", "e5e6", "c4c5"],
        "description": "Peón pasado con rey apoyando - regla del cuadrado",
        "difficulty": "Fácil",
        "expected_moves": 8
    },
    "Mate de la Coz": {
        "fen": "8/8/8/8/8/6N1/5K1k/8 w - - 0 1",
        "theoretical_moves": ["g3f5", "h2h3", "f2g1", "h3h2", "g1f1", "h2h1", "f5g3"],
        "description": "Mate con caballo requiriendo rey enemigo en esquina",
        "difficulty": "Muy Difícil",
        "expected_moves": 15
    },
    "Torre y Peón vs Torre (Tablas Philidor)": {
        "fen": "8/4k3/8/4pP2/4K3/8/8/r7 b - - 0 1",
        "theoretical_moves": ["a1a5", "e4d3", "a5f5", "d3e3", "f5f1"],
        "description": "Defensa de tablas cortando al rey",
        "difficulty": "Medio",
        "expected_moves": 20
    },
    "Mate de Anastasia": {
        "fen": "5rk1/5Npp/8/8/8/8/5RPP/6K1 w - - 0 1",
        "theoretical_moves": ["f2f8", "g8h7", "f8f7"],
        "description": "Patrón de mate con torre y caballo",
        "difficulty": "Fácil",
        "expected_moves": 3
    }
}

def initialize_session_state():
    """Inicializa el estado de la sesión"""
    if 'board' not in st.session_state:
        default_endgame = "Rey y Dama vs Rey"
        default_fen = FAMOUS_ENDGAMES[default_endgame]["fen"]
        st.session_state.board = chess.Board(default_fen)
        st.session_state.game_over = False
        st.session_state.move_history = []
        st.session_state.status_message = "¡Juego iniciado! Blancas (MCTS) mueven primero."
        st.session_state.user_color = chess.BLACK
        st.session_state.mcts_time = 2.0
        st.session_state.selected_endgame = default_endgame
        st.session_state.tb_path = None
        st.session_state.debug_mode = True
        st.session_state.last_mcts_debug = []
        st.session_state.last_mcts_stats = {}
        st.session_state.game_start_fen = default_fen
        st.session_state.moves_to_mate = None
        st.session_state.mate_achieved = False

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
        
        mcts_moves = len([m for m in st.session_state.move_history if m['player'] in ['MCTS', 'MCTS (manual)']])
        
        if result == "1-0":
            st.session_state.status_message = "🎉 ¡Ganan las Blancas (MCTS)!"
            st.session_state.mate_achieved = True
            st.session_state.moves_to_mate = mcts_moves
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
                
                if stats.get('mate_found'):
                    st.session_state.status_message = f"🎯 MCTS jugó: {best_move.uci()} - ¡JAQUE MATE!"
                else:
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
    endgame_data = FAMOUS_ENDGAMES[endgame_name]
    fen = endgame_data["fen"]
    
    st.session_state.board = chess.Board(fen)
    st.session_state.game_over = False
    st.session_state.move_history = []
    st.session_state.mcts_time = mcts_time
    st.session_state.selected_endgame = endgame_name
    st.session_state.last_mcts_debug = []
    st.session_state.last_mcts_stats = {}
    st.session_state.game_start_fen = fen
    st.session_state.moves_to_mate = None
    st.session_state.mate_achieved = False
    
    if st.session_state.board.turn == chess.WHITE:
        st.session_state.status_message = "MCTS (Blancas) está pensando..."
        st.rerun()
    else:
        st.session_state.status_message = "¡Tu turno!"

# Configuración
st.set_page_config(layout="wide", page_title="MCTS Ajedrez - Análisis Completo")
initialize_session_state()

# Título
st.title("♟️ MCTS para Endgames - Análisis Teórico")
st.markdown("Juega como **Negras** contra MCTS (**Blancas**) y compara con la teoría")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuración")
    
    endgame_choice = st.selectbox(
        "Selecciona un endgame:",
        options=list(FAMOUS_ENDGAMES.keys()),
        index=list(FAMOUS_ENDGAMES.keys()).index(st.session_state.selected_endgame)
    )
    
    # Mostrar info del endgame seleccionado
    endgame_info = FAMOUS_ENDGAMES[endgame_choice]
    st.info(f"**{endgame_info['description']}**\n\nDificultad: {endgame_info['difficulty']}\nMovidas esperadas: ~{endgame_info['expected_moves']}")
    
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
    
    # Override tool
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
            icon = "🤖" if 'MCTS' in move_info['player'] else "👤"
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

# Panel principal de análisis
st.divider()
st.header("📊 Análisis Completo")

# Crear tabs
tabs = st.tabs([
    "📈 Comparación Teórica",
    "📊 Estadísticas MCTS",
    "🌳 Árbol de Decisión",
    "🎲 Iteraciones Debug"
])

# TAB 1: Comparación Teórica
with tabs[0]:
    st.subheader("🎯 Análisis vs Teoría de Endgames")
    
    endgame_data = FAMOUS_ENDGAMES[st.session_state.selected_endgame]
    theoretical_moves = endgame_data["theoretical_moves"]
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    mcts_moves = [m['move'] for m in st.session_state.move_history if 'MCTS' in m['player']]
    user_moves = [m['move'] for m in st.session_state.move_history if m['player'] == 'Usuario']
    
    with col1:
        accuracy = 0
        if theoretical_moves and mcts_moves:
            matches = sum(1 for i, m in enumerate(mcts_moves) if i < len(theoretical_moves) and m == theoretical_moves[i])
            accuracy = (matches / min(len(mcts_moves), len(theoretical_moves))) * 100
        st.metric("Precisión MCTS", f"{accuracy:.1f}%")
    
    with col2:
        st.metric("Movidas MCTS", len(mcts_moves))
    
    with col3:
        expected = endgame_data["expected_moves"]
        efficiency = (expected / max(len(mcts_moves), 1)) * 100 if mcts_moves else 0
        st.metric("Eficiencia", f"{min(efficiency, 100):.1f}%")
    
    with col4:
        if st.session_state.mate_achieved:
            st.metric("Mate en", f"{st.session_state.moves_to_mate} movidas", delta="✓")
        else:
            st.metric("Estado", "En progreso" if not st.session_state.game_over else "Incompleto")
    
    st.divider()
    
    # Comparación de secuencias
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("**🎓 Secuencia Teórica**")
        if theoretical_moves:
            for i, move in enumerate(theoretical_moves[:10], 1):
                status = ""
                if i-1 < len(mcts_moves):
                    if mcts_moves[i-1] == move:
                        status = "✅"
                    else:
                        status = "❌"
                st.text(f"{i}. {move} {status}")
            if len(theoretical_moves) > 10:
                st.text(f"... ({len(theoretical_moves)} total)")
        else:
            st.info("No hay línea teórica definida para este endgame")
    
    with col_right:
        st.markdown("**🤖 Secuencia MCTS**")
        if mcts_moves:
            for i, move in enumerate(mcts_moves[:10], 1):
                status = ""
                if i-1 < len(theoretical_moves):
                    if move == theoretical_moves[i-1]:
                        status = "✅"
                    else:
                        status = f"❌ (esperado: {theoretical_moves[i-1]})"
                st.text(f"{i}. {move} {status}")
            if len(mcts_moves) > 10:
                st.text(f"... ({len(mcts_moves)} total)")
        else:
            st.info("MCTS aún no ha jugado")
    
    st.divider()
    
    # Gráfico de convergencia
    if len(mcts_moves) > 0:
        st.markdown("**📉 Convergencia hacia la Teoría**")
        
        convergence_data = []
        for i in range(len(mcts_moves)):
            matches = sum(1 for j in range(i+1) if j < len(theoretical_moves) and mcts_moves[j] == theoretical_moves[j])
            acc = (matches / (i+1)) * 100
            convergence_data.append(acc)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=list(range(1, len(convergence_data) + 1)),
            y=convergence_data,
            mode='lines+markers',
            name='Precisión',
            line=dict(color='royalblue', width=3),
            marker=dict(size=8)
        ))
        
        fig.update_layout(
            title="Precisión del MCTS por Movida",
            xaxis_title="Número de Movida",
            yaxis_title="Precisión (%)",
            yaxis=dict(range=[0, 105]),
            height=300
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Tabla de análisis detallado
    if st.session_state.last_mcts_stats and 'all_moves' in st.session_state.last_mcts_stats:
        st.divider()
        st.markdown("**🔍 Análisis del Último Movimiento**")
        
        moves_data = st.session_state.last_mcts_stats['all_moves']
        
        # Verificar si algún movimiento teórico fue considerado
        theoretical_considered = []
        for theo_move in theoretical_moves[:3]:
            if theo_move in moves_data:
                theoretical_considered.append({
                    'Movimiento': theo_move,
                    'Visitas': moves_data[theo_move]['N'],
                    'Valor Q': moves_data[theo_move]['Q'],
                    'Prioridad': '🎓 Teórico'
                })
        
        if theoretical_considered:
            st.markdown("**Movimientos Teóricos Evaluados:**")
            import pandas as pd
            df_theo = pd.DataFrame(theoretical_considered)
            st.dataframe(df_theo, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ El MCTS no consideró los movimientos teóricos en su evaluación")

# TAB 2: Estadísticas MCTS
with tabs[1]:
    if st.session_state.last_mcts_stats:
        stats = st.session_state.last_mcts_stats
        
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
            st.metric("Q Mejor", round(stats.get('best_Q', 0), 3))
        
        if 'all_moves' in stats:
            st.divider()
            st.markdown("**Top 10 Movimientos Evaluados:**")
            
            moves_data = list(stats['all_moves'].items())[:10]
            
            for move_uci, move_stats in moves_data:
                with st.expander(f"🔹 {move_uci} - N:{move_stats['N']} Q:{move_stats['Q']:.3f}"):
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Visitas", move_stats['N'])
                    with col_b:
                        st.metric("Valor Q", round(move_stats['Q'], 3))
                    with col_c:
                        st.metric("W (ganadas)", round(move_stats['W'], 2))
                    
                    if move_stats.get('is_mate'):
                        st.success("✅ Este movimiento da JAQUE MATE")
                    
                    # Progress bar
                    pct = (move_stats['N'] / stats['root_N'] * 100) if stats['root_N'] > 0 else 0
                    st.progress(min(pct / 100, 1.0))
                    st.caption(f"Exploración: {pct:.1f}%")
            
            # Gráfico de distribución de visitas
            st.divider()
            st.markdown("**📊 Distribución de Exploraciones**")
            
            top_moves = list(stats['all_moves'].items())[:8]
            moves_names = [m[0] for m in top_moves]
            visits = [m[1]['N'] for m in top_moves]
            
            fig = go.Figure(data=[
                go.Bar(x=moves_names, y=visits, marker_color='lightblue')
            ])
            fig.update_layout(
                title="Visitas por Movimiento (Top 8)",
                xaxis_title="Movimiento",
                yaxis_title="Número de Visitas",
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Espera a que MCTS haga un movimiento para ver estadísticas")

# TAB 3: Árbol de Decisión
with tabs[2]:
    st.markdown("**🌳 Árbol de Exploración (Top Movimientos)**")
    
    if 'all_moves' in st.session_state.last_mcts_stats:
        stats = st.session_state.last_mcts_stats
        moves_sorted = sorted(
            stats['all_moves'].items(), 
            key=lambda x: x[1]['N'], 
            reverse=True
        )[:6]
        
        for i, (move_uci, move_stats) in enumerate(moves_sorted, 1):
            n_pct = (move_stats['N'] / stats['root_N'] * 100) if stats['root_N'] > 0 else 0
            
            expander_label = f"{i}. {move_uci} - {move_stats['N']} visitas ({n_pct:.1f}%) | Q: {move_stats['Q']:.3f}"
            
            with st.expander(expander_label):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**📊 Estadísticas**")
                    st.markdown(f"- Visitas (N): {move_stats['N']}")
                    st.markdown(f"- Valor (Q): {move_stats['Q']:.3f}")
                    st.markdown(f"- Ganadas (W): {move_stats['W']:.2f}")
                    if move_stats.get('is_mate'):
                        st.markdown("- **✅ JAQUE MATE**")
                
                with col2:
                    st.markdown("**📈 Métricas**")
                    st.markdown(f"- % Exploración: {n_pct:.2f}%")
                    st.markdown(f"- Score: {move_stats.get('score', 0):.2f}")
                    win_rate = ((move_stats['Q'] + 1) / 2) * 100
                    st.markdown(f"- Win Rate: {win_rate:.1f}%")
                
                with col3:
                    st.markdown("**📊 Visualización**")
                    st.progress(min(n_pct / 100, 1.0))
                    
                    # Mini gráfico de Q value
                    q_normalized = (move_stats['Q'] + 1) / 2
                    color = "green" if move_stats['Q'] > 0.3 else "red" if move_stats['Q'] < -0.3 else "gray"
                    st.markdown(f"<div style='background-color:{color};height:20px;width:{q_normalized*100}%;'></div>", unsafe_allow_html=True)
    else:
        st.info("Espera a que MCTS haga un movimiento")

# TAB 4: Iteraciones Debug
with tabs[3]:
    if st.session_state.last_mcts_debug:
        st.markdown(f"**🔬 Últimas Iteraciones (Total: {len(st.session_state.last_mcts_debug)})**")
        
        num_to_show = st.slider(
            "Número de iteraciones a mostrar:",
            min_value=1,
            max_value=min(20, len(st.session_state.last_mcts_debug)),
            value=min(5, len(st.session_state.last_mcts_debug)),
            key="debug_slider"
        )
        
        debug_data = st.session_state.last_mcts_debug[-num_to_show:]
        
        for iter_info in reversed(debug_data):
            iter_num = iter_info.get('iteration', '?')
            value = iter_info.get('value', 0)
            
            # Color según valor
            value_color = "🟢" if value > 0.5 else "🔴" if value < -0.5 else "🟡"
            
            with st.expander(f"{value_color} Iteración #{iter_num} - Valor: {value:.3f}"):
                # Selección
                if 'select_path' in iter_info and iter_info['select_path']:
                    st.markdown("**🎯 Fase de Selección:**")
                    for step in iter_info['select_path']:
                        uct_str = step['uct'] if step['uct'] != 'INF' else '∞'
                        mate_indicator = " 👑" if step.get('is_mate') else ""
                        st.text(f"  → {step['move']} (N:{step['N']}, Q:{step['Q']:.3f}, UCT:{uct_str}, depth:{step['depth']}){mate_indicator}")
                
                # Expansión
                if 'expand' in iter_info:
                    exp = iter_info['expand']
                    st.markdown("**🌱 Fase de Expansión:**")
                    if exp.get('expanded'):
                        mate_str = " - ¡MATE ENCONTRADO! 👑" if exp.get('is_mate') else ""
                        st.text(f"  ✓ Expandido: {exp.get('move', '?')} con prior_Q={exp.get('prior_Q', 0):.3f}{mate_str}")
                        if exp.get('total_mates_found', 0) > 1:
                            st.text(f"  🎯 Total de mates encontrados: {exp['total_mates_found']}")
                    else:
                        st.text(f"  ✗ No expandido (terminal o ya expandido)")
                
                # Simulación
                if 'simulate' in iter_info:
                    sim = iter_info['simulate']
                    st.markdown("**🎲 Fase de Simulación:**")
                    st.text(f"  Plies: {sim.get('plies', 0)}")
                    st.text(f"  Resultado: {sim.get('outcome', '?')}")
                    if sim.get('tb_hit'):
                        st.text(f"  ✓ Tablebase consultada")
                    if sim.get('moves'):
                        moves_str = ' '.join(sim['moves'][:10])
                        st.text(f"  Secuencia: {moves_str}")
                        if len(sim['moves']) > 10:
                            st.text(f"  ... ({len(sim['moves'])} total)")
                
                # Backpropagation
                if 'backprop_node' in iter_info:
                    st.markdown("**⬆️ Backpropagation:**")
                    st.text(f"  Nodo: {iter_info['backprop_node']}")
    else:
        st.info("No hay datos de debugging. Activa el modo debug y espera al próximo movimiento MCTS.")

# Footer con resumen de rendimiento
st.divider()

if st.session_state.move_history:
    st.subheader("📊 Resumen de Rendimiento Global")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total_moves = len(st.session_state.move_history)
    mcts_moves_total = len([m for m in st.session_state.move_history if 'MCTS' in m['player']])
    
    with col1:
        st.metric("Total Movidas", total_moves)
    
    with col2:
        st.metric("Movidas MCTS", mcts_moves_total)
    
    with col3:
        avg_iters = sum(m['stats'].get('iters', 0) for m in st.session_state.move_history if m.get('stats') and not m['stats'].get('manual')) / max(mcts_moves_total, 1)
        st.metric("Promedio Iteraciones", f"{avg_iters:.0f}")
    
    with col4:
        mates_found = sum(1 for m in st.session_state.move_history if m.get('stats') and m['stats'].get('mate_found'))
        st.metric("Mates Detectados", mates_found)
    
    with col5:
        if st.session_state.game_over and st.session_state.mate_achieved:
            expected = FAMOUS_ENDGAMES[st.session_state.selected_endgame]['expected_moves']
            performance = (expected / st.session_state.moves_to_mate * 100) if st.session_state.moves_to_mate > 0 else 0
            st.metric("Performance", f"{min(performance, 100):.0f}%")
        else:
            st.metric("Estado", "En curso")
    
    # Gráfico de evolución de Q values
    if any(m.get('stats') and 'best_Q' in m['stats'] for m in st.session_state.move_history):
        st.divider()
        st.markdown("**📈 Evolución de Valores Q del MCTS**")
        
        q_values = []
        move_numbers = []
        for i, m in enumerate(st.session_state.move_history):
            if m.get('stats') and 'best_Q' in m['stats'] and 'MCTS' in m['player']:
                q_values.append(m['stats']['best_Q'])
                move_numbers.append(i + 1)
        
        if q_values:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=move_numbers,
                y=q_values,
                mode='lines+markers',
                name='Valor Q',
                line=dict(color='green', width=2),
                marker=dict(size=6),
                fill='tozeroy',
                fillcolor='rgba(0,255,0,0.1)'
            ))
            
            fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Equilibrio")
            
            fig.update_layout(
                title="Confianza del MCTS a lo largo del juego",
                xaxis_title="Número de Movida",
                yaxis_title="Valor Q",
                height=300,
                yaxis=dict(range=[-1.1, 1.1])
            )
            
            st.plotly_chart(fig, use_container_width=True)

st.caption("🤖 Motor MCTS mejorado con análisis teórico completo | Modelación y Simulación")