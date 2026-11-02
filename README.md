# TokStance!

Plataforma aberta, auditavel e colaborativa para anotacao e deteccao de posicionamento (*stance detection*) em videos curtos do TikTok, desenvolvida para pesquisas academicas na Universidade Federal de Minas Gerais (UFMG).

O sistema oferece suporte completo a multiplos anotadores concorrentes com isolamento de sessoes, calculo automatizado da concordancia interanotador via Alfa de Krippendorff ponderado por distancias ordinais customizaveis, algoritmo de balanceamento de sobreposicao (*overlap*) entre rotuladores, substituicao automatica de videos inacessiveis por acervo de reserva e consolidacao relacional em banco SQLite local com exportacao sob demanda.

---

## 1. Visao Geral da Arquitetura

O TokStance foi projetado seguindo principios de arquitetura limpa em camadas desacopladas, garantindo testabilidade extensiva, ausencia de efeitos colaterais e facil manutencao:

```
src/tokstance/
├── backend/
│   ├── api/             # Rotas FastAPI para verificacao de saude e endpoints
│   ├── domain/          # Modelos de dominio puros, metricas de concordancia e regras de negocio
│   ├── repositories/    # Persistencia relacional SQLite com integridade referencial ativa
│   ├── security/        # Criptografia de senhas (bcrypt), controle de tentativas e sessoes
│   └── services/        # Orquestracao de servicos (Autenticacao, Administracao e Fila de Rotulacao)
├── frontend/
│   ├── gradio_ui.py     # Interface visual integrada (Hub, Criador de Tarefas, Rotulador e Admin)
│   ├── theme.py         # Tema visual e paleta de cores institucional da UFMG
│   └── components.py    # Cartoes KPI, tabelas e componentes visuais do dashboard
└── main.py              # Acoplamento FastAPI e Gradio via Uvicorn
```

---

## 2. Esquema Relacional de Dados (`data/tokstance.db`)

Toda a persistencia e centralizada no SQLite com chaves estrangeiras ativas (`PRAGMA foreign_keys = ON`), transacoes atomicas e consultas estritamente parametrizadas:

| Tabela | Finalidade Principal |
| :--- | :--- |
| `usuarios` | Cadastro de usuarios, email, hash seguro de senha (bcrypt com 12 rounds) e data de registro. |
| `tarefas` | Metadados do estudo, titulo, pergunta norteadora com template de target, opcoes de rotulo, matriz de penalidades JSON, numero de vagas, percentual de sobreposicao e codigo de convite unico. |
| `membros_tarefa` | Associacao entre usuarios e tarefas com definicao explicita de papel (`administrador` ou `rotulador`). |
| `videos_tarefa` | Catalogo de videos vinculados a cada tarefa, classificados entre o conjunto `principal` e a fila de `reserva`. |
| `atribuicoes` | Fila individualizada de videos designados para cada rotulador, registrando posicao ordinal e versao de particionamento. |
| `anotacoes` | Respostas registradas por video, incluindo a opcao escolhida, tempo de analise em segundos e timestamp no Horario de Brasilia. |
| `erros_videos` | Registro de videos com link corrompido ou erro de reproducao, exigindo tempo minimo de tentativa (10 segundos) antes de acionar a substituicao automatica por reserva. |
| `logs_acesso` | Trilha de auditoria das acoes operacionais (login, logout, criacao de tarefas) com timestamps detalhados. |
| `recuperacao_senha` | Armazenamento de codigos de recuperacao de 6 digitos com controle de validade temporal e consumo de uso unico. |

---

## 3. Instalacao e Execucao Local

### Requisitos de Ambiente
- Python 3.10 ou superior
- Sistema operacional Linux ou macOS (suporte a Windows via WSL2)
- Navegador moderno com suporte a JavaScript

### Passo a Passo

1. **Clonar o repositorio e criar o ambiente virtual**:
   ```bash
   git clone https://github.com/gustavofcunha/ufmg-stance-tiktok.git
   cd ufmg-stance-tiktok
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Instalar as dependencias do projeto**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   playwright install --with-deps chromium
   ```

3. **Popular o banco com dados demonstrativos para avaliacao**:
   ```bash
   PYTHONPATH=src:. python3 scripts/seed_demo.py
   ```

