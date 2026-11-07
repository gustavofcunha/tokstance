#!/usr/bin/env bash
#configuracao automatizada da vm gcp compute engine para o tokstance
set -euo pipefail

DOMAIN="${1:-tokstance.duckdns.org}"

echo "=========================================================="
echo "Iniciando provisionamento da VM GCP para TokStance"
echo "Dominio configurado: $DOMAIN"
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
    nginx \
    certbot \
    python3-certbot-nginx \
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
REPO_URL="https://github.com/gustavofcunha/tokstance.git"

if [ ! -d "$APP_DIR" ]; then
    echo "Clonando repositorio em $APP_DIR..."
    sudo git clone "$REPO_URL" "$APP_DIR"
    sudo chown -R "$USER:$USER" "$APP_DIR"
else
    echo "Atualizando repositorio existente em $APP_DIR..."
    cd "$APP_DIR"
    git fetch origin
    git checkout main || true
    git pull origin main || true
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

#configurar nginx como reverse proxy
echo "Configurando Nginx como proxy reverso para a porta 7860..."
cat << 'EOF' | sudo tee /etc/nginx/sites-available/tokstance
server {
    listen 80;
    listen [::]:80;
    server_name __DOMAIN__ _;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:7860;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
EOF

sudo sed -i "s|__DOMAIN__|$DOMAIN|g" /etc/nginx/sites-available/tokstance
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/tokstance /etc/nginx/sites-enabled/tokstance
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

#obter certificado SSL/HTTPS com Certbot (Let's Encrypt)
echo "Configurando certificado SSL/HTTPS gratuito com Let's Encrypt (Certbot)..."
HTTPS_HABILITADO=false
if sudo certbot --nginx \
    -d "$DOMAIN" \
    --non-interactive \
    --agree-tos \
    --register-unsafely-without-email \
    --redirect; then
    HTTPS_HABILITADO=true
    echo "Certificado SSL emitido e configurado com sucesso!"
else
    echo "Aviso: Nao foi possivel obter o certificado SSL automaticamente."
    echo "A aplicacao continuara disponivel via HTTP normal na porta 80."
fi

echo "=========================================================="
echo "TokStance provisionado com sucesso na VM!"
echo "Status do servico:"
sudo systemctl status tokstance.service --no-pager || true
echo "=========================================================="
if [ "$HTTPS_HABILITADO" = true ]; then
    echo "🎉 APLICACAO PUBLICADA COM SUCESSO (HTTPS):"
    echo "👉 https://$DOMAIN"
else
    echo "APLICACAO PUBLICADA (HTTP):"
    echo "👉 http://$DOMAIN"
    echo "   (ou http://$(curl -s -m 3 https://api.ipify.org 2>/dev/null || echo '34.56.250.144'))"
fi
echo "=========================================================="
