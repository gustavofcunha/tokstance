# TokStance

Plataforma de curadoria, anotação e cálculo de concordância em vídeos curtos do TikTok para treinamento de classificador multimodal.
Trabalho prático da disciplina de Teste de Software (DCC/UFMG).

[![CI/CD Multi-OS](https://github.com/gustavofcunha/tokstance/actions/workflows/ci.yml/badge.svg)](https://github.com/gustavofcunha/tokstance/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/gustavofcunha/tokstance/branch/main/graph/badge.svg)](https://codecov.io/gh/gustavofcunha/tokstance)
[![Ambiente em Produção](https://img.shields.io/badge/Produção-https%3A%2F%2Ftokstance.duckdns.org-brightgreen)](https://tokstance.duckdns.org)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Integrantes

- Gustavo Freitas Cunha (gustavocunha@dcc.ufmg.br)

Realizei este trabalho de forma individual por ser aluno regular da pós-graduação (mestrado acadêmico no PPGCC/UFMG), com autorização do professor da disciplina.

---

## Sobre o sistema

Desenvolvi o TokStance como parte da minha pesquisa de mestrado no DCC/UFMG. Na minha dissertação, estou construindo um classificador multimodal para detecção de posicionamento (stance detection) em vídeos curtos do TikTok, analisando imagem, áudio transcrito e texto das legendas.

Para treinar e validar esse modelo, preciso de uma base de vídeos anotada por múltiplos avaliadores humanos com controle de qualidade e medição de concordância. Criei o TokStance para gerenciar esse processo de ponta a ponta.

### Funcionalidades implementadas

1. Autenticação e contas:
   - Cadastro com validação de formato e e-mail obrigatório
   - Senhas criptografadas com bcrypt
   - Proteção contra força bruta com bloqueio temporário após tentativas incorretas
   - Recuperação de senha com envio de código numérico de 6 dígitos via SMTP pelo Gmail

2. Painel central (Hub):
   - Separação entre tarefas que eu administro e tarefas atribuídas para eu rotular
   - Entrada em tarefas por código de convite (como o código TOK-DEMO2026)
   - Acompanhamento do progresso de anotações em tempo real

3. Criação de tarefas e distribuição:
   - Definição da pergunta e das opções de resposta
   - Matriz de penalidades para cálculo ordinal de divergências
   - Separação automática entre acervo principal e vídeos de reserva
   - Distribuição intercalada de vídeos entre anotadores com percentual de sobreposição configurável

4. Tela de rotulação:
   - Player embutido do TikTok em formato widescreen
   - Aviso de conteúdo sensível com opção de saída
   - Destaque do tema em análise direto no enunciado
   - Cronometragem do tempo gasto por vídeo e confirmação visual ao salvar

5. Substituição de vídeos com falha:
   - Opção para reportar vídeos fora do ar ou com link quebrado
   - Tempo mínimo de tentativa antes de permitir o reporte
   - Troca automática por outro vídeo do mesmo tema vindo da reserva

6. Console administrativo e métricas:
   - Cálculo automático do Alfa de Krippendorff ordinal ponderado
   - Gráficos de progresso, total de anotações e taxa de retenção
   - Exportação dos dados anotados em formato CSV para uso no treino do meu modelo

7. Persistência e segurança:
   - Diário transacional em arquivo JSONL com checksum SHA-256 para não perder dados se o servidor reiniciar
   - Reconciliação automática entre o diário e o banco SQLite
   - Middlewares contra ataques DoS por envio de arquivos grandes, rate limit por IP e cabeçalhos de proteção HTTP

---

## Tecnologias

Estruturei o projeto separando domínio, serviços, banco de dados e interface visual.

- Python 3.10+
- FastAPI e Uvicorn para rotas REST e servidor ASGI
- Gradio 4+ para a interface web reativa, com CSS customizado no padrão visual da UFMG
- SQLite 3 com modo WAL ativado e verificação de chaves estrangeiras
- bcrypt para hash de senhas
- pandas para manipulação de tabelas e cálculo das matrizes
- Nginx na nuvem atuando como proxy reverso nas portas 80 e 443, com suporte a WebSockets
- Certbot para emissão e renovação automática do certificado SSL gratuito (Let's Encrypt)
- pytest, Coverage.py e Playwright para a suite de testes unitários, de integração e ponta a ponta
- GitHub Actions rodando os testes automaticamente a cada commit no Linux, macOS e Windows
- Codecov para publicação dos relatórios de cobertura
- Horário oficial padronizado no fuso de Brasília (UTC-3)

---

## Uso de inteligência artificial

Durante o desenvolvimento, utilizei ferramentas de inteligência artificial (Google Antigravity, Claude e ChatGPT) como assistentes de programação nas seguintes etapas:

1. Modelagem e arquitetura:
   - Discussão da estrutura de camadas para manter regras de negócio separadas da interface do Gradio
   - Modelagem das tabelas relacionais do SQLite e integridade referencial

2. Criação dos testes:
   - Geração de casos de teste unitários com padrão Arrange-Act-Assert
   - Mapeamento de cenários de borda para validação de formulários, controle de concorrência e injeção de dados inválidos
   - Apoio na escrita dos fluxos de teste ponta a ponta com Playwright

3. Estatística e algoritmos:
   - Revisão da fórmula matemática do Alfa de Krippendorff ordinal aplicada à matriz de distâncias

4. Infraestrutura e deploy:
   - Configuração do pipeline multiplataforma no GitHub Actions
   - Escrita dos scripts de configuração da máquina virtual no Google Cloud, Nginx e systemd

---

## Execução dos testes

Implementei 230 testes automatizados cobrindo testes unitários, testes de integração e testes de ponta a ponta com o navegador, mantendo a cobertura acima de 88%.

### Preparar o ambiente local

```bash
git clone https://github.com/gustavofcunha/tokstance.git
cd tokstance

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
playwright install --with-deps chromium
```

### Rodar a suite completa
```bash
PYTHONPATH=src pytest
```

### Rodar apenas testes unitários
```bash
PYTHONPATH=src pytest tests/unit/
```

### Rodar apenas testes de integração
```bash
PYTHONPATH=src pytest tests/integration/
```

### Rodar testes ponta a ponta (E2E com Playwright)
Abre o Chromium em modo headless e simula o usuário navegando, criando conta, rotulando vídeos e recuperando senha:
```bash
PYTHONPATH=src pytest tests/e2e/test_e2e_user_journeys.py
```

### Medir cobertura com Coverage.py
```bash
PYTHONPATH=src pytest --cov=src/tokstance --cov-report=term-missing
```

Para gerar o XML que envio ao Codecov:
```bash
PYTHONPATH=src pytest --cov=src/tokstance --cov-report=xml
```

---

## Como rodar localmente

```bash
# Popular o banco com dados demonstrativos
PYTHONPATH=src:. python3 scripts/seed_demo.py

# Iniciar o servidor
PYTHONPATH=src:. python3 -m tokstance.main
```
Acesse no navegador: `http://localhost:7860`

### Usuários de teste cadastrados pelo seed:

| Usuário | Senha | Perfil no sistema |
| :--- | :--- | :--- |
| professor | senha123 | Conta principal para avaliação. O professor é o criador da tarefa de teste, tendo acesso ao Console de Administração para ver métricas e exportar dados, e também está cadastrado como rotulador da tarefa para testar o fluxo de anotação. |
| rotulador_1 | senha123 | Anotador com 10 vídeos rotulados e 1 relato de problema para testar a substituição de vídeo com falha. |
| rotulador_2 | senha123 | Anotador com 8 vídeos rotulados com sobreposição para gerar métricas de concordância no painel. |
| gustavo | senha123 | Conta avulsa para testar o ingresso na tarefa usando o código de convite TOK-DEMO2026 ou o fluxo de esqueci minha senha. |

Código de convite para teste: `TOK-DEMO2026`

---

## Links para avaliação

1. Sistema em produção: [https://tokstance.duckdns.org](https://tokstance.duckdns.org) (ou pelo IP da máquina no Google Cloud: [http://34.56.250.144](http://34.56.250.144))
2. Repositório no GitHub: [https://github.com/gustavofcunha/tokstance](https://github.com/gustavofcunha/tokstance)
3. Execução no GitHub Actions: [https://github.com/gustavofcunha/tokstance/actions](https://github.com/gustavofcunha/tokstance/actions)
4. Relatório no Codecov: [https://codecov.io/gh/gustavofcunha/tokstance](https://codecov.io/gh/gustavofcunha/tokstance)
5. Vídeo de apresentação no YouTube: [https://www.youtube.com/watch?v=SUBSTITUIR_LINK_VIDEO](https://www.youtube.com/watch?v=SUBSTITUIR_LINK_VIDEO)
