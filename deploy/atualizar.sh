#!/usr/bin/env bash
# Script para atualizar o TokStance na VM de producao
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/tokstance}"
cd "$APP_DIR"

echo "=========================================================="
echo "Atualizando TokStance em $APP_DIR"
echo "=========================================================="

echo "1. Obtendo as alteracoes mais recentes do repositorio Git..."
git fetch origin
git pull origin main

echo "2. Atualizando dependencias Python..."
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

echo "3. Atualizando banco de dados relacional com videos reais e usuario do Professor Andre Hora..."
PYTHONPATH="$APP_DIR/src:$APP_DIR" "$APP_DIR/.venv/bin/python3" "$APP_DIR/scripts/seed_demo.py"

echo "4. Reiniciando o servico TokStance no systemd..."
sudo systemctl daemon-reload || true
sudo systemctl restart tokstance.service

echo "=========================================================="
echo "TokStance atualizado com sucesso no servidor!"
echo "Verifique o status com: sudo systemctl status tokstance.service"
echo "=========================================================="
