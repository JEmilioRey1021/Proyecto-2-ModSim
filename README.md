
# Paso 3: Integración con Syzygy (WDL/DTZ) + evaluación de jugadas

Objetivo: comparar cada jugada (tuya y del MCTS) contra la “verdad” de finales.
- WDL: 2 = gana el bando al mover, 1 = tablas, 0 = pierde
- DTZ: distancia a cambiar el contador 50-movs (avanza hacia mate/empate)

## Qué hace
- Muestra `WDL/DTZ` del estado actual (si la posición está en TB).
- Marca tu jugada y la del bot como **ÓPTIMA** o **Subóptima**.
- Guarda logs con evaluación antes/después de cada jugada.

## Requisitos
- Tener una carpeta local con **Syzygy tablebases** (3–5 piezas).

## Instalar
```
pip install -r requirements.txt
```

## Ejecutar
```
python play_cli_tb.py --mcts-time 1.0 --you-play white --syzygy-dir "C:/ruta/a/syzygy"
```
Opciones:
- `--fen "<FEN>"` para iniciar desde una posición concreta
- `--mcts-time 0.5` tiempo (s) por jugada del bot
- `--syzygy-dir` ruta a la carpeta con archivos `.rtbw/.rtbz`

Salida:
- En consola: WDL/DTZ, si la jugada fue **ÓPTIMA** o no.
- En `logs/game_tb_*.jsonl`: registro estructurado para métricas.

Siguiente (Paso 4): UI web con chessboard.js + selector de escenarios (Lucena/Philidor).