4. **Iniciar o servidor da aplicacao**:
   ```bash
   PYTHONPATH=src:. python3 -m tokstance.main
   ```
   Acesse a aplicacao no navegador em: `http://localhost:7860`

---

## 4. Credenciais de Acesso para Avaliacao

O script `scripts/seed_demo.py` inicializa o banco com a tarefa demonstrativa **Detecção de Posição** (campanha autentica de videos sobre temas publicos como *Fim da Escala 6x1*, *Vacinacao* e *Aborto*) e as seguintes contas de teste:

| Papel | Usuario | Senha Padrao | Observacoes |
| :--- | :--- | :--- | :--- |
| **Coordenador (Admin)** | `coordenador` | `senha123` | Criador da tarefa, acesso total ao Console de Administracao com metricas de concordancia, KPIs, graficos e download de relatorios. |
| **Professor (Avaliador)** | `professor` | `senha123` | Conta livre para entrar na tarefa pelo Hub usando o codigo de convite `TOK-DEMO2026`. |
| **Rotulador Ativo 1** | `rotulador_1` | `senha123` | Ja possui 10 videos anotados e 1 relato de erro de reproducao para demonstrar o fluxo de substituicao. |
| **Rotulador Ativo 2** | `rotulador_2` | `senha123` | Possui 8 videos anotados com sobreposicao em relacao ao rotulador 1, gerando indice de concordancia consistente. |
| **Usuario Geral** | `gustavo` | `senha123` | Conta pessoal para verificacao de fluxos de login e alteracao de perfil. |

> **Codigo de Convite Demonstrativo**: `TOK-DEMO2026` (insere novos rotuladores diretamente nas vagas livres da tarefa demonstrativa).

---

## 5. Guia da Suite de Testes

O repositorio conta com uma suite de testes automatizados cobrindo testes unitarios, de integracao e testes end-to-end de navegacao com Playwright.

### 1. Testes Unitarios
Validam a camada de dominio (calculo do Alfa de Krippendorff ordinal, matriz par a par de penalidades, rate limiting e hashing de senhas):
```bash
PYTHONPATH=src pytest tests/unit/
```

### 2. Testes de Integracao
Validam a integracao dos repositorios SQLite, servicos de autenticacao e rotulacao, particionamento de pool principal/reserva e substituicao de videos:
```bash
PYTHONPATH=src pytest tests/integration/
```

### 3. Testes End-to-End no Navegador (Playwright)
Executam as 6 jornadas completas de usuario no navegador Chromium headless em um servidor isolado temporario:
```bash
PYTHONPATH=src pytest tests/e2e/test_e2e_user_journeys.py
```

As 6 jornadas testadas sao:
1. Cadastro de nova conta, login no Hub e ingresso em tarefa via codigo de convite.
2. Rejeicao de credenciais incorretas e codigo de convite inexistente com avisos contextuais.
3. Abertura do espaco de rotulacao, exibicao do modal de aviso de conteudo sensivel com desfoque e saida segura.
4. Confirmacao no aviso sensivel revelando o player TikTok e os controles de resposta.
5. Selecao de opcao de posicionamento, salvamento e avanco da barra de progresso.
6. Criacao de nova tarefa no assistente e auditoria de metricas no Console de Administracao.

### 4. Execucao Global com Relatorio de Cobertura
```bash
PYTHONPATH=src pytest --cov=src/tokstance --cov-report=term-missing
```

---

## 6. Implantacao em Producao (Google Cloud Platform)

A pasta `deploy/` contem os artefatos necessarios para execucao continua em uma maquina virtual Compute Engine no Google Cloud Platform:

- `deploy/tokstance.service`: Arquivo de configuracao da unidade de servico `systemd` para inicializacao automatica, reinicio em caso de falha e gerenciamento de logs via `journalctl`.
- `deploy/setup_vm.sh`: Script em shell que automatiza a preparacao completa da VM, instalando os pacotes do sistema operacional, configurando o ambiente Python virtual, executando o seed demonstrativo e ativando o servico `systemd`.

Para provisionar a VM:
```bash
sudo bash deploy/setup_vm.sh
```

---

## 7. Fuso Horario Oficial

Todas as operacoes com registro temporal (anotacoes, erros reportados, auditoria de acesso e relatorios de concordancia) operam estritamente no **Horario de Brasilia (UTC-03:00)**, garantindo conformidade com a legislacao e com os padroes academicos brasileiros.
