import streamlit as st
import chess
import chess.svg
import base64
from mcts_core import mcts_search
from tb_utils import TBLite

# Endgames famosos con nombres descriptivos
FAMOUS_ENDGAMES = {
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
        # Por defecto, Rey y Dama vs Rey
        default_fen = FAMOUS_ENDGAMES["Rey y Dama vs Rey"]
        st.session_state.board = chess.Board(default_fen)
        st.session_state.game_over = False
        st.session_state.move_history = []
        st.session_state.status_message = "¡Juego iniciado! Blancas (MCTS) mueven primero."
        st.session_state.user_color = chess.BLACK
        st.session_state.mcts_time = 2.0
        st.session_state.selected_endgame = "Rey y Dama vs Rey"
        st.session_state.tb_path = None

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

def make_mcts_move():
    """Ejecuta el movimiento del MCTS"""
    if st.session_state.game_over:
        return
    
    board = st.session_state.board
    
    # Verificar que sea turno de las blancas
    if board.turn != chess.WHITE:
        return
    
    with st.spinner(f'MCTS pensando ({st.session_state.mcts_time}s)...'):
        try:
            # Usar TBLite si hay ruta configurada
            with TBLite(st.session_state.tb_path) as tb:
                best_move, stats = mcts_search(
                    board, 
                    time_limit=st.session_state.mcts_time,
                    tb=tb
                )
            
            if best_move:
                board.push(best_move)
                st.session_state.move_history.append({
                    'move': best_move.uci(),
                    'player': 'MCTS',
                    'stats': stats
                })
                st.session_state.status_message = f"MCTS jugó: {best_move.uci()}"
                
                # Verificar si el juego terminó
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
            
            # Verificar si terminó el juego
            if not check_game_over():
                # Turno del MCTS
                make_mcts_move()
            
            return True
        else:
            st.warning(f"Movimiento ilegal: {move_uci}")
            return False
    except ValueError:
        st.warning(f"Formato inválido: {move_uci}. Usa formato UCI (ej: e2e4)")
        return False

def reset_game(endgame_name, mcts_time):
    """Reinicia el juego con configuración específica"""
    fen = FAMOUS_ENDGAMES[endgame_name]
    st.session_state.board = chess.Board(fen)
    st.session_state.game_over = False
    st.session_state.move_history = []
    st.session_state.mcts_time = mcts_time
    st.session_state.selected_endgame = endgame_name
    
    # Si las blancas empiezan, hacer el primer movimiento
    if st.session_state.board.turn == chess.WHITE:
        st.session_state.status_message = "MCTS (Blancas) está pensando..."
        st.rerun()
    else:
        st.session_state.status_message = "¡Tu turno!"

# Configuración de la página
st.set_page_config(layout="wide", page_title="MCTS Ajedrez - Endgames")

# Inicialización
initialize_session_state()

# Título
st.title("♟️ MCTS para Endgames de Ajedrez")
st.markdown("Juega como **Negras** contra un motor MCTS que juega como **Blancas**")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # Selector de endgame
    endgame_choice = st.selectbox(
        "Selecciona un endgame famoso:",
        options=list(FAMOUS_ENDGAMES.keys()),
        index=list(FAMOUS_ENDGAMES.keys()).index(st.session_state.selected_endgame)
    )
    
    # Tiempo de pensamiento
    mcts_time = st.slider(
        "Tiempo MCTS (segundos):",
        min_value=0.5,
        max_value=10.0,
        value=st.session_state.mcts_time,
        step=0.5
    )
    
    # Botón de reinicio
    if st.button("🔄 Reiniciar Juego", use_container_width=True):
        reset_game(endgame_choice, mcts_time)
        st.rerun()
    
    st.divider()
    
    # Información del endgame actual
    st.subheader("📋 Información")
    st.markdown(f"**Endgame:** {st.session_state.selected_endgame}")
    st.markdown(f"**FEN:** `{st.session_state.board.fen()}`")
    st.markdown(f"**Movimientos:** {st.session_state.board.fullmove_number}")
    
    # Historial de movimientos
    if st.session_state.move_history:
        st.divider()
        st.subheader("📜 Historial")
        for i, move_info in enumerate(reversed(st.session_state.move_history[-10:])):
            player_icon = "🤖" if move_info['player'] == 'MCTS' else "👤"
            st.text(f"{player_icon} {move_info['move']}")

# Layout principal
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Tablero")
    display_board()
    
    # Mensaje de estado
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
        
        # Input para movimiento UCI
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
        
        # Mostrar movimientos legales
        st.markdown("**Movimientos legales:**")
        legal_moves = [m.uci() for m in st.session_state.board.legal_moves]
        st.text(", ".join(legal_moves[:10]))
        if len(legal_moves) > 10:
            st.text(f"... y {len(legal_moves) - 10} más")
    
    else:
        st.markdown("**🤖 Turno de MCTS (Blancas)**")
        st.info("El motor está calculando...")
        
        # Ejecutar movimiento de MCTS automáticamente
        make_mcts_move()
        st.rerun()

# Footer
st.divider()
st.caption("Motor MCTS con búsqueda de árbol Monte Carlo para endgames de ajedrez")