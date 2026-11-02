#!/usr/bin/env bash
#configuracao automatizada da vm gcp compute engine para o tokstance
set -euo pipefail

echo "=========================================================="
echo "Iniciando provisionamento da VM GCP para TokStance"
echo "=========================================================="

#atualizar pacotes do sistema
sudo apt-get update -y
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    sqlite3 \
    curl \
    ca-certificates \
    libnspr4 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2

#diretorio da aplicacao
APP_DIR="/opt/tokstance"
REPO_URL="https://github.com/gustavofcunha/ufmg-stance-tiktok.git"

if [ ! -d "$APP_DIR" ]; then
    echo "Clonando repositorio em $APP_DIR..."
    sudo git clone "$REPO_URL" "$APP_DIR"
    sudo chown -R "$USER:$USER" "$APP_DIR"
else
    echo "Atualizando repositorio existente em $APP_DIR..."
    cd "$APP_DIR"
    git fetch origin
    git checkout main || true
fi

cd "$APP_DIR"

#ambiente virtual python
if [ ! -d "$APP_DIR/.venv" ]; then
    echo "Criando ambiente virtual python em $APP_DIR/.venv..."
    python3 -m venv "$APP_DIR/.venv"
fi

echo "Instalando dependencias python..."
"$APP_DIR/.venv/bin/pip" install --upgrade pip setuptools wheel
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

#garantir diretorio de dados
mkdir -p "$APP_DIR/data"

#popular banco de dados relacional com dados de avaliacao
echo "Executando seed de avaliacao..."
PYTHONPATH="$APP_DIR/src:$APP_DIR" "$APP_DIR/.venv/bin/python3" "$APP_DIR/scripts/seed_demo.py"

#configurar servico systemd
echo "Configurando systemd service..."
sudo cp "$APP_DIR/deploy/tokstance.service" /etc/systemd/system/tokstance.service
#ajustar usuario no arquivo de servico para o usuario corrente
sudo sed -i "s/User=gustavocunha/User=$USER/g" /etc/systemd/system/tokstance.service
sudo sed -i "s|WorkingDirectory=/opt/tokstance|WorkingDirectory=$APP_DIR|g" /etc/systemd/system/tokstance.service
sudo sed -i "s|/opt/tokstance|$APP_DIR|g" /etc/systemd/system/tokstance.service

sudo systemctl daemon-reload
sudo systemctl enable tokstance.service
sudo systemctl restart tokstance.service

echo "=========================================================="
echo "TokStance provisionado com sucesso na VM!"
echo "Status do servico:"
sudo systemctl status tokstance.service --no-pager || true
echo "=========================================================="
