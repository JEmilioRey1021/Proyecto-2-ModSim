# -*- coding: utf-8 -*-
"""
Script unificado para ejecutar tests MCTS, generar visualizaciones y análisis de performance.
- Implementa la SIMULACIÓN DE PARTIDA COMPLETA para evaluar el manejo de endgames.
- Elimina el análisis profundo para reducir la salida de archivos.
- Añade nuevas visualizaciones clave para el informe final.

Salida:
- directorios: mcts_report_output/metricas/
- imágenes PNG, raw_results.json, CSV con resúmenes y tablas comparativas

Dependencias: python-chess, matplotlib, seaborn, pandas, numpy
"""

import os
import time
import json
import random
from datetime import datetime
from collections import defaultdict

import chess
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# Importar funciones MCTS desde tu módulo
# mcts_search debe aceptar (board, time_limit=..., seed=None, debug_callback=None)
# y devolver (best_move, stats)
from mcts_core import mcts_search, C_PUCT, ROLLOUT_MAX_PLIES, PRIOR_N, PRIOR_W_MATE, PRIOR_W_CHECK

# --- Configuraciones generales ---
BASE_OUTPUT = "mcts_report_output"
METRICS_DIR = os.path.join(BASE_OUTPUT, "metricas")
# ANALYSIS_DIR eliminado para limpieza
os.makedirs(METRICS_DIR, exist_ok=True)

sns.set_theme(style="whitegrid")
plt.rcParams['figure.dpi'] = 150
plt.rcParams['figure.figsize'] = (11, 7)

# --- Bancos de posiciones extendido ---
# Incluye mates en 1, mates en 2, mates en 3 y posiciones con tablebase relevantes.
TEST_POSITIONS = {
    "Mate en 1 - Dama esquina": {"fen": "7k/6Q1/6K1/8/8/8/8/8 w - - 0 1", "expected_mate_in": 1},
    "Mate en 1 - Torre séptima": {"fen": "6k1/5R2/6K1/8/8/8/8/8 w - - 0 1", "expected_mate_in": 1},
    "Mate en 1 - Dama lateral": {"fen": "7k/8/6KQ/8/8/8/8/8 w - - 0 1", "expected_mate_in": 1},
    "Mate en 1 - Torre banda": {"fen": "k7/8/1K6/8/8/8/8/R7 w - - 0 1", "expected_mate_in": 1},
    "Mate en 1 - Dos torres": {"fen": "k7/8/1K6/8/8/8/R7/R7 w - - 0 1", "expected_mate_in": 1},

    # Mate en 2 (ejemplos simples)
    "Mate en 2 - Basic 1": {"fen": "8/8/8/8/8/4K3/5Q2/6k1 w - - 0 1", "expected_mate_in": 2},
    "Mate en 2 - R vs K": {"fen": "8/8/8/8/8/4K3/5R2/6k1 w - - 0 1", "expected_mate_in": 2},

    # Mate en 3 (un par de casos)
    "Mate en 3 - ejemplo": {"fen": "8/8/8/8/8/3K4/2Q5/6k1 w - - 0 1", "expected_mate_in": 3},

    # Posiciones con oportunidad de promoción
    "Promotion tactic": {"fen": "8/P7/8/8/8/6K1/6P1/6k1 w - - 0 1", "expected_mate_in": None},

    # Posición compleja (más piezas)
    "Complex mid-endgame": {"fen": "r4rk1/1pp1qppp/p1np1n2/4p3/2P1P3/1PN2N2/PB1Q1PPP/R3R1K1 w - - 0 1", "expected_mate_in": None},
    
    # Endgames famosos y factibles (10 nuevos)
    "King and Queen vs King (WTM)": {"fen": "k7/8/K7/Q7/8/8/8/8 w - - 0 1", "expected_mate_in": 10}, # DTM (Depth To Mate) es más largo, pero el MCTS debería ganar.
    "King and Rook vs King (WTM)": {"fen": "k7/8/K7/R7/8/8/8/8 w - - 0 1", "expected_mate_in": 16}, # DTM, el MCTS debería progresar
    "Two Rooks vs King": {"fen": "k7/8/K7/R7/8/8/8/R7 w - - 0 1", "expected_mate_in": 3},
    "King and Pawn endgame 1": {"fen": "8/8/5P2/4K3/8/8/8/k7 w - - 0 1", "expected_mate_in": None}, # Simple promotion
    "King and Pawn endgame 2 (Opposition)": {"fen": "8/8/8/4k3/4K3/8/6P1/8 w - - 0 1", "expected_mate_in": None}, # White wins by pushing pawn
    "Lucena Position": {"fen": "1K6/8/8/R7/8/8/7k/5Q2 w - - 0 1", "expected_mate_in": None}, # Lucena is R vs P
    "Philidor Position (Rook)": {"fen": "8/8/8/8/3R4/8/3P4/k3K3 w - - 0 1", "expected_mate_in": None}, # R vs P, simple win
    "Bishop and Knight vs King (starting)": {"fen": "8/8/8/8/8/5B2/3N4/k3K3 w - - 0 1", "expected_mate_in": 33}, # DTM, but for MCTS it's complex, aiming for progression.
    "Rook vs Pawn on 7th (Rook behind)": {"fen": "8/P7/8/8/8/3R4/8/1k6 w - - 0 1", "expected_mate_in": None}, # White must win
    "Simple Passed Pawn": {"fen": "8/8/8/8/4k3/6K1/8/8 b - - 0 1", "expected_mate_in": None}, # King and Pawn vs King (Black to play, White wins if G2, so change to e4/g3)
    "Simple Passed Pawn 2": {"fen": "8/8/8/8/3K4/6P1/8/5k2 w - - 0 1", "expected_mate_in": None}, # White wins
}

