# Roteiro de Gravação do Vídeo de Apresentação (TokStance!)
**Disciplina:** Teste de Software - DCC / UFMG  
**Tempo Máximo:** 5 minutos (300 segundos)  
**Apresentador:** Gustavo Cunha  

---

## 📋 Checklist Pré-Gravação (Prepare antes de iniciar)

1. **Abas abertas no navegador**:
   - **Aba 1 (Aplicação em Produção):** Tela inicial de Login do TokStance!.
   - **Aba 2 (GitHub Actions):** Página da [Execução #10 do GitHub Actions](https://github.com/gustavofcunha/tokstance/actions) com os 4 jobs verdes (Ubuntu, macOS, Windows e Playwright E2E).
   - **Aba 3 (Codecov):** Página do Codecov mostrando a cobertura de testes (acima de 88%).
   - **Aba 4 (Repositório GitHub):** Página inicial com o `README.md` estruturado.
2. **Terminal (opcional, para exibir execução rápida dos testes)**:
   - Na raiz do projeto, pronto para executar: `pytest -m "not e2e"`.
3. **Credenciais para Demonstração**:
   - Usuário: `professor` (Professor André Hora)
   - Senha: `senha123`
   - Código de convite da tarefa demo: `TOK-DEMO2026`

---

## ⏱️ Linha do Tempo do Vídeo (5 Minutos)

```
[00:00 - 00:50] 1. Introdução, Objetivo do Sistema e Tecnologias (50s)
[00:50 - 02:40] 2. Demonstração Prática e Fluxo do Avaliador (110s)
[02:40 - 03:30] 3. Como as Ferramentas de IA Foram Empregadas (50s)
[03:30 - 04:40] 4. Bateria de Testes, Cobertura e CI/CD Multi-OS (70s)
[04:40 - 05:00] 5. Conclusão e Submissão (20s)
```

---

## 🎬 Roteiro Detalhado Bloco a Bloco

### Bloco 1: Introdução, Objetivo e Tecnologias (00:00 a 00:50 - 50 segundos)
**Na tela:** Mostrar a tela de login da aplicação publicada em produção e o título do repositório no GitHub.

> **Fala sugerida:**  
> *"Olá! Meu nome é Gustavo Cunha e este é o vídeo de apresentação do **TokStance!**, sistema desenvolvido para o Trabalho Prático da disciplina de Teste de Software da UFMG.*  
>  
> *O TokStance! é uma plataforma web para detecção de posicionamento (stance detection) em vídeos curtos do TikTok. Ele permite coordenar rodadas científicas de rotulação, gerenciar múltiplos anotadores concorrentes, balancear sobreposição de dados entre avaliadores e mensurar a confiabilidade estatística por meio do Alfa de Krippendorff.*  
>  
> *Na arquitetura, utilizamos **Python 3.11** com **FastAPI** e **Gradio** reativo no frontend, banco relacional **SQLite** com integridade referencial ativa, **bcrypt** para hashing seguro de credenciais, **pandas** e implementações estatísticas para cálculo de concordância."*

---

### Bloco 2: Demonstração Prática e Fluxo do Professor (00:50 a 02:40 - 110 segundos)
**Na tela:** Fazer login com o usuário `professor` e demonstrar as duas perspectivas (Rotulador e Administrador).

> **Fala sugerida:**  
> *"Pensando na avaliação do professor, preparamos uma conta de demonstração completa para o Professor André Hora: usuário `professor` e senha `senha123`.  
> Ao efetuar o login, o professor chega imediatamente ao **Painel Principal Multi-Papel**, onde tem uma experiência dupla: ele é simultaneamente rotulador e administrador da tarefa 'Detecção de Posição'.*

#### Parte A: O Espaço de Rotulagem (Rotulador)
**Ação na tela:** Clicar em *"Abrir Espaço de Rotulagem"*.

> **Fala sugerida:**  
> *"Como rotulador, ao clicar no espaço de rotulagem, o avaliador visualiza o modal de aviso ético sobre conteúdo sensível. Ao aceitar, ele é apresentado ao ambiente de trabalho widescreen com o player nativo do TikTok embutido, transcrição do áudio e as opções de postura (*Contra*, *A Favor*, *Neutro* ou *Não relacionado*).  
>  
> O sistema possui atalhos de teclado (teclas 1, 2, 3 e 4) para rotulação ágil, feedback visual imediato por toasts flutuantes e botão para reportar vídeos corrompidos, que envia o item para a fila de substituição. Conforme rotulamos, a barra de progresso avança em tempo real."*

#### Parte B: O Console Administrativo (Coordenador)
**Ação na tela:** Clicar em *"← Voltar ao Painel Principal"* e depois em *"Console Administrativo"*.

> **Fala sugerida:**  
> *"Retornando ao Painel Principal, o professor pode abrir o **Console Administrativo**. Aqui ele acompanha o progresso de toda a equipe: vemos que os rotuladores 1 e 2 já concluíram anotações parciais, permitindo o cálculo em tempo real do percentual de concordância e do **Alfa de Krippendorff ordinal** ponderado pela matriz par a par de distâncias.  
>  
> O console também exibe a auditoria de erros reportados, permitindo substituir um vídeo com falha por outro do acervo de reserva, além de exportar em um clique todos os 8 artefatos tabulares e relatórios em CSV e JSON.*  
>  
> *Caso o professor queira testar o fluxo de ponta a ponta a partir do zero, basta criar uma conta nova e usar o código de convite `TOK-DEMO2026`, que possui vaga aberta pronta para novos ingressos."*

---

### Bloco 3: Uso de Ferramentas de Inteligência Artificial (02:40 a 03:30 - 50 segundos)
**Na tela:** Mostrar rapidamente o arquivo `README.md` (seção de Uso de IA) ou o código-fonte no VS Code/GitHub.

> **Fala sugerida:**  
> *"As ferramentas de Inteligência Artificial foram utilizadas como parceiras de desenvolvimento (pair programming) em todas as fases do projeto:  
>  
> 1. **Modelagem de Domínio e Arquitetura:** Estruturação da arquitetura limpa em camadas (domínio puro, repositórios com transações atômicas, serviços e UI desacoplada).  
> 2. **Geração e Ponderação de Casos de Borda:** Criação de cenários de teste não-triviais, como mitigação de ataques de força bruta no login, recuperação de senha com expiração temporal e tratamento de condições de corrida em substituições concorrentes de vídeo.  
> 3. **Engenharia de Testes:** Auxílio na escrita de fixtures do pytest, dados sintéticos determinísticos e scripts de automação E2E."*

---

### Bloco 4: Testes, Cobertura e CI/CD Multi-OS (03:30 a 04:40 - 70 segundos)
**Na tela:** Alternar para a aba do **GitHub Actions** e depois para o **Codecov**.

> **Fala sugerida:**  
> *"A qualidade do software foi garantida por uma rigorosa bateria de testes:  
>  
> - **Mais de 190 testes de unidade e integração**, testando comportamento através de APIs públicas, regras de negócio e validações defensivas.  
> - **11 testes end-to-end com Playwright**, cobrindo todas as jornadas do usuário: cadastro, rejeição de credenciais inválidas, ingresso por código de convite, rotulagem de vídeos com atalhos, relato de erros e navegação administrativa.  
>  
> No **GitHub Actions**, implementamos pipeline de Integração Contínua com matriz de execução rodando em **três sistemas operacionais**: Ubuntu Linux, macOS e Windows, além do job dedicado de Playwright E2E em ambiente headless. Como podem ver na execução mais recente, todos os jobs estão verdes e passaram com sucesso.  
>  
> No **Codecov**, a cobertura de testes do projeto está consolidada em torno de **89%**, superando amplamente o requisito mínimo de 80% exigido na especificação."*

---

### Bloco 5: Conclusão e Encerramento (04:40 a 05:00 - 20 segundos)
**Na tela:** Mostrar a página principal do repositório no GitHub com todos os links.

> **Fala sugerida:**  
> *"Todos os links de submissão do trabalho - o sistema publicado em produção, o repositório público no GitHub, o histórico de builds do GitHub Actions e o relatório detalhado do Codecov - estão disponíveis no README do projeto e na entrega do Moodle.  
>  
> Muito obrigado pela atenção!"*

---

## 💡 Dicas Importantes para a Gravação

1. **Ritmo de Fala:** Fale de forma pausada, mas dinâmica. Não se preocupe em mostrar cada linha de código; foque na experiência em funcionamento, nos testes e no CI/CD.
2. **Resolução de Tela:** Grave em Full HD (1920x1080) com zoom do navegador em 100% ou 110% para que os textos e métricas fiquem bem legíveis no YouTube.
3. **Se Errar:** Não precisa reiniciar o vídeo do zero; apenas pause 2 segundos em silêncio e repita a frase do bloco para cortar facilmente no editor.
4. **Tempo:** Se perceber que está perto de 4 minutos ao chegar no bloco de testes, simplifique a fala dos testes e vá direto para a tela do GitHub Actions e Codecov.
