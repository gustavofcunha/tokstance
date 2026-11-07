#!/usr/bin/env bash
# Script para reiniciar o banco de dados com os dados demonstrativos de avaliacao
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

cd "$PROD_DIR"

# 2. Localizar interpretador python do ambiente virtual
PYTHON_EXEC="python3"
if [ -f "$PROD_DIR/.venv/bin/python3" ]; then
    PYTHON_EXEC="$PROD_DIR/.venv/bin/python3"
elif [ -f "/opt/tokstance/.venv/bin/python3" ]; then
    PYTHON_EXEC="/opt/tokstance/.venv/bin/python3"
elif [ -f "$CURRENT_DIR/.venv/bin/python3" ]; then
    PYTHON_EXEC="$CURRENT_DIR/.venv/bin/python3"
else
    echo "Criando ambiente virtual em $PROD_DIR/.venv..."
    python3 -m venv "$PROD_DIR/.venv"
    "$PROD_DIR/.venv/bin/pip" install -q -r "$PROD_DIR/requirements.txt"
    PYTHON_EXEC="$PROD_DIR/.venv/bin/python3"
fi

echo "=========================================================="
echo "Reiniciando banco de dados com especificacoes de demo"
echo "Diretorio de producao: $PROD_DIR"
echo "Interpretador Python:  $PYTHON_EXEC"
echo "Usuarios preservados:  professor, rotulador_1, rotulador_2, gustavo"
echo "=========================================================="

echo "1. Limpando usuarios extras e restaurando dados da demonstracao..."
PYTHONPATH="$PROD_DIR/src:$PROD_DIR" "$PYTHON_EXEC" "$PROD_DIR/scripts/seed_demo.py" "$@"

echo "2. Verificando usuarios ativos no banco..."
PYTHONPATH="$PROD_DIR/src:$PROD_DIR" "$PYTHON_EXEC" -c "
from tokstance.backend.repositories.database import BancoDadosSQLite
from tokstance.config import resolver_caminhos_dados
c = resolver_caminhos_dados()
b = BancoDadosSQLite(c.arquivo_banco_dados)
usuarios = b.consultar_todos('SELECT usuario_id, nome_usuario, email, nome_completo FROM usuarios ORDER BY usuario_id')
print(f'Total de usuarios restantes: {len(usuarios)}')
for u in usuarios:
    print(f\"  • [{u['usuario_id']}] {u['nome_usuario']} ({u['nome_completo'] or 'Sem nome'}) <{u['email']}>\")
"

echo "3. Reiniciando servico da aplicacao para carregar os novos dados..."
if command -v systemctl >/dev/null 2>&1 && [ -f /etc/systemd/system/tokstance.service ]; then
    sudo systemctl restart tokstance.service
    echo "Servico tokstance.service reiniciado com sucesso."
fi

echo "=========================================================="
echo "Banco de dados demonstrativo reiniciado com sucesso!"
echo "=========================================================="