# Más posiciones para diversify pruebas (stalemates y checks)
EXTRA_POSITIONS = {
    "Stalemate trap": {"fen": "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1", "expected_mate_in": None},
}

TEST_POSITIONS.update(EXTRA_POSITIONS)

# --- Helpers ---

def save_figure(fig, path):
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)

# --- SIMULACIÓN DE PARTIDA COMPLETA ---

def run_game_simulation(fen, time_limit_per_move=1.5, max_moves=10):
    """Juega una partida simulada con MCTS (jugador) y un oponente simple hasta mate o límite."""
    board = chess.Board(fen)
    moves_history = []
    
    for i in range(max_moves):
        # 1. Movimiento MCTS
        player_turn = board.turn
        start_time = time.time()
        
        # MCTS siempre juega con su color actual (player_turn)
        best_move, stats = mcts_search(board, time_limit=time_limit_per_move)
        
        if best_move is None:
            # No hay jugadas legales o MCTS falló
            return {'result': 'No move/Error', 'history': moves_history, 'total_moves': i}

        board.push(best_move)
        moves_history.append({'move': best_move.uci(), 'player': 'MCTS', 'time': time.time() - start_time, 'stats': stats, 'is_win_move': board.is_checkmate()})

        if board.is_checkmate():
            return {'result': 'Mate by MCTS', 'history': moves_history, 'total_moves': i+1}
        if board.is_stalemate() or board.is_insufficient_material() or board.halfmove_clock >= 100:
            return {'result': 'Draw by rule', 'history': moves_history, 'total_moves': i+1}

        # 2. Movimiento Oponente (respuesta simple/aleatoria)
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            break
            
        # Oponente: Elige aleatoriamente, pero EVITA el mate en 1 (si es posible)
        safe_moves = []
        for mv in legal_moves:
            test_board = board.copy()
            test_board.push(mv)
            if not test_board.is_checkmate():
                safe_moves.append(mv)
        
        opponent_move = random.choice(safe_moves) if safe_moves else legal_moves[0] # Juega mate en 1 si no hay otra
        
        board.push(opponent_move)
        moves_history.append({'move': opponent_move.uci(), 'player': 'Opponent', 'time': 0, 'stats': {}})

        if board.is_checkmate():
            return {'result': 'Mate by Opponent', 'history': moves_history, 'total_moves': i+2}
        
    return {'result': 'Max moves reached', 'history': moves_history, 'total_moves': len(moves_history)}


