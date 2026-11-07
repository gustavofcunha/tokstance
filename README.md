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

Trabalho de forma individual (aluno da pós-graduação).

---

## Sobre o sistema

O TokStance é uma aplicação real que desenvolvi para ser utilizada na prática durante a minha pesquisa de mestrado, e não um projeto simulado apenas para cumprir a disciplina, apesar de ter sido adaptado para as demonstrações e avaliações da disciplina.

Na minha dissertação, estou construindo um classificador multimodal de aprendizado profundo para detecção de posicionamento (stance detection) em vídeos curtos do TikTok. O modelo precisa analisar conjuntamente os quadros de vídeo, o áudio com fala transcrita e o texto de legendas e hashtags para identificar se o autor do vídeo se posiciona a favor, contra ou neutro em relação a temas de debate público.

Como se trata de aprendizado supervisionado, eu preciso de um acervo rotulado por múltiplos anotadores humanos, com rigor metodológico, controle de sobreposição de amostras entre pessoas e cálculo de confiabilidade estatística. O TokStance foi construído exatamente para coordenar essa campanha de anotação com os voluntários que irão participar.

### Por que desenvolvi uma ferramenta própria?

Ferramentas prontas de rotulação de mercado (como Label Studio ou Prodigy) são genéricas e não atendiam ao que a minha pesquisa precisa:

1. Suporte nativo a vídeos verticais do TikTok: A maioria das ferramentas foi feita para texto ou imagens estáticas. O TokStance embute o player oficial do TikTok em layout widescreen, preservando a experiência real da plataforma sem exigir que os anotadores baixem gigabytes de arquivos para o próprio computador.

2. Gestão de vídeos que saem do ar: No TikTok, é muito comum que autores apaguem vídeos ou mudem a privacidade durante o estudo. Criei um fluxo onde o anotador pode reportar falha de reprodução e o sistema substitui automaticamente aquele item por outro vídeo equivalente do mesmo tema, vindo de uma fila de reserva, sem quebrar a distribuição estatística.

3. Controle fino de sobreposição e alocação: Implementei um algoritmo próprio que distribui os vídeos garantindo que parte deles seja avaliada por mais de um rotulador para medir a concordância, enquanto o restante é distribuído de forma exclusiva para cobrir mais conteúdo.

4. Métricas estatísticas integradas: Em vez de exportar dados brutos para calcular concordância em planilhas externas, implementei diretamente no sistema o cálculo do Alfa de Krippendorff ordinal, já ponderado pela matriz de distâncias da pesquisa.

5. Soberania dos dados e custo zero: Não fico preso a planos pagos por usuário nem a limites de armazenamento de plataformas comerciais. Todo o banco de dados e os registros de auditoria ficam na minha própria infraestrutura.

### Funcionalidades implementadas

1. Autenticação e contas:
   - Cadastro com validação de formato e e-mail obrigatório
   - Senhas criptografadas com bcrypt
   - Proteção contra força bruta com bloqueio temporário após tentativas incorretas
   - Recuperação de senha com envio de código numérico de 6 dígitos via SMTP pelo Gmail

2. Painel central:
   - Separação entre tarefas que eu administro e tarefas atribuídas para eu rotular
   - Entrada em tarefas por código de convite 
   - Acompanhamento do progresso de anotações em tempo real

3. Criação de tarefas e distribuição:
   - Definição da pergunta e das opções de resposta
   - Matriz personalizável de penalidades para cálculo ordinal de divergências
   - Separação entre acervo principal e vídeos de reserva
   - Distribuição intercalada de vídeos entre anotadores com percentual de sobreposição configurável

