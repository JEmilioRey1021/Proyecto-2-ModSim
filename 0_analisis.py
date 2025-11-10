import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np

# ==================================================
# Directorios de Archivos
# ==================================================
INPUT_FILE = "mcts_report_output/metricas/raw_results_1762657827.json"
OUTPUT_DIR = "mcts_report_output/plots_adicionales"

# ==================================================
# 1. Carga y Preparación de Datos
# ==================================================

def load_and_preprocess_data(input_file):
    """Carga los datos JSON y los transforma en un DataFrame de Pandas."""
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: El archivo '{input_file}' no se encontró.")
        return None

    # Normalizar los datos anidados
    all_data = []
    for position_name, runs in data['positions'].items():
        for run_data in runs:
            # Incluir el nombre de la posición en cada corrida
            row = {'position': position_name, **run_data}
            all_data.append(row)

    df = pd.DataFrame(all_data)
    
    # Limpieza: Convertir NaN en 'time_winning_move' a 0 o NaN
    # Usaremos NaN para el promedio si el resultado fue 'No move/Error'
    df['time_winning_move'] = df['time_winning_move'].replace({np.nan: 0})
    df['iterations_winning_move'] = df['iterations_winning_move'].replace({np.nan: 0})

    # Crear una columna binaria para el éxito (Mate by MCTS)
    df['success'] = df['result'].apply(lambda x: 1 if x == 'Mate by MCTS' else 0)
    
    return df

# ==================================================
# 2. Funciones de Ploteo
# ==================================================

# --- Éxito y Errores (1-3) ---

def plot_1_success_rate(df, output_dir):
    """Tasa de éxito (Mate by MCTS) por posición (Gráfico de Barras)."""
    success_rate = df.groupby('position')['success'].mean().sort_values(ascending=False)
    plt.figure(figsize=(12, 6))
    sns.barplot(x=success_rate.index, y=success_rate.values, palette="viridis")
    plt.title('1. Tasa de Éxito de MCTS por Posición (Mate Found)')
    plt.ylabel('Tasa de Éxito (0.0 a 1.0)')
    plt.xlabel('Posición de Ajedrez')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '1_success_rate.png'))
    plt.close()

def plot_2_result_distribution(df, output_dir):
    """Distribución de Resultados (Mate, No move/Error, etc.) (Gráfico de Tarta)."""
    results_counts = df['result'].value_counts()
    plt.figure(figsize=(8, 8))
    plt.pie(results_counts, labels=results_counts.index, autopct='%1.1f%%', startangle=90, colors=sns.color_palette("Set2"))
    plt.title('2. Distribución General de Resultados de las Corridas')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '2_result_distribution.png'))
    plt.close()

def plot_3_errors_per_position(df, output_dir):
    """Número de 'No move/Error' por posición (Gráfico de Barras)."""
    error_df = df[df['result'] == 'No move/Error']
    error_counts = error_df.groupby('position').size().sort_values(ascending=False)
    
    if not error_counts.empty:
        plt.figure(figsize=(12, 6))
        sns.barplot(x=error_counts.index, y=error_counts.values, palette="Reds_d")
        plt.title('3. Número de Errores/Fallas por Posición')
        plt.ylabel('Conteo de Errores')
        plt.xlabel('Posición de Ajedrez')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, '3_errors_per_position.png'))
        plt.close()
    else:
        print("No hay errores para graficar.")

# --- Tiempos de Ejecución (4-6) ---

def plot_4_time_first_move_success(df, output_dir):
    """Tiempo promedio para el primer movimiento (solo corridas exitosas) (Gráfico de Barras)."""
    success_df = df[df['success'] == 1]
    avg_time = success_df.groupby('position')['time_first_move'].mean().sort_values(ascending=False)
    plt.figure(figsize=(12, 6))
    sns.barplot(x=avg_time.index, y=avg_time.values, palette="Blues_d")
    plt.title('4. Tiempo Promedio del Primer Movimiento (Solo Éxito)')
    plt.ylabel('Tiempo (segundos)')
    plt.xlabel('Posición de Ajedrez')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '4_avg_time_first_move_success.png'))
    plt.close()

def plot_5_total_time_violin(df, output_dir):
    """Distribución del tiempo total (time_winning_move) por posición (Gráfico de Violín)."""
    # Solo para resultados con un movimiento (Mate by MCTS)
    plot_df = df[(df['total_moves'] > 0) & (df['time_winning_move'] > 0)]
    plt.figure(figsize=(14, 7))
    sns.violinplot(x='position', y='time_winning_move', data=plot_df, palette="Pastel1", inner='quartile')
    plt.title('5. Distribución del Tiempo Total de la Partida por Posición (Solo Éxito)')
    plt.ylabel('Tiempo Total de la Partida (segundos)')
    plt.xlabel('Posición de Ajedrez')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '5_total_time_violin.png'))
    plt.close()

def plot_6_time_vs_total_moves(df, output_dir):
    """Relación entre el tiempo de victoria y el total de movimientos (Gráfico de Dispersión)."""
    # Solo corridas exitosas con más de un movimiento
    plot_df = df[(df['success'] == 1) & (df['total_moves'] > 0)]
    plt.figure(figsize=(10, 6))
    sns.scatterplot(x='total_moves', y='time_winning_move', hue='position', data=plot_df, palette="tab10", s=100)
    plt.title('6. Tiempo de Victoria vs. Número de Movimientos (Solo Éxito)')
    plt.ylabel('Tiempo Total de la Partida (segundos)')
    plt.xlabel('Total de Movimientos')
    plt.legend(title='Posición', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '6_time_vs_total_moves.png'))
    plt.close()

