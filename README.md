# TokStance!

> **Plataforma de Curadoria, Anotação e Concordância Estatística em Vídeos Curtos do TikTok para Treinamento de Classificador Multimodal**  
> *Trabalho Prático da disciplina de Teste de Software — Departamento de Ciência da Computação (DCC / UFMG)*

[![CI/CD Multi-OS](https://github.com/gustavofcunha/tokstance/actions/workflows/ci.yml/badge.svg)](https://github.com/gustavofcunha/tokstance/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/gustavofcunha/tokstance/branch/main/graph/badge.svg)](https://codecov.io/gh/gustavofcunha/tokstance)
[![Ambiente em Produção](https://img.shields.io/badge/Produção-https%3A%2F%2Ftokstance.duckdns.org-brightgreen)](https://tokstance.duckdns.org)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Integrantes

- **Gustavo Freitas Cunha** — `gustavocunha182020@gmail.com`
  > **Nota de Justificativa Individual:** O trabalho é realizado de forma estritamente individual em conformidade com as diretrizes do docente da disciplina, por se tratar de aluno regular do **Programa de Pós-Graduação em Ciência da Computação (PPGCC/UFMG)** (Mestrado Acadêmico).

---

## Sobre o Sistema

### Contexto de Pesquisa Científica (Mestrado PPGCC / UFMG)
O **TokStance!** não é apenas um projeto avaliativo didático, mas o **artefato central de engenharia de software e coleta de dados primários da dissertação de mestrado do autor**. O objetivo da pesquisa é o desenvolvimento de um **classificador multimodal de detecção de posicionamento (*stance detection*) em vídeos curtos do TikTok**, capaz de processar simultaneamente sinais visuais de vídeo, áudio/fala transcrita e texto de legendas/hashtags.

Para viabilizar o treinamento e a validação desse modelo de inteligência artificial multimodal, é imperativo dispor de um acervo rotulado com rigor científico, controle de viés, distribuição balanceada de tópicos e auditoria de concordância interanotador. O TokStance! foi concebido e implementado para gerenciar rodadas completas de anotação colaborativa entre múltiplos avaliadores humanos.

### Principais Módulos e Funcionalidades

1. **Autenticação Segura, Gestão de Contas e Auditoria**:
   - Cadastro com validação de formato e obrigatoriedade de e-mail institucional/pessoal.
   - Hashing seguro de senhas via `bcrypt` com salt adaptativo.
   - Proteção ativa contra força bruta com bloqueio temporal de conta após tentativas consecutivas incorretas.
   - Fluxo de recuperação de senha em duas etapas com geração de código numérico efêmero de 6 dígitos, com envio real por e-mail via **SMTP (Gmail)** e tela interativa de redefinição com redirecionamento automático.

2. **Hub Central Multi-Papel**:
   - Separação contextual entre tarefas gerenciadas (papel de coordenador/pesquisador) e tarefas atribuídas para rotulação (papel de anotador).
   - Ingresso imediato em tarefas através de tokens de convite exclusivos (`TOK-DEMO2026`).
   - Monitoramento de progresso individual e global por meio de barras de progresso reativas.

3. **Assistente de Criação de Tarefas e Particionamento**:
   - Definição customizada da pergunta norteadora com template dinâmico `{target}` e opções de resposta.
   - Matriz par a par de penalidades para ponderação ordinal de discordâncias.
   - Algoritmo de particionamento determinístico entre conjunto principal e fila de reserva.
   - Motor de distribuição intercalada por alvo temático e balanceamento de sobreposição (*overlap*) entre anotadores.

4. **Ambiente de Rotulação Widescreen e Player Integrado**:
   - Player nativo do TikTok embutido em layout widescreen responsivo e otimizado para evitar rolagens desnecessárias.
   - Modal de proteção com aviso de conteúdo sensível e opção de saída segura.
   - Destaque contrastante do alvo temático (*target*) embutido diretamente no cabeçalho e na pergunta.
   - Cronometragem automática de tempo de análise por vídeo e salvamento com feedback visual efêmero (*toast* de confirmação).

5. **Substituição Automática de Vídeos com Falha**:
   - Mecanismo para reportar links corrompidos ou vídeos indisponíveis no TikTok.
   - Validação de tempo mínimo de tentativa para impedir fraudes ou avanço indevido.
   - Substituição transparente do vídeo defeituoso por um item equivalente do mesmo target a partir da fila de reserva.

6. **Console de Administração e Auditoria Estatística**:
   - Mensuração automatizada da concordância interanotador por meio do **Alfa de Krippendorff ordinal** ponderado por matriz de distâncias.
   - Painel com KPIs operacionais, volume total de anotações, distribuição temporal de atividade e taxa de retenção.
   - Exportação sob demanda dos dados primários em formato tabular estruturado (CSV) para alimentação direta nos pipelines de treinamento multimodal.

7. **Camada de Resiliência e Vault de Persistência**:
   - Sistema de persistência com **diário transacional imutável (*append-only journal*)** com validação criptográfica via checksum SHA-256 (`persistence_vault.py`).
   - Reconciliação e recuperação automática de registros entre o log de auditoria e a base SQLite em caso de reinicialização.
   - Middlewares de proteção: limites contra DoS em payloads volumosos, rate limiting por endereço IP e cabeçalhos de segurança OWASP (HSTS, CSP, X-Frame-Options, X-Content-Type-Options).

---

## Tecnologias Utilizadas

A aplicação adota uma arquitetura em camadas limpas (Clean Architecture / Domain-Driven Design), desacoplando o domínio de negócio, serviços, repositórios de dados e interfaces de apresentação:

- **Linguagem Principal**: Python 3.10+ com tipagem estática rigorosa (PEP 484).
- **Backend & Servidor Web**:
  - `FastAPI`: Roteamento assíncrono de APIs REST, endpoints de verificação de integridade e middlewares de segurança.
  - `Uvicorn`: Servidor ASGI de alto desempenho para concorrência de requisições.
  - `Nginx`: Servidor web e *reverse proxy* de produção na porta padrão 80 (HTTP) e 443 (HTTPS) com suporte a WebSockets e cabeçalhos de proteção.
- **Frontend & Interface Visual Reativa**:
  - `Gradio 4+`: Renderização de componentes reativos, gerenciamento de estado de sessão e disparo assíncrono de eventos.
  - `CSS Customizado` e `HTML5`: Tema claro institucional de alto contraste baseado nas cores da UFMG, suporte a layout widescreen, alertas inline acessíveis e notificações flutuantes.
  - `Favicon Customizado`: Ícone de marca vetorial em SVG e ICO (`t!`) integrado diretamente no cabeçalho HTML e nas rotas estáticas do servidor.
- **Persistência de Dados & Confiabilidade**:
  - `SQLite 3`: Banco relacional local com integridade referencial ativa (`PRAGMA foreign_keys = ON`), timeout de concorrência (`busy_timeout = 30000`) e modo de gravação atômica WAL (`PRAGMA journal_mode = WAL`).
  - `Vault Transacional`: Diário transacional em formato JSONL com verificação de integridade SHA-256 para tolerância a falhas.
- **Segurança & Criptografia**:
  - `bcrypt`: Criptografia unidirecional com salt dinâmico para armazenamento de credenciais.
  - Middlewares customizados: Mitigação de ataques DoS por limitação de payload, rate limiting por IP e higienização contra SQL Injection.
  - `Certbot / Let's Encrypt`: Emissão automatizada de certificado digital SSL/TLS com renovação contínua.
- **Tratamento de Dados & Estatística**:
  - `pandas`: Processamento de tabelas, estruturas matriciais de contingência e exportação de datasets.
  - Implementação nativa do cálculo do **Alfa de Krippendorff** para escalas ordinais.
- **Testes & Qualidade de Software**:
  - `pytest`: Framework central de testes.
  - `pytest-cov` / `Coverage.py`: Mensuração e auditoria de cobertura de código.
  - `Playwright` (`pytest-playwright`): Automação de navegadores Chromium headless para testes ponta a ponta (E2E).
- **Integração e Entrega Contínuas (CI/CD)**:
  - `GitHub Actions`: Matriz de execução contínua em três sistemas operacionais distintos (Ubuntu Linux, macOS e Windows).
  - `Codecov`: Upload automatizado de relatórios e validação do threshold mínimo de cobertura.
- **Fuso Horário Oficial**:
  - Todas as transações com registro de data e hora operam padronizadas no **Horário de Brasília (UTC-03:00)** (`BRT_TZ`).

---

## Uso de Inteligência Artificial

No desenvolvimento do TokStance!, ferramentas modernas de inteligência artificial e agentes autônomos de engenharia de software (em especial os modelos avançados **Google DeepMind / Antigravity**, Claude e ChatGPT) foram empregados de forma ética, controlada e transparente em todas as fases do ciclo de desenvolvimento:

1. **Design Arquitetural e Modelagem de Domínio**:
   - Apoio na estruturação da arquitetura em camadas e no desacoplamento entre regras de negócio puras (`domain/`), orquestradores de regras de negócio (`services/`), persistência relacional (`repositories/`) e apresentação reativa (`frontend/`).
   - Desenho do esquema relacional de 9 tabelas no SQLite com integridade referencial e chaves estrangeiras ativas.

2. **Engenharia e Automação de Testes**:
   - Geração e refinamento de baterias de testes unitários seguindo a metodologia **Arrange-Act-Assert (AAA)** e princípios **DAMP** (*Descriptive And Meaningful Phrases*).
   - Formulação de testes de robustez contra casos de borda (injeção maliciosa, payloads truncados, estouro de tentativas de login, concorrência e transição de estados).
   - Estruturação dos cenários E2E com Playwright para simular o comportamento de avaliadores reais no navegador.

3. **Validação Matemática e Estatística**:
   - Verificação formal da formulação matricial do Alfa de Krippendorff ordinal ponderado por penalidades dinâmicas, garantindo confiabilidade nas métricas estatísticas geradas para a dissertação.

4. **Hardening de Segurança e Resiliência**:
   - Criação da camada de middlewares defensivos de segurança: cabeçalhos recomendados pela OWASP, proteção anti-DoS para endpoints de arquivos e rate limiting de requisições.
   - Concepção do vault de persistência transacional com diário append-only e hashes SHA-256 para recuperação de desastres.

5. **Infraestrutura em Nuvem e CI/CD**:
   - Automação de scripts de provisionamento para Google Cloud Compute Engine (`setup_vm.sh`), configuração de reverse proxy Nginx com WebSockets e integração do pipeline multiplataforma no GitHub Actions.

---

## Execução dos Testes

O projeto conta com **229 testes automatizados** e cobertura de código **superior a 88%**, distribuídos entre testes de unidade, testes de integração e testes ponta a ponta (*end-to-end*).

### Pré-requisitos para Execução Local

- Python 3.10 ou superior instalado.
- Ambiente virtual Python ativado.

```bash
# 1. Clonar o repositório oficial
git clone https://github.com/gustavofcunha/tokstance.git
cd tokstance

# 2. Criar e ativar o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate

# 3. Instalar dependências e navegadores do Playwright
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
playwright install --with-deps chromium
```

### 1. Executar Todos os Testes
```bash
PYTHONPATH=src pytest
```

### 2. Executar Apenas Testes Unitários
Valida lógica pura de domínio, hashing de senhas, validação de targets, motor de penalidades, recuperação de senha, sanitização de inputs e cálculo de concordância:
```bash
PYTHONPATH=src pytest tests/unit/
```

### 3. Executar Apenas Testes de Integração
Valida a comunicação entre repositórios SQLite, transações, concorrência, consistência do diário de persistência e chamadas de serviços:
```bash
PYTHONPATH=src pytest tests/integration/
```

### 4. Executar Testes End-to-End (E2E com Playwright)
Executa jornadas reais automatizadas no navegador Chromium (modo headless), validando o fluxo completo do usuário (login, cadastro, ingresso em tarefa via convite, visualização de vídeos, modal de conteúdo sensível, rotulação, envio de respostas e recuperação de senha):
```bash
PYTHONPATH=src pytest tests/e2e/test_e2e_user_journeys.py
```

### 5. Mensuração de Cobertura com Coverage.py
Gera o relatório de cobertura de código no terminal com detalhamento de linhas não cobertas:
```bash
PYTHONPATH=src pytest --cov=src/tokstance --cov-report=term-missing
```

Para gerar o arquivo XML de cobertura consumido pelo Codecov e GitHub Actions:
```bash
PYTHONPATH=src pytest --cov=src/tokstance --cov-report=xml
```

---

## Execução da Aplicação Localmente

```bash
# 1. Popular o banco relacional local com dados demonstrativos
PYTHONPATH=src:. python3 scripts/seed_demo.py

# 2. Iniciar o servidor local
PYTHONPATH=src:. python3 -m tokstance.main
```
Acesse no seu navegador: `http://localhost:7860`

### Credenciais Padrão para Demonstração:

| Papel | Usuário | Senha | Descrição |
| :--- | :--- | :--- | :--- |
| **Coordenador / Pesquisador** | `coordenador` | `senha123` | Administrador da tarefa demonstrativa, com acesso ao Console de Administração, gráficos e relatórios estatísticos. |
| **Professor / Avaliador** | `professor` | `senha123` | Usuário para teste prático de ingresso em tarefas usando o código de convite `TOK-DEMO2026`. |
| **Rotulador Ativo 1** | `rotulador_1` | `senha123` | Possui 10 anotações efetuadas e 1 relato de problema para teste do fluxo de substituição de vídeos. |
| **Rotulador Ativo 2** | `rotulador_2` | `senha123` | Possui 8 anotações com sobreposição, gerando métricas reais de concordância interanotador. |

> **Código de Convite Demonstrativo**: `TOK-DEMO2026`

---

## Submissão do Trabalho Prático

Conforme solicitado no enunciado da disciplina, seguem os cinco links oficiais de entrega do projeto:

1. **Sistema em Produção**: [https://tokstance.duckdns.org](https://tokstance.duckdns.org) *(IP direto da VM GCP: [http://34.56.250.144](http://34.56.250.144))*
2. **Repositório no GitHub**: [https://github.com/gustavofcunha/tokstance](https://github.com/gustavofcunha/tokstance)
3. **Build no GitHub Actions**: [https://github.com/gustavofcunha/tokstance/actions](https://github.com/gustavofcunha/tokstance/actions)
4. **Relatório no Codecov**: [https://codecov.io/gh/gustavofcunha/tokstance](https://codecov.io/gh/gustavofcunha/tokstance)
5. **Vídeo de Apresentação no YouTube**: [https://www.youtube.com/watch?v=SUBSTITUIR_LINK_VIDEO](https://www.youtube.com/watch?v=SUBSTITUIR_LINK_VIDEO) *(vídeo demonstrativo de até 5 minutos)*