# --- Visualizaciones mejoradas (Ahora basadas en Simulación) ---

def plot_mate_detection_rate(all_results, out_path):
    df = []
    for name, runs in all_results.items():
        mates = sum(1 for r in runs if r['mate_found'])
        df.append({'Posición': name, 'Mates': mates, 'Runs': len(runs), 'Rate': mates / len(runs) * 100})
    df = pd.DataFrame(df).sort_values('Rate', ascending=False)

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(data=df, x='Rate', y='Posición', palette='viridis', ax=ax)
    ax.set_xlabel('Tasa de partidas ganadas (%)')
    ax.set_title('Tasa de Éxito de Partida por Posición (MCTS vs. Oponente Simple)')

    for i, row in df.iterrows():
        ax.text(row['Rate'] + 0.5, i, f"{row['Rate']:.0f}%", va='center')

    save_figure(fig, out_path)
    df.to_csv(out_path.replace('.png', '.csv'), index=False)


def plot_iters_vs_time(all_results, out_path):
    rows = []
    for name, runs in all_results.items():
        for r in runs:
            iters = r.get('iterations_first_move', 0)
            time_elapsed = r.get('time_first_move', 0.0)
            if time_elapsed > 0:
                rows.append({'Posición': name, 'Iters_per_s': iters / time_elapsed, 'Iterations': iters, 'Time': time_elapsed})
    df = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(12, 6))
    sns.boxplot(data=df, y='Posición', x='Iters_per_s', palette='Set2', ax=ax)
    ax.set_title('Iteraciones por segundo (Rendimiento MCTS en el primer movimiento)')
    save_figure(fig, out_path)
    df.to_csv(out_path.replace('.png', '.csv'), index=False)


def plot_time_to_mate(all_results, out_path):
    rows = []
    for name, runs in all_results.items():
        mate_times = [r['time_first_move'] for r in runs if r['mate_found']]
        if mate_times:
            rows.append({'Posición': name, 'AvgTime': np.mean(mate_times), 'StdTime': np.std(mate_times)})
    if not rows:
        print('No hay mates para plot_time_to_mate')
        return
    df = pd.DataFrame(rows).sort_values('AvgTime')

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(range(len(df)), df['AvgTime'], yerr=df['StdTime'], capsize=5)
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(df['Posición'], rotation=45, ha='right')
    ax.set_ylabel('Tiempo medio del primer movimiento (s)')
    ax.set_title('Tiempo medio del MCTS en el movimiento ganador inicial')

    plt.subplots_adjust(bottom=0.28)
    save_figure(fig, out_path)
    df.to_csv(out_path.replace('.png', '.csv'), index=False)


