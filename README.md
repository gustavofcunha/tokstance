# TokStance!

Plataforma aberta, auditável e colaborativa para anotação e detecção de posicionamento (*stance detection*) em vídeos curtos do TikTok, desenvolvida no âmbito da disciplina de Teste de Software da Universidade Federal de Minas Gerais (UFMG).

[![CI/CD Multi-OS](https://github.com/gustavofcunha/ufmg-stance-tiktok/actions/workflows/ci.yml/badge.svg)](https://github.com/gustavofcunha/ufmg-stance-tiktok/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/gustavofcunha/ufmg-stance-tiktok/branch/main/graph/badge.svg)](https://codecov.io/gh/gustavofcunha/ufmg-stance-tiktok)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Integrantes

- **Gustavo Cunha** (gustavocunha182020@gmail.com)

---

## Sobre o Sistema

O **TokStance!** é uma aplicação web completa voltada para pesquisa científica, análise de opinião e rotulação de conteúdo em mídias sociais. O sistema permite criar e gerenciar rodadas de rotulação de posicionamento em relação a temas de debate público (*targets* como vacinação, aborto, escalas de trabalho, entre outros), coordenando múltiplos anotadores concorrentes e mensurando o rigor estatístico das marcações.

### Principais Funcionalidades

1. **Autenticação Segura e Gestão de Contas**:
   - Cadastro com validação de formato e obrigatoriedade de e-mail.
   - Armazenamento de senhas com criptografia irreversível via `bcrypt` (12 rodadas).
   - Proteção ativa contra força bruta com bloqueio temporal por tentativas consecutivas incorretas.
   - Fluxo de recuperação de senha com verificação em duas etapas por código numérico de 6 dígitos temporário (validade de 15 minutos).
   - Transição automática pós-redefinição com redirecionamento para o login, pré-preenchimento de usuário e alertas contextuais inline.

2. **Hub Central Multi-Papel**:
   - Visão dinâmica dividida entre tarefas sob a administração do usuário e tarefas atribuídas para rotulação.
   - Ingresso imediato em novas tarefas por código de convite único alfanumérico.
   - Acompanhamento em tempo real do progresso individual e coletivo por barras de avanço.

3. **Assistente de Criação de Tarefas**:
   - Definição customizada de título, pergunta norteadora com template de substituição do target e opções de resposta.
   - Matriz par a par de penalidades editável para ponderar divergências de rotulação de acordo com o grau de polaridade.
   - Particionamento automático do acervo entre conjunto principal e fila de reserva.
   - Algoritmo de distribuição intercalada por target e balanceamento de sobreposição (*overlap*) entre anotadores.

4. **Ambiente de Rotulação Widescreen**:
   - Player nativo do TikTok integrado em layout widescreen sem barras de rolagem desnecessárias.
   - Modal de proteção com aviso de conteúdo sensível e opção de saída segura.
   - Destaque visual contrastante na transição de targets, com o target destacado embutido diretamente no enunciado da pergunta.
   - Registro de tempo de visualização por vídeo e salvamento com confirmação visual efêmera (*toast*).

5. **Substituição Automática de Vídeos com Falha**:
   - Botão para reportar problemas de reprodução ou links corrompidos.
   - Exigência de tempo mínimo de tentativa para evitar fraudes ou pulos acidentais.
   - Substituição determinística do vídeo com falha por um item equivalente do acervo de reserva, mantendo o balanceamento da rodada.

6. **Console de Administração e Auditoria Estatística**:
   - Cálculo automatizado da concordância interanotador pelo **Alfa de Krippendorff ordinal** ponderado pela matriz de distâncias.
   - Painel com KPIs operacionais, total de anotações, distribuição diária e estatísticas de acesso.
   - Tabela detalhada de atribuições e progresso por avaliador.
   - Exportação sob demanda em formato tabular dos resultados consolidados, trilha de auditoria e relatórios de concordância.

---

## Tecnologias Utilizadas

O projeto adota uma arquitetura em camadas limpas, desacoplando o domínio de negócio, as regras de segurança, a persistência relacional e as interfaces de visualização:

- **Linguagem**: Python 3.10+ (compatível com tipagem estática e anotações PEP 484).
- **Backend e API**:
  - `FastAPI`: Criação de rotas REST, endpoints de verificação de integridade (*health check*) e documentação OpenAPI.
  - `Uvicorn`: Servidor ASGI de alta performance para execução concorrente.
- **Frontend e Apresentação Visual**:
  - `Gradio`: Interface web reativa baseada em componentes visuais, gerenciamento de estados de sessão e disparo assíncrono de eventos.
  - `CSS Customizado` e `HTML5`: Tema institucional da UFMG com suporte a layout widescreen, alertas inline acessíveis e sistema de notificações flutuantes (*toasts*).
- **Persistência de Dados**:
  - `SQLite 3`: Banco relacional embarcado com integridade referencial ativa (`PRAGMA foreign_keys = ON`), transações atômicas e consultas estritamente parametrizadas.
- **Segurança e Criptografia**:
  - `bcrypt`: Algoritmo de derivação de chave e hashing adaptativo para proteção de credenciais de acesso.
- **Manipulação de Dados e Estatística**:
  - `pandas`: Processamento eficiente de tabelas, exportações CSV e estruturas matriciais de atribuição.
  - Implementação pura do `Alfa de Krippendorff` ordinal para avaliação estatística da confiabilidade dos dados anotados.
- **Testes e Qualidade de Código**:
  - `pytest`: Framework de testes para execução de suites unitárias, integradas e ponta a ponta.
  - `pytest-cov` / `Coverage.py`: Mensuração e auditoria de cobertura de código.
  - `Playwright` (`pytest-playwright`): Automação de navegadores Chromium headless para testes de jornadas reais do usuário (E2E).
  - `unittest.mock`: Isolamento de serviços externos de rede (como envio de e-mails via SMTP).
- **Integração e Entrega Contínuas (CI/CD)**:
  - `GitHub Actions`: Execução automática dos testes e cobertura a cada commit em três sistemas operacionais (Ubuntu Linux, macOS e Windows).
  - `Codecov`: Plataforma online para publicação e rastreamento contínuo dos relatórios de cobertura.
- **Fuso Horário Oficial**:
  - Todas as operações com registro temporal operam no **Horário de Brasília (UTC-03:00)** (`BRT_TZ = timezone(timedelta(hours=-3))`).

---

## Uso de Inteligência Artificial

No desenvolvimento do TokStance!, ferramentas modernas de inteligência artificial generativa e agentes autônomos de engenharia de software (incluindo modelos de linguagem avançados como Google DeepMind / Antigravity, Claude e ChatGPT) foram empregadas de forma estruturada e transparente durante todo o ciclo de vida do projeto:

1. **Arquitetura Limpa e Modelagem Conceitual**:
   - Apoio na definição da separação estrita em camadas (domínio puro, repositórios com transações atômicas, serviços orquestradores e interface desacoplada).
   - Estruturação do modelo relacional no SQLite com 9 tabelas interligadas por integridade referencial.

2. **Engenharia de Testes e Práticas de Confiabilidade**:
   - Aplicação rigorosa das diretrizes de testes modernos: estrutura Arrange-Act-Assert (AAA), código DAMP (foco em legibilidade e clareza contextual sem duplicação arriscada), testes através de APIs públicas e isolamento com fixtures em diretórios temporários.
   - Criação de mecanismos de teste determinísticos, incluindo relógios simulados com injeção de dependência e mocks de transporte SMTP para validação de fluxos de recuperação de senha sem acoplamento a provedores externos de e-mail.

3. **Algoritmos Matemáticos e Estatística Aplicada**:
   - Validação da formulação matemática do Alfa de Krippendorff ponderado por distâncias ordinais e matriz de penalidades dinâmica, garantindo precisão nos cálculos de concordância interanotador.

4. **Acessibilidade e Experiência do Usuário (UX/UI)**:
   - Prototipação e refinamento dos estilos CSS para suporte a telas widescreen, destaque visual contrastante para alternância de alvos temáticos e alertas inline de validação com papéis de acessibilidade ARIA.

5. **Automação de CI/CD e Governança de Versionamento**:
   - Elaboração do pipeline multiplataforma no GitHub Actions com matriz para Linux, macOS e Windows.
   - Planejamento de histórico de commits atômicos, descritivos e com mensagens padronizadas no formato Conventional Commits.

---

## Execução dos Testes

O repositório conta com uma ampla suite de testes automatizados com cobertura superior a 80%, cobrindo testes unitários, testes de integração e testes de ponta a ponta (*end-to-end*) no navegador.

### Pré-requisitos para Execução Local

- Python 3.10 ou superior instalado.
- Ambiente virtual configurado e ativado.
- Dependências do projeto instaladas.

```bash
# 1. Clonar o repositorio e navegar ate a raiz
git clone https://github.com/gustavofcunha/ufmg-stance-tiktok.git
cd ufmg-stance-tiktok

# 2. Criar e ativar o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate

# 3. Instalar dependencias e navegadores do Playwright
pip install --upgrade pip
pip install -r requirements.txt
playwright install --with-deps chromium
```

### 1. Testes Unitários

Executa mais de 80 testes de unidade que validam a lógica pura de domínio (modelos de dados, validação de CSV, motor de atribuições, intercalação de alvos, cálculo ordinal do Alfa de Krippendorff, criptografia e proteção contra força bruta):

```bash
PYTHONPATH=src pytest tests/unit/
```

### 2. Testes de Integração

Executa os testes que validam a interação entre repositórios SQLite, transações, banco de dados isolado e os serviços de administração e fila de anotação:

```bash
PYTHONPATH=src pytest tests/integration/
```

### 3. Testes End-to-End (E2E com Playwright)

Executa 7 testes completos de jornadas reais do usuário no navegador Chromium headless, simulando interação visual, digitação, cliques, alternância de abas, exibição de modais e navegação:

```bash
PYTHONPATH=src pytest tests/e2e/test_e2e_user_journeys.py
```

As 7 jornadas testadas no E2E cobrem:
1. Cadastro de nova conta, login no Hub e ingresso em tarefa por código de convite.
2. Rejeição de login com credenciais incorretas e bloqueio de convite inexistente com avisos inline.
3. Abertura do workspace de rotulação, exibição do modal de conteúdo sensível com desfoque e saída segura.
4. Confirmação do aviso sensivel revelando o player do TikTok e os controles de resposta.
5. Seleção de opção de posicionamento, salvamento com feedback visual e avanço da barra de progresso.
6. Criação de nova tarefa pelo assistente e auditoria de métricas no Console de Administração.
7. Redefinição de senha com validação de senhas divergentes, código temporário e redirecionamento automático para a tela de login com usuário pré-preenchido.

### 4. Execução Completa com Relatório de Cobertura

Gera o relatório detalhado de cobertura de linhas e branches com o `Coverage.py`:

```bash
PYTHONPATH=src pytest --cov=src/tokstance --cov-report=term-missing
```

Para gerar o relatório em formato XML para envio ao Codecov:

```bash
PYTHONPATH=src pytest --cov=src/tokstance --cov-report=xml
```

---

## Submissão do Trabalho Prático

Links oficiais para avaliação do projeto conforme especificado no enunciado do TP:

- **Sistema em Produção**: [http://34.133.155.105:7860](http://34.133.155.105:7860) *(substituir pelo endereço público da aplicação implantada em nuvem)*
- **Repositório no GitHub**: [https://github.com/gustavofcunha/ufmg-stance-tiktok](https://github.com/gustavofcunha/ufmg-stance-tiktok)
- **Build no GitHub Actions**: [https://github.com/gustavofcunha/ufmg-stance-tiktok/actions](https://github.com/gustavofcunha/ufmg-stance-tiktok/actions)
- **Relatório no Codecov**: [https://codecov.io/gh/gustavofcunha/ufmg-stance-tiktok](https://codecov.io/gh/gustavofcunha/ufmg-stance-tiktok)
- **Vídeo de Apresentação no YouTube**: [https://www.youtube.com/watch?v=EXEMPLO](https://www.youtube.com/watch?v=EXEMPLO) *(vídeo demonstrativo de até 5 minutos)*

---

## Execução da Aplicação em Modo Local

### Inicialização Rápida com Dados de Teste

Para rodar a aplicação localmente com uma base populada com dados demonstrativos (usuários, rodadas ativas, vídeos autênticos de debate público e métricas de exemplo):

```bash
# Popular o banco relacional de demonstracao
PYTHONPATH=src:. python3 scripts/seed_demo.py

# Iniciar o servidor
PYTHONPATH=src:. python3 -m tokstance.main
```

Acesse a interface pelo navegador no endereço: `http://localhost:7860`

### Credenciais Padrão de Avaliação

O script `scripts/seed_demo.py` gera as seguintes contas para testes práticos:

| Papel | Usuário | Senha Padrão | Descrição do Perfil |
| :--- | :--- | :--- | :--- |
| **Coordenador (Admin)** | `coordenador` | `senha123` | Administrador da tarefa demonstrativa, com acesso ao Console de Administração, gráficos e exportações. |
| **Professor (Avaliador)** | `professor` | `senha123` | Usuário livre para testar a entrada em tarefas via código de convite `TOK-DEMO2026`. |
| **Rotulador Ativo 1** | `rotulador_1` | `senha123` | Possui 10 vídeos anotados e 1 relato de problema para demonstrar o fluxo de substituição. |
| **Rotulador Ativo 2** | `rotulador_2` | `senha123` | Possui 8 vídeos anotados com sobreposição, gerando métricas de concordância no painel. |
| **Usuário Geral** | `gustavo` | `senha123` | Conta padrão para verificação de fluxos gerais e recuperação de senha. |

> **Código de Convite Demonstrativo**: `TOK-DEMO2026` (vincula novos anotadores diretamente às vagas da tarefa demonstrativa).

---

## Esquema Relacional de Dados (`data/tokstance.db`)

O banco SQLite é estruturado com chaves estrangeiras ativas, índices operacionais e consultas estritamente parametrizadas:

| Tabela | Finalidade Principal |
| :--- | :--- |
| `usuarios` | Cadastro de usuários, e-mail, hash seguro de senha (`bcrypt`) e data de registro. |
| `tarefas` | Metadados do estudo, título, pergunta com template de target, opções de rótulo, matriz de penalidades, vagas, sobreposição e código de convite único. |
| `membros_tarefa` | Associação entre usuários e tarefas com definição de papel (`administrador` ou `rotulador`). |
| `videos_tarefa` | Catálogo de vídeos vinculados a cada tarefa, distribuídos entre o conjunto `principal` e a fila de `reserva`. |
| `atribuicoes` | Fila individualizada de vídeos atribuídos a cada rotulador, registrando posição ordinal e versão de particionamento. |
| `anotacoes` | Respostas registradas por vídeo, incluindo a opção selecionada, tempo de análise em segundos e timestamp no Horário de Brasília. |
| `erros_videos` | Registro de vídeos com link quebrado ou falha de reprodução, com validação de tempo mínimo de tentativa. |
| `logs_acesso` | Trilha de auditoria das ações do sistema (login, logout, criação de tarefas e redefinição de senha). |
| `recuperacao_senha` | Armazenamento de códigos numéricos de recuperação de 6 dígitos com controle de validade temporal e uso único. |

---

## Implantação em Produção

A pasta `deploy/` inclui os scripts para provisionamento automático em máquinas virtuais na nuvem (Google Cloud Platform Compute Engine, AWS EC2 ou similares):

- `deploy/tokstance.service`: Unidade `systemd` para inicialização automática no boot do sistema, reinício automático em caso de falha e gestão de logs via `journalctl`.
- `deploy/setup_vm.sh`: Script em shell que automatiza a instalação de dependências do sistema operacional, criação do ambiente virtual Python, carga do seed demonstrativo e inicialização do serviço.

Comando de provisionamento na VM:
```bash
sudo bash deploy/setup_vm.sh
```
