# Guia de Operação, Deploy e Infraestrutura em Produção (GCP)

Este documento centraliza todas as instruções, comandos de operação, arquitetura de deploy e práticas de alta disponibilidade para manter o **TokStance!** em execução 24/7 na nuvem do Google Cloud até o término do período de avaliação da disciplina.

---

## 🌐 Informações de Produção

| Item | Detalhe |
| :--- | :--- |
| **URL Pública Oficial (HTTPS)** | [https://tokstance.duckdns.org](https://tokstance.duckdns.org) |
| **IP Externo da VM** | `34.56.250.144` |
| **Provedor de Nuvem** | Google Cloud Platform (GCP) - Compute Engine |
| **Zona / Região** | `us-central1-a` |
| **Tipo de Instância** | `e2-medium` (2 vCPUs, 4 GB RAM + 2 GB Swap SSD) |
| **Disco** | 63 GB Standard Persistent Disk |
| **Web Server / Reverse Proxy** | Nginx 1.22+ (portas 80 e 443 com WebSockets e SSL Let's Encrypt) |
| **Serviço de Aplicação** | Systemd unit `tokstance.service` (Python 3 / FastAPI / Gradio na porta interna 7860) |
| **Diretório da Aplicação em Produção** | `/opt/tokstance` |

---

## 🔑 Como Conectar à Máquina Virtual

### 1. Pelo Antigravity IDE (Recomendado)
A conexão já está pré-configurada no seu arquivo `C:\Users\gusta\.ssh\config`:
1. Pressione `Ctrl + Shift + P` no Antigravity IDE.
2. Selecione: **`Remote-SSH: Connect to Host...`**
3. Escolha: **`tokstance-gcp`**.
4. Uma nova janela se abrirá conectada diretamente à VM, com explorador de arquivos e terminal integrado.

### 2. Pelo Terminal Local (SSH)
```bash
ssh tokstance-gcp
# ou especificando a chave diretamente:
ssh -i ~/.ssh/ssh-key-2026-09-07.key gustavocunha@34.56.250.144
```

### 3. Pelo Console Web do Google Cloud
No painel do Google Cloud Console ➔ **Compute Engine** ➔ **Instâncias de VM**, clique no botão cinza **`SSH`** na linha da máquina `instance-tikstancev2`. O terminal abrirá direto no navegador.

---

## 📊 Comandos de Diagnóstico e Monitoramento

Execute estes comandos no terminal da VM:

### 1. Verificar se a aplicação está rodando (Status do Serviço)
```bash
sudo systemctl status tokstance.service
```
> [!NOTE]
> Você deve ver o indicador verde `● Active: active (running)`. Para sair da tela caso não feche automaticamente, pressione a tecla **`q`**.

### 2. Acompanhar os Logs em Tempo Real (Live Streaming)
```bash
sudo journalctl -u tokstance.service -f
```
> [!TIP]
> Exibe cada requisição HTTP, logins, anotações de vídeos e erros no instante em que acontecem. Para sair e liberar o terminal, aperte **`Ctrl + C`**.

### 3. Ver as Últimas 50 Linhas de Log
```bash
sudo journalctl -u tokstance.service -n 50 --no-pager
```

### 4. Monitorar Consumo de Memória e Disco
```bash
# Ver uso de memória RAM física e memória Swap
free -h

# Ver espaço livre em disco
df -h /
```

---

## 🔍 Consultas SQL no Banco de Dados SQLite e Auditoria

Na VM, todas as informações estruturadas (usuários, tarefas, membros, anotações, reservas e acessos) residem no banco de dados SQLite em **`/opt/tokstance/data/tokstance.db`**.

Execute os comandos abaixo diretamente no terminal da VM:

### 1. Tabela de Usuários Cadastrados (`usuarios`)
Para listar os usuários registrados na plataforma, seus e-mails cadastrados, nomes completos e data de criação:
```bash
sqlite3 -header -column /opt/tokstance/data/tokstance.db \
  "SELECT usuario_id, nome_usuario, email, nome_completo, criado_em FROM usuarios ORDER BY usuario_id ASC;"
```
> [!NOTE]
> O hash seguro da senha (bcrypt/argon2) é omitido nesta consulta para manter a visualização limpa e legível no terminal.

### 2. Códigos de Recuperação de Senha (`recuperacao_senha`)
Caso alguém solicite redefinição de senha na tela inicial e você precise resgatar o código de 6 dígitos gerado:
```bash
sqlite3 -header -column /opt/tokstance/data/tokstance.db \
  "SELECT r.recuperacao_id, u.nome_usuario, u.email, r.codigo_recuperacao, r.usado, r.expira_em, r.criado_em \
   FROM recuperacao_senha r \
   JOIN usuarios u ON r.usuario_id = u.usuario_id \
   ORDER BY r.recuperacao_id DESC LIMIT 10;"
```

### 3. Rodadas de Pesquisa Criadas (`tarefas`)
Para consultar as tarefas configuradas, código de convite, quantidade de vagas e criador:
```bash
sqlite3 -header -column /opt/tokstance/data/tokstance.db \
  "SELECT t.tarefa_id, t.titulo, t.codigo_convite, t.numero_vagas, t.percentual_sobreposicao, u.nome_usuario AS criador, t.criado_em \
   FROM tarefas t \
   JOIN usuarios u ON t.criado_por_usuario_id = u.usuario_id \
   ORDER BY t.tarefa_id ASC;"
```

### 4. Membros e Ocupação de Vagas por Tarefa (`membros_tarefa`)
Para conferir quais usuários entraram em cada tarefa, qual papel exercem e qual vaga ocupam:
```bash
sqlite3 -header -column /opt/tokstance/data/tokstance.db \
  "SELECT m.tarefa_id, t.titulo, u.nome_usuario, u.nome_completo, m.papel, m.vaga_atribuida, m.entrou_em \
   FROM membros_tarefa m \
   JOIN tarefas t ON m.tarefa_id = t.tarefa_id \
   JOIN usuarios u ON m.usuario_id = u.usuario_id \
   ORDER BY m.tarefa_id, m.vaga_atribuida;"
```

### 5. Progresso de Rotulação por Usuário (Atribuídos vs Concluídos)
Para auditar quantos vídeos foram atribuídos para cada rotulador e quantos já foram salvos:
```bash
sqlite3 -header -column /opt/tokstance/data/tokstance.db \
  "SELECT a.tarefa_id, a.labeler, \
          COUNT(DISTINCT a.video_id) AS videos_atribuidos, \
          COUNT(DISTINCT n.video_id) AS videos_rotulados, \
          ROUND(COUNT(DISTINCT n.video_id) * 100.0 / COUNT(DISTINCT a.video_id), 1) || '%' AS progresso \
   FROM atribuicoes a \
   LEFT JOIN anotacoes n ON a.tarefa_id = n.tarefa_id AND a.labeler = n.labeler AND a.video_id = n.video_id \
   GROUP BY a.tarefa_id, a.labeler;"
```

### 6. Distribuição de Posicionamentos / Rótulos Salvos (`anotacoes`)
Para inspecionar a contagem de votos computados por classe (Contra, A Favor, Neutro) e tempo médio de análise:
```bash
sqlite3 -header -column /opt/tokstance/data/tokstance.db \
  "SELECT tarefa_id, stance, COUNT(*) AS total, \
          ROUND(AVG(tempo_analise_segundos), 1) AS tempo_medio_seg \
   FROM anotacoes GROUP BY tarefa_id, stance ORDER BY tarefa_id, total DESC;"
```

### 7. Últimas Rotulações Realizadas (Anotações Salvas)
Para inspecionar as anotações gravadas mais recentes, o rotulador, o posicionamento escolhido e o tempo gasto:
```bash
sqlite3 -header -column /opt/tokstance/data/tokstance.db \
  "SELECT anotacao_id, labeler, video_id, stance, tempo_analise_segundos, timestamp \
   FROM anotacoes ORDER BY anotacao_id DESC LIMIT 15;"
```

### 8. Relatos de Erros e Substituições por Reserva (`erros_videos`)
Para auditar quando um rotulador informou que o vídeo não carregou e qual vídeo substituto foi alocado da reserva técnica:
```bash
sqlite3 -header -column /opt/tokstance/data/tokstance.db \
  "SELECT erro_id, labeler, video_id, replacement_video_id, replacement_status, timestamp \
   FROM erros_videos ORDER BY erro_id DESC LIMIT 10;"
```

### 9. Acervo de Vídeos Principais e Reservas Técnicas (`videos_tarefa`)
Para conferir a quantidade de vídeos principais e em reserva técnica cadastrados para cada tarefa:
```bash
sqlite3 -header -column /opt/tokstance/data/tokstance.db \
  "SELECT tarefa_id, tipo_pool, COUNT(*) AS quantidade \
   FROM videos_tarefa GROUP BY tarefa_id, tipo_pool ORDER BY tarefa_id, tipo_pool;"
```

### 10. Últimos Logs de Acesso (Logins, Logouts e Navegação)
Para ver os acessos mais recentes registrados no banco:
```bash
sqlite3 -header -column /opt/tokstance/data/tokstance.db \
  "SELECT log_id, usuario, acao, timestamp FROM logs_acesso ORDER BY log_id DESC LIMIT 15;"
```
> [!NOTE]
> Ações registradas: `login`, `logout`, `criar_tarefa`, `entrar_tarefa_convite`, `aceitar_aviso_sensivel` e `parar_rotulacao`.

### 11. Relatório Consolidado de Status do Banco e Progresso
Para ver uma visão geral estruturada com usuários, tarefas ativas, vagas ocupadas, progresso de anotação de cada rotulador e estoque de reservas:
```bash
cd /opt/tokstance
PYTHONPATH=src /opt/tokstance/.venv/bin/python3 scripts/status_banco.py
```
> [!TIP]
> Esse comando também atualiza automaticamente o arquivo `/opt/tokstance/STATUS_BANCO.md`.

### 12. Acompanhar Requisições Web e Acessos em Tempo Real
Para ver as requisições HTTP e conexões de rede no instante em que ocorrem:
```bash
# Logs da aplicação Python e FastAPI
sudo journalctl -u tokstance.service -f

# Logs do servidor web Nginx com IP de origem e status HTTP
sudo tail -f /var/log/nginx/access.log
```

---

## 🚀 Como Subir Atualizações de Código (Deploy de Novas Versões)

O serviço de produção executa o código que reside em **`/opt/tokstance`**. Quando você fizer alterações no computador local e der `git push origin main`:

### Opção Rápida (Script Automatizado de Atualização de Código):
Conecte-se na VM pelo terminal e execute o script genérico (ele puxa o Git, sincroniza dependências e reinicia o serviço, **sem alterar o banco de dados**):

```bash
cd /opt/tokstance
bash deploy/atualizar.sh
```

### Reiniciar o Banco de Dados com Dados de Demonstração (Demo):
Caso deseje resetar a base relacional SQLite para o estado original da avaliação do professor com os vídeos autênticos de `videos.csv`:

```bash
cd /opt/tokstance
bash deploy/resetar_banco_demo.sh
```

---

## 🛡️ Checklist de Alta Disponibilidade (Garantir 24/7 até 06/12)

Para garantir que o professor consiga acessar o sistema sem nenhuma interrupção até a data limite da disciplina:

### 1. Créditos do Google Cloud vs Consumo
* **Saldo de Créditos:** R$ 1.746,74 (período de avaliação).
* **Consumo Mensal da VM (`e2-medium`):** Aprox. **R$ 130 a R$ 160 por mês** ligada 24h.
* **Gasto até 06/12 (29 dias):** Aprox. **R$ 145**. Os créditos cobrem mais de 10 vezes essa despesa.

> [!IMPORTANT]
> **Ação Preventiva no GCP (Fazer Upgrade da Conta):**
> O banner do Google Cloud alerta sobre *"30 dias restantes"*. Como 30 dias contados a partir de 07/11 vencem em 07/12, faça o upgrade da conta clicando no botão azul **"Fazer upgrade"** no console do GCP:
> - Você **NÃO perde os créditos** de R$ 1.746,74 (o próprio banner garante que eles continuam sendo usados).
> - Isso evita que o Google suspenda a VM no momento exato do encerramento dos 30 dias de teste gratuito.

### 2. Fixar o IP Externo como Estático
Por padrão, o IP da VM (`34.56.250.144`) é efêmero (pode mudar se a GCP reiniciar o host físico):
1. No GCP Console, vá em **Rede VPC** ➔ **Endereços IP externos**.
2. Localize a linha do IP `34.56.250.144` da `instance-tikstancev2`.
3. Altere a coluna **Tipo** de *Efêmero* para **Estático** (ou clique nos três pontinhos ➔ *Promover para endereço IP estático*).
4. Dê um nome (ex: `ip-tokstance`) e confirme. *(Enquanto a VM estiver ligada, o IP estático é 100% gratuito).*

### 3. Memória SWAP Ativada (Proteção contra OOM-Killer)
* Foi criado um arquivo de troca de **2 GB de SWAP** em `/swapfile` e configurado no `/etc/fstab`.
* A VM agora conta com **6 GB de memória utilizável** (4 GB RAM + 2 GB Swap), impedindo que o sistema operacional derrube a aplicação em momentos de pico de acessos.

### 4. Reinicialização Automática em Caso de Falhas (Systemd)
O serviço `/etc/systemd/system/tokstance.service` está configurado com:
* `Restart=always`: Se o processo Python sofrer qualquer interrupção, o Linux o reinicia automaticamente.
* `RestartSec=5s`: O reinício ocorre em no máximo 5 segundos.

### 5. Certificado SSL / HTTPS
* O certificado SSL foi emitido pela Let's Encrypt via Certbot e possui validade inicial de 90 dias (fevereiro de 2027).
* O temporizador `certbot.timer` já está ativo no sistema para renovação automática, garantindo navegação segura com cadeado verde sem necessidade de intervenção.

---

## 🎨 Identidade Visual e Favicon

* **Ícone da Aba:** O ícone do navegador foi personalizado com o logo **`T!`** na tipografia e tom carmesim (`#9c0014`) da identidade do TokStance!.
* **Arquivos Estáticos:** Localizados em `src/tokstance/frontend/static/` (`favicon.svg`, `favicon.ico`, `favicon.png`).
* **Cache do Navegador:** Caso você acesse e ainda veja o ícone anterior em cache, utilize o atalho de recarregamento forçado no navegador:
  * **Windows / Linux:** `Ctrl + F5` ou `Ctrl + Shift + R`
  * **macOS:** `Cmd + Shift + R`