def save_summary_table(all_results, out_path):
    rows = []
    for name, runs in all_results.items():
        mates = sum(1 for r in runs if r['mate_found'])
        avg_iters = np.mean([r['iterations_first_move'] for r in runs]) if runs else 0
        avg_time = np.mean([r['time_first_move'] for r in runs]) if runs else 0
        avg_Q = np.mean([r['best_Q_first_move'] for r in runs]) if runs else np.nan
        rows.append({'Posición': name, 'Tasa_Ganada_%': mates / len(runs) * 100, 'Iter_prom_1er_mov': avg_iters, 'Time_prom_s_1er_mov': avg_time, 'Q_prom_1er_mov': avg_Q})
    df = pd.DataFrame(rows).sort_values('Tasa_Ganada_%', ascending=False)

    # Guardar CSV
    df.to_csv(out_path.replace('.png', '.csv'), index=False)

    # Guardar como imagen de tabla
    fig, ax = plt.subplots(figsize=(12, max(4, 0.5 * len(df) + 1)))
    ax.axis('off')
    table = ax.table(cellText=df.round(3).values, colLabels=df.columns, cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    save_figure(fig, out_path)


# --- Nuevos Gráficos Clave para el Informe ---

def plot_success_vs_difficulty(all_results, out_path):
    rows = []
    for name, runs in all_results.items():
        mates = sum(1 for r in runs if r['mate_found'])
        difficulty = TEST_POSITIONS[name].get('expected_mate_in')
        difficulty_str = f"Mate en {difficulty}" if difficulty else "Complejo/Draw"
        rows.append({'Posición': name, 'Tasa_Mate_%': mates / len(runs) * 100, 'Dificultad': difficulty_str})
    
    df = pd.DataFrame(rows).sort_values('Tasa_Mate_%', ascending=False)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    # Usamos Posición para el hue para ver la contribución de cada posición a la dificultad
    sns.barplot(data=df, x='Tasa_Mate_%', y='Dificultad', hue='Posición', dodge=False, palette='cool', ax=ax)
    ax.set_title('Tasa de Éxito por Nivel de Dificultad Teórica (Simulación)')
    ax.set_xlabel('Tasa de Partidas Ganadas (%)')
    ax.legend(title='Posiciones', bbox_to_anchor=(1.05, 1), loc='upper left')
    save_figure(fig, out_path)
    df.to_csv(out_path.replace('.png', '.csv'), index=False)


def plot_moves_to_win_distribution(all_results, out_path):
    rows = []
    for name, runs in all_results.items():
        for r in runs:
            if r['mate_found']:
                # total_moves incluye movimientos de MCTS y del oponente
                rows.append({'Posición': name, 'Total_Moves_a_Mate': r['total_moves']})
    
    if not rows:
        print('No hay mates para plot_moves_to_win_distribution')
        return

    df = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(10, 6))
    # Bins de 2 en 2 para capturar los turnos del MCTS
    sns.histplot(data=df, x='Total_Moves_a_Mate', hue='Posición', multiple='stack', bins=range(1, int(df['Total_Moves_a_Mate'].max() + 3), 1), ax=ax)
    ax.set_title('Distribución de Movimientos para Ganar (MCTS + Oponente)')
    ax.set_xlabel('Total de movimientos en la partida hasta el mate')
    save_figure(fig, out_path)
    df.to_csv(out_path.replace('.png', '.csv'), index=False)