# --- Iteraciones y Calidad (7-9) ---

def plot_7_avg_iterations_first_move(df, output_dir):
    """Número promedio de iteraciones para el primer movimiento (Gráfico de Barras)."""
    avg_iterations = df.groupby('position')['iterations_first_move'].mean().sort_values(ascending=False)
    plt.figure(figsize=(12, 6))
    sns.barplot(x=avg_iterations.index, y=avg_iterations.values, palette="Oranges_d")
    plt.title('7. Iteraciones Promedio para el Primer Movimiento')
    plt.ylabel('Iteraciones MCTS Promedio')
    plt.xlabel('Posición de Ajedrez')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '7_avg_iterations_first_move.png'))
    plt.close()

def plot_8_best_q_first_move_boxplot(df, output_dir):
    """Distribución del valor Q del mejor primer movimiento (Gráfico de Caja)."""
    # Solo corridas donde el valor Q es relevante (puede filtrar por éxito si es necesario)
    plot_df = df[df['best_Q_first_move'] > 0]
    plt.figure(figsize=(12, 6))
    sns.boxplot(x='position', y='best_Q_first_move', data=plot_df, palette="PuRd")
    plt.title('8. Distribución del Valor Q del Mejor Primer Movimiento')
    plt.ylabel('Valor Q del Primer Movimiento')
    plt.xlabel('Posición de Ajedrez')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '8_best_q_first_move_boxplot.png'))
    plt.close()

def plot_9_iterations_winning_move_vs_time(df, output_dir):
    """Relación entre iteraciones totales (winning move) y tiempo (Gráfico de Dispersión)."""
    # Solo corridas exitosas con más de 0 iteraciones
    plot_df = df[(df['success'] == 1) & (df['iterations_winning_move'] > 0)]
    plt.figure(figsize=(10, 6))
    sns.scatterplot(x='iterations_winning_move', y='time_winning_move', hue='position', data=plot_df, palette="Set1", s=100, alpha=0.7)
    plt.title('9. Tiempo de Victoria vs. Iteraciones Totales (Solo Éxito)')
    plt.xlabel('Iteraciones Totales MCTS')
    plt.ylabel('Tiempo Total de la Partida (segundos)')
    plt.legend(title='Posición', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '9_iterations_winning_move_vs_time.png'))
    plt.close()

# --- Análisis Adicional (10-11) ---

def plot_10_moves_per_position_bar(df, output_dir):
    """Conteo de movimientos total por posición (Gráfico de Barras con Desviación Estándar)."""
    plot_df = df[df['total_moves'] > 0]
    plt.figure(figsize=(12, 6))
    # Usar un `estimator` para el promedio y mostrar la desviación estándar
    sns.barplot(x='position', y='total_moves', data=plot_df, errorbar='sd', palette="YlGnBu")
    plt.title('10. Movimientos Promedio por Partida Exitosa (con Desv. Est.)')
    plt.ylabel('Total de Movimientos')
    plt.xlabel('Posición de Ajedrez')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '10_avg_moves_per_position.png'))
    plt.close()

def plot_11_q_vs_time_first_move_success(df, output_dir):
    """Relación entre el valor Q y el tiempo del primer movimiento (Gráfico de Dispersión)."""
    plot_df = df[(df['success'] == 1) & (df['best_Q_first_move'] > 0) & (df['time_first_move'] > 0)]
    plt.figure(figsize=(10, 6))
    sns.scatterplot(x='time_first_move', y='best_Q_first_move', hue='position', data=plot_df, palette="Spectral", s=100)
    plt.title('11. Valor Q vs. Tiempo de Cálculo del Primer Movimiento (Solo Éxito)')
    plt.ylabel('Valor Q del Primer Movimiento')
    plt.xlabel('Tiempo del Primer Movimiento (segundos)')
    plt.legend(title='Posición', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '11_q_vs_time_first_move.png'))
    plt.close()


# ==================================================
# 3. Función Principal de Ejecución
# ==================================================

def generate_mcts_plots(input_file, output_dir):
    """Función principal para cargar datos y generar todos los gráficos."""
    print("Iniciando la generación de gráficos...")
    
    # 1. Crear el directorio de salida si no existe
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Directorio de salida creado: {output_dir}")

    # 2. Cargar y preparar los datos
    df = load_and_preprocess_data(input_file)
    if df is None:
        return

    # 3. Generar gráficos (¡más de 10!)
    print(f"Datos cargados. Total de corridas: {len(df)}")
    
    # Éxito y Errores
    plot_1_success_rate(df, output_dir)
    plot_2_result_distribution(df, output_dir)
    plot_3_errors_per_position(df, output_dir)
    
    # Tiempos de Ejecución
    plot_4_time_first_move_success(df, output_dir)
    plot_5_total_time_violin(df, output_dir)
    plot_6_time_vs_total_moves(df, output_dir)
    
    # Iteraciones y Calidad
    plot_7_avg_iterations_first_move(df, output_dir)
    plot_8_best_q_first_move_boxplot(df, output_dir)
    plot_9_iterations_winning_move_vs_time(df, output_dir)
    
    # Análisis Adicional
    plot_10_moves_per_position_bar(df, output_dir)
    plot_11_q_vs_time_first_move_success(df, output_dir)

    print(f"\n¡Gráficos generados con éxito! Revise la carpeta: {output_dir}")

# Ejecutar la función principal
if __name__ == "__main__":
    generate_mcts_plots(INPUT_FILE, OUTPUT_DIR)