4. Tela de rotulação:
   - Player embutido do TikTok em formato widescreen
   - Aviso de conteúdo sensível com opção de saída
   - Destaque do tema em análise direto no enunciado
   - Salvamento incremental que permite ao rotulador sair da plataforma e retomar a tarefa posteriormente de onde ele parou

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
- Gradio 4+ para a interface web reativa, com CSS customizado
- SQLite 3 com modo WAL ativado e verificação de chaves estrangeiras
- bcrypt para hash de senhas
- pandas para manipulação de tabelas e cálculo das matrizes
- Google Cloud Platform (Compute Engine) para hospedagem da máquina virtual e deploy em nuvem, com endereço IP externo estático para garantir persistência
- DuckDNS para personalização gratuita do domínio apontando para a máquina virtual
- Nginx atuando como proxy reverso nas portas 80 e 443, com suporte a WebSockets
- Certbot para emissão e renovação automática do certificado SSL gratuito (Let's Encrypt)
- systemd para gerenciamento do serviço com inicialização automática e recuperação de falhas
- pytest, Coverage.py e Playwright para a suite de testes unitários, de integração e ponta a ponta
- GitHub Actions rodando os testes automaticamente a cada commit no Linux, macOS e Windows
- Codecov para publicação dos relatórios de cobertura
- Horário oficial padronizado no fuso de Brasília (UTC-3)

---

## Uso de inteligência artificial

Utilizei a IDE Antigravity com agente integrado, utilizando principalmente o modelo Gemini 3.8 Pro. O agente de IA foi empregado como ferramental de apoio para modelagem, implementação do código de produção e escrita dos testes automatizados.

O trabalho ocorreu de forma incremental, o que me permitiu revisar, testar e refatorar tudo o que foi gerado pelo agente antes de integrar ao repositório. Todas as decisões de projeto, regras de negócio e arquitetura de software foram tomadas exclusivamente por mim.

---

## Execução dos testes

Implementei 242 testes automatizados mantendo a cobertura de código acima de 88%. A suite é distribuída em:

- 214 testes de unidade, validando regras de domínio, criptografia de senhas, matrizes ordinais e validação de formulários
- 17 testes de integração, validando transações no SQLite, tolerância a falhas e consistência do diário de persistência
- 11 testes de sistema, executando jornadas completas de usuário no navegador Chromium via Playwright

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

## Avaliação

1. Sistema em produção: [https://tokstance.duckdns.org](https://tokstance.duckdns.org) (ou pelo IP da máquina no Google Cloud: [http://34.56.250.144](http://34.56.250.144))
2. Repositório no GitHub: [https://github.com/gustavofcunha/tokstance](https://github.com/gustavofcunha/tokstance)
3. Última execução no GitHub Actions: [https://github.com/gustavofcunha/tokstance/actions/runs/42406651354](https://github.com/gustavofcunha/tokstance/actions/runs/42406651354)
4. Relatório no Codecov: [https://codecov.io/gh/gustavofcunha/tokstance](https://codecov.io/gh/gustavofcunha/tokstance)
5. Vídeo de apresentação no YouTube: [https://youtu.be/z9VkcT7AKpI](https://youtu.be/z9VkcT7AKpI)

### Credenciais para acesso em produção:

| Usuário | Senha | Perfil no sistema |
| :--- | :--- | :--- |
| professor | senha123 | Conta principal para avaliação. O professor é o criador da tarefa de teste, tendo acesso ao Console de Administração para ver métricas e exportar dados, e também está cadastrado como rotulador da tarefa para testar o fluxo de anotação. |
| rotulador_1 | senha123 | Anotador com 10 vídeos rotulados e 1 relato de problema para testar a substituição de vídeo com falha. |
| rotulador_2 | senha123 | Anotador com 8 vídeos rotulados com sobreposição para gerar métricas de concordância no painel. |

Código de convite para teste: `TOK-DEMO2026`

O usuário `professor` já está configurado tanto como administrador quanto como rotulador da tarefa demonstrativa. Recomendo que a avaliação seja feita acessando com essa conta, pois ela permite explorar de imediato todas as funcionalidades do sistema (gestão da rodada, gráficos de concordância e o ambiente de rotulação de vídeos), conforme demonstrado no [vídeo de apresentação](https://youtu.be/z9VkcT7AKpI). Caso prefira não utilizar os dados previamente preparados para demonstração, você também tem total liberdade para cadastrar uma nova conta e criar uma nova tarefa do zero diretamente pela interface.

### Roteiro rápido sugerido para avaliação

Para percorrer todas as telas do sistema logado em poucos minutos, sugiro o seguinte fluxo:

1. Acessar o sistema em produção e fazer login com o usuário 'professor' e a senha 'senha123'.
2. No painel principal, visualizar a divisão entre as tarefas que você administra e as tarefas atribuídas para rotular, com botões de ação rápida e o código de convite da rodada.
3. Clicar no botão do Console de Administração da tarefa para abrir o painel gerencial. Note que criei rotuladores fictícios e rótulos fictícios para permitir a visualização completa dos relatórios operacionais: cobertura da rodada, tempo mediano de análise, cálculo automático do Alfa de Krippendorff ordinal, gráficos de distribuição de posicionamento, progresso da equipe e tabela detalhada de concordância, além de tooltips explicativas nos cartões e exportação dos dados em CSV. Retornar ao painel principal pelo botão de voltar.
4. Na seção de tarefas para rotular, clicar no botão de rotulação para abrir o ambiente de trabalho do anotador. Confirmar o aviso de conteúdo sensível no modal para carregar o player embutido do TikTok, selecionar uma das opções de posicionamento (Contra, A Favor ou Neutro) e salvar para conferir o feedback visual efêmero e o avanço da barra de progresso. Retornar ao painel principal.
5. Clicar no botão de criação de nova tarefa para abrir o assistente (wizard), onde é possível conferir as tooltips e textos explicativos em cada parâmetro de configuração de um estudo (pergunta norteadora, opções de resposta, matriz de penalidades, definição de vagas, sobreposição de amostras e upload de arquivos). Retornar ao painel principal.
