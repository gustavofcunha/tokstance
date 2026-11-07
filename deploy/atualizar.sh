#!/usr/bin/env bash
# Script generico para atualizar o TokStance com novas alteracoes de codigo sem alterar o banco de dados
set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$APP_DIR"

echo "=========================================================="
echo "Atualizando aplicacao TokStance em: $APP_DIR"
echo "=========================================================="

echo "1. Obtendo as alteracoes mais recentes do repositorio Git..."
git fetch origin
git pull origin main

echo "2. Sincronizando dependencias Python..."
if [ -d "$APP_DIR/.venv" ]; then
    "$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"
else
    pip install -q -r "$APP_DIR/requirements.txt"
fi

echo "3. Reiniciando servico da aplicacao..."
if command -v systemctl >/dev/null 2>&1 && [ -f /etc/systemd/system/tokstance.service ]; then
    sudo systemctl daemon-reload || true
    sudo systemctl restart tokstance.service
    echo "Servico tokstance.service reiniciado com sucesso."
else
    echo "Aviso: Servico systemd nao detectado. Se estiver executando manualmente, reinicie o processo."
fi

echo "=========================================================="
echo "Atualizacao de codigo concluida com sucesso!"
echo "=========================================================="
