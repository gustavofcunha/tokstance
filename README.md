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

Realizei este trabalho de forma individual por ser aluno da pós-graduação.

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
- Nginx na nuvem atuando como proxy reverso nas portas 80 e 443, com suporte a WebSockets
- Certbot para emissão e renovação automática do certificado SSL gratuito (Let's Encrypt)
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

## Links para avaliação

1. Sistema em produção: [https://tokstance.duckdns.org](https://tokstance.duckdns.org) (ou pelo IP da máquina no Google Cloud: [http://34.56.250.144](http://34.56.250.144))
2. Repositório no GitHub: [https://github.com/gustavofcunha/tokstance](https://github.com/gustavofcunha/tokstance)
3. Execução no GitHub Actions: [https://github.com/gustavofcunha/tokstance/actions](https://github.com/gustavofcunha/tokstance/actions)
4. Relatório no Codecov: [https://codecov.io/gh/gustavofcunha/tokstance](https://codecov.io/gh/gustavofcunha/tokstance)
5. Vídeo de apresentação no YouTube: [https://www.youtube.com/watch?v=SUBSTITUIR_LINK_VIDEO](https://www.youtube.com/watch?v=SUBSTITUIR_LINK_VIDEO)

### Credenciais para acesso em produção:

| Usuário | Senha | Perfil no sistema |
| :--- | :--- | :--- |
| professor | senha123 | Conta principal para avaliação. O professor é o criador da tarefa de teste, tendo acesso ao Console de Administração para ver métricas e exportar dados, e também está cadastrado como rotulador da tarefa para testar o fluxo de anotação. |
| rotulador_1 | senha123 | Anotador com 10 vídeos rotulados e 1 relato de problema para testar a substituição de vídeo com falha. |
| rotulador_2 | senha123 | Anotador com 8 vídeos rotulados com sobreposição para gerar métricas de concordância no painel. |
| gustavo | senha123 | Conta avulsa para testar o ingresso na tarefa usando o código de convite TOK-DEMO2026 ou o fluxo de esqueci minha senha. |

Código de convite para teste: `TOK-DEMO2026`
