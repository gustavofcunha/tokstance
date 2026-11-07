#!/usr/bin/env bash
# Script para reiniciar o banco de dados com os dados demonstrativos de avaliacao
set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$APP_DIR"

PYTHON_EXEC="python3"
if [ -d "$APP_DIR/.venv" ]; then
    PYTHON_EXEC="$APP_DIR/.venv/bin/python3"
fi

echo "=========================================================="
echo "Reiniciando banco de dados com especificacoes de demo"
echo "Diretorio: $APP_DIR"
echo "=========================================================="

echo "1. Executando seed de demonstracao..."
PYTHONPATH="$APP_DIR/src:$APP_DIR" "$PYTHON_EXEC" "$APP_DIR/scripts/seed_demo.py" "$@"

echo "2. Reiniciando servico da aplicacao para carregar os novos dados..."
if command -v systemctl >/dev/null 2>&1 && [ -f /etc/systemd/system/tokstance.service ]; then
    sudo systemctl restart tokstance.service
    echo "Servico tokstance.service reiniciado com sucesso."
fi

echo "=========================================================="
echo "Banco de dados demonstrativo reiniciado com sucesso!"
echo "=========================================================="