def save_mcts_characteristics(out_path):
    # Asegúrate de que las constantes se importen correctamente desde mcts_core
    data = {
        'Característica': [
            'Constante UCT (C_PUCT)', 
            'Plies Max. en Rollout', 
            'Nodos de Prioridad (N)', 
            'Peso Prioridad Mate (Q)', 
            'Peso Prioridad Jaque (Q)'
        ],
        'Valor': [
            C_PUCT, 
            ROLLOUT_MAX_PLIES, 
            PRIOR_N, 
            PRIOR_W_MATE, 
            PRIOR_W_CHECK
        ]
    }
    df = pd.DataFrame(data)

    # Guardar CSV
    df.to_csv(out_path.replace('.png', '.csv'), index=False)

    # Guardar como imagen de tabla
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.axis('off')
    table = ax.table(cellText=df.values, colLabels=df.columns, cellLoc='left', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    ax.set_title('Características del Algoritmo MCTS (Hiperparámetros)')
    save_figure(fig, out_path)


# --- Función central que corre todo ---

# *** CAMBIO: num_runs se establece a 25 por defecto ***
def run_full_experiment(time_limit=1.5, num_runs=25, seeds=None):
    all_results = {}
    raw_export = {'timestamp': datetime.now().isoformat(), 'positions': {}}
    random.seed(seeds[0] if seeds else 42) # Semilla para la simulación
    
    for name, meta in TEST_POSITIONS.items():
        fen = meta['fen']
        print(f"Simulando partida ({num_runs} veces): {name}")
        
        runs = []
        for i in range(num_runs):
            # Ejecutamos la simulación de juego completo
            game_result = run_game_simulation(fen, time_limit_per_move=time_limit, max_moves=10)
            
            # Recopilar métricas clave del primer movimiento y del resultado final
            first_move_stats = game_result['history'][0]['stats'] if game_result['history'] else {}
            
            # Buscar el tiempo e iteraciones del movimiento ganador (si existe)
            winning_move = next((m for m in game_result['history'] if m.get('is_win_move')), None)
            
            runs.append({
                'run': i + 1,
                'result': game_result['result'],
                'total_moves': game_result['total_moves'],
                'mate_found': game_result['result'] == 'Mate by MCTS',
                # Métricas del primer movimiento para análisis de rendimiento
                'time_first_move': game_result['history'][0]['time'] if game_result['history'] else 0.0,
                'iterations_first_move': first_move_stats.get('iters', 0),
                'best_Q_first_move': first_move_stats.get('best_Q', 0),
                # Stats del movimiento que dio mate
                'time_winning_move': winning_move['time'] if winning_move else np.nan,
                'iterations_winning_move': winning_move['stats'].get('iters', 0) if winning_move else 0
            })
        
        all_results[name] = runs
        raw_export['positions'][name] = runs

    # Guardar raw JSON
    raw_path = os.path.join(METRICS_DIR, f"raw_results_{int(time.time())}.json")
    with open(raw_path, 'w', encoding='utf-8') as f:
        json.dump(raw_export, f, ensure_ascii=False, indent=2)
    print(f"Export raw: {raw_path}")

    # Generar visualizaciones y tablas (basadas en la simulación/primer movimiento)
    plot_mate_detection_rate(all_results, os.path.join(METRICS_DIR, 'mate_detection_rate.png'))
    plot_iters_vs_time(all_results, os.path.join(METRICS_DIR, 'iterations_vs_time.png'))
    plot_time_to_mate(all_results, os.path.join(METRICS_DIR, 'time_of_first_move.png'))
    save_summary_table(all_results, os.path.join(METRICS_DIR, 'summary_table.png'))

    # Nuevos gráficos de simulación de partida
    plot_success_vs_difficulty(all_results, os.path.join(METRICS_DIR, 'success_vs_difficulty.png'))
    plot_moves_to_win_distribution(all_results, os.path.join(METRICS_DIR, 'moves_to_win_distribution.png'))

    # Tabla de características
    save_mcts_characteristics(os.path.join(METRICS_DIR, 'mcts_characteristics_table.png'))

    # Comparativa en heatmap
    rows = []
    for name, runs in all_results.items():
        mates = sum(1 for r in runs if r['mate_found'])
        avg_time_1st = np.mean([r['time_first_move'] for r in runs])
        avg_iters_1st = np.mean([r['iterations_first_move'] for r in runs])
        rows.append({'Posición': name, 'mate_rate': mates / len(runs) * 100, 'avg_time_1st': avg_time_1st, 'avg_iters_1st': avg_iters_1st})
    comp_df = pd.DataFrame(rows).set_index('Posición')
    comp_path = os.path.join(METRICS_DIR, 'comparison_heatmap.png')
    fig, ax = plt.subplots(figsize=(10, max(4, 0.4 * len(comp_df) + 1)))
    sns.heatmap(comp_df[['mate_rate', 'avg_time_1st', 'avg_iters_1st']].astype(float), annot=True, fmt='.1f', cmap='YlGnBu', ax=ax)
    ax.set_title('Comparativa rápida de Simulación y Primer Movimiento')
    save_figure(fig, comp_path)
    comp_df.to_csv(comp_path.replace('.png', '.csv'))

    return all_results

# --- CLI mínima ---

def main():
    print('\n=== MCTS FULL REPORT RUN ===\n')
    # *** CAMBIO: Se llama con num_runs=25 (aunque ya es el default en run_full_experiment) ***
    all_results = run_full_experiment(time_limit=1.5, num_runs=25) 

    print('\nArchivos generados en:', BASE_OUTPUT)
    print('Directorio métricas:', METRICS_DIR)

if __name__ == '__main__':
    # Nota: Asegúrate de que mcts_core.py esté en el mismo directorio.
    main()