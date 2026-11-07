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

* **Ícone da Aba:** O ícone do navegador foi personalizado com o logo **`t!`** na tipografia e tom carmesim (`#9c0014`) da identidade do TokStance!.
* **Arquivos Estáticos:** Localizados em `src/tokstance/frontend/static/` (`favicon.svg`, `favicon.ico`, `favicon.png`).
* **Cache do Navegador:** Caso você acesse e ainda veja o ícone anterior em cache, utilize o atalho de recarregamento forçado no navegador:
  * **Windows / Linux:** `Ctrl + F5` ou `Ctrl + Shift + R`
  * **macOS:** `Cmd + Shift + R`

