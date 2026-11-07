#!/usr/bin/env bash
# Script generico para atualizar o TokStance com novas alteracoes de codigo sem alterar o banco de dados
set -euo pipefail

# 1. Identificar diretorio da aplicacao e do servico de producao
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_APP_DIR=""
if [ -f /etc/systemd/system/tokstance.service ]; then
    SERVICE_APP_DIR=$(grep -E "^WorkingDirectory=" /etc/systemd/system/tokstance.service 2>/dev/null | cut -d= -f2 | tr -d ' ' || true)
fi

# Priorizar o diretorio do servico em producao (/opt/tokstance)
if [ -n "$SERVICE_APP_DIR" ] && [ -d "$SERVICE_APP_DIR" ]; then
    PROD_DIR="$SERVICE_APP_DIR"
elif [ -d "/opt/tokstance" ]; then
    PROD_DIR="/opt/tokstance"
else
    PROD_DIR="$CURRENT_DIR"
fi

echo "=========================================================="
echo "Atualizando aplicacao TokStance"
echo "Diretorio de producao: $PROD_DIR"
echo "Diretorio do script:   $CURRENT_DIR"
echo "=========================================================="

# 2. Atualizar codigo via Git no diretorio de producao
echo "1. Obtendo alteracoes no diretorio de producao ($PROD_DIR)..."
cd "$PROD_DIR"
if [ -d ".git" ]; then
    git fetch origin
    git checkout main || true
    git pull origin main
fi

# Se o script foi executado de outro clone (ex: ~/tokstance), sincronizar tambem
if [ "$CURRENT_DIR" != "$PROD_DIR" ] && [ -d "$CURRENT_DIR/.git" ]; then
    echo "Sincronizando clone local ($CURRENT_DIR)..."
    (cd "$CURRENT_DIR" && git fetch origin && git checkout main 2>/dev/null || true && git pull origin main) || true
fi

# 3. Localizar ambiente virtual Python
echo "2. Sincronizando dependencias Python..."
VENV_DIR=""
if [ -d "$PROD_DIR/.venv" ]; then
    VENV_DIR="$PROD_DIR/.venv"
elif [ -d "/opt/tokstance/.venv" ]; then
    VENV_DIR="/opt/tokstance/.venv"
elif [ -d "$CURRENT_DIR/.venv" ]; then
    VENV_DIR="$CURRENT_DIR/.venv"
else
    echo "Criando ambiente virtual em $PROD_DIR/.venv..."
    python3 -m venv "$PROD_DIR/.venv"
    VENV_DIR="$PROD_DIR/.venv"
fi

"$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel -q || true
"$VENV_DIR/bin/pip" install -q -r "$PROD_DIR/requirements.txt"

# 4. Reiniciar servico systemd
echo "3. Reiniciando servico da aplicacao..."
if command -v systemctl >/dev/null 2>&1 && [ -f /etc/systemd/system/tokstance.service ]; then
    sudo systemctl daemon-reload || true
    sudo systemctl restart tokstance.service
    echo "Servico tokstance.service reiniciado com sucesso."
else
    echo "Aviso: Servico systemd nao detectado. Se estiver executando manualmente, reinicie o processo."
fi

echo "=========================================================="
echo "Atualizacao concluida com sucesso!"
echo "=========================================================="

