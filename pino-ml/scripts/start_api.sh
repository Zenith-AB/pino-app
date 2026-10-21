#!/usr/bin/env bash
# Script para iniciar la API de ML de Pino en modo desarrollo o producción
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"
export PYTHONPATH="$DIR/src:/home/zenith/Proyectos/Pino/pino-ml/.venv/lib/python3.14/site-packages:$PYTHONPATH"

HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-8000}

echo "=== Iniciando Pino ML & PISA Analytics API ==="
echo "Host: $HOST"
echo "Port: $PORT"
echo "Directorio raíz: $DIR"

python3 -m uvicorn pino_ml.api.main:app --host "$HOST" --port "$PORT" --reload
