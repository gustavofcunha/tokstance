"""Tema visual branco de alto contraste e estilos CSS globais (versao inicial do frontend)."""

from typing import Any
import gradio as gr

COR_PRIMARIA = "#9c0014"
COR_PRIMARIA_HOVER = "#7a0010"
COR_SECUNDARIA = "#176b87"
COR_ALERTA = "#b56b00"
COR_SUCESSO = "#4f6f52"
COR_FUNDO = "#f8fafc"
COR_BRANCO = "#ffffff"
COR_TEXTO_TITULO = "#0f172a"
COR_TEXTO_CORPO = "#1e293b"
COR_TEXTO_MUTED = "#475569"
COR_BORDA = "#e2e8f0"
COR_BORDA_INPUT = "#cbd5e1"

JS_FORCAR_MODO_CLARO = """
() => {
    function atualizarFavicon() {
        let link = document.querySelector("link[rel*='icon']");
        if (!link) {
            link = document.createElement('link');
            link.rel = 'icon';
            document.head.appendChild(link);
        }
        link.type = 'image/svg+xml';
        link.href = '/favicon.svg?v=2';
    }
    atualizarFavicon();
    setTimeout(atualizarFavicon, 300);
    setTimeout(atualizarFavicon, 1000);

    function travarModoClaro() {
        document.documentElement.classList.remove('dark');
        document.body.classList.remove('dark');
        document.documentElement.setAttribute('data-theme', 'light');
    }
    travarModoClaro();
    const observerModo = new MutationObserver(() => {
        if (document.documentElement.classList.contains('dark') || document.body.classList.contains('dark')) {
            travarModoClaro();
        }
    });
    observerModo.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    observerModo.observe(document.body, { attributes: true, attributeFilter: ['class'] });

    const svgOlho = '<svg class="icone-olho-svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>';
    const svgOlhoFechado = '<svg class="icone-olho-svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" x2="22" y1="2" y2="22"/></svg>';

    function configurarOlhoSenha(inp) {
        if (!inp || inp.dataset.olhoConfigurado) return;
        inp.dataset.olhoConfigurado = '1';
        inp.classList.add('tem-olho-senha');
        const container = inp.closest('.input-container') || inp.parentElement;
        if (!container) return;
        container.classList.add('container-olho-senha');

        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn-olho-senha';
        btn.setAttribute('aria-label', 'Mostrar senha');
        btn.title = 'Mostrar senha';
        btn.innerHTML = svgOlho;

        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const visivel = inp.type === 'text';
            inp.type = visivel ? 'password' : 'text';
            btn.innerHTML = visivel ? svgOlho : svgOlhoFechado;
            const rotulo = visivel ? 'Mostrar senha' : 'Ocultar senha';
            btn.setAttribute('aria-label', rotulo);
            btn.title = rotulo;
            inp.focus();
        });

        container.appendChild(btn);
    }

    function varrerCamposSenha() {
        document.querySelectorAll('input[type="password"], input.tem-olho-senha').forEach(configurarOlhoSenha);
    }

    function reiniciarAnimacaoToasts() {
        document.querySelectorAll('.tokstance-toast').forEach((el) => {
            const nonce = el.getAttribute('data-nonce') || el.innerText;
            if (el.dataset.lastNonce !== nonce) {
                el.dataset.lastNonce = nonce;
                el.style.animation = 'none';
                void el.offsetHeight;
                el.style.animation = '';
            }
        });
    }

    function configurarFuncoesDiscordancia() {
        window.tokstanceAplicarFiltrosDiscordancia = function(cardEl) {
            if (!cardEl) return;
            const inputEl = cardEl.querySelector('.disagreement-search-input');
            const termo = inputEl ? (inputEl.value || '').trim().toLowerCase() : '';
            const btnAtivo = cardEl.querySelector('.disagreement-filter-btn.active');
            const sevFiltro = btnAtivo ? (btnAtivo.getAttribute('data-filter') || 'all') : 'all';
            const linhas = cardEl.querySelectorAll('tr.disagreement-row');
            let visiveis = 0;
            linhas.forEach(function(tr) {
                const sev = tr.getAttribute('data-severity') || '';
                const busca = (tr.getAttribute('data-search') || tr.innerText || '').toLowerCase();
                const passaSev = (sevFiltro === 'all') || (sev === sevFiltro);
                const passaTermo = !termo || busca.indexOf(termo) !== -1;
                if (passaSev && passaTermo) {
                    tr.style.display = '';
                    visiveis += 1;
                } else {
                    tr.style.display = 'none';
                }
            });
            const linhaVazia = cardEl.querySelector('.disagreement-no-match-row');
            if (linhaVazia) {
                linhaVazia.style.display = (linhas.length > 0 && visiveis === 0) ? '' : 'none';
            }
        };

        window.tokstanceFiltrarDiscordancia = function(inputEl) {
            const cardEl = inputEl ? inputEl.closest('.disagreement-full-card') : document.querySelector('.disagreement-full-card');
            window.tokstanceAplicarFiltrosDiscordancia(cardEl);
        };

        window.tokstanceFiltrarSeveridade = function(btnEl, sev) {
            if (!btnEl) return;
            const cardEl = btnEl.closest('.disagreement-full-card') || document.querySelector('.disagreement-full-card');
            if (cardEl) {
                cardEl.querySelectorAll('.disagreement-filter-btn').forEach(function(b) {
                    b.classList.toggle('active', b === btnEl);
                });
                window.tokstanceAplicarFiltrosDiscordancia(cardEl);
            }
        };

        window.tokstanceAlternarPlayer = function(btnEl, containerId, url) {
            const box = document.getElementById(containerId);
            if (!box) return;
            const aberto = box.style.display !== 'none' && box.innerHTML.trim() !== '';
            if (aberto) {
                box.style.display = 'none';
                box.innerHTML = '';
                if (btnEl) {
                    btnEl.innerText = '▶ Assistir vídeo';
                    btnEl.classList.remove('active');
                }
            } else {
                const limpo = String(url || '').replace(/\/+$/, '').split('/').pop().split('?')[0];
                const playerUrl = 'https://www.tiktok.com/player/v1/' + encodeURIComponent(limpo) + '?music_info=1&description=1&rel=0';
                box.innerHTML = '<iframe src="' + playerUrl + '" title="Preview do vídeo TikTok" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen scrolling="no"></iframe>';
                box.style.display = 'block';
                if (btnEl) {
                    btnEl.innerText = '✕ Ocultar vídeo';
                    btnEl.classList.add('active');
                }
            }
        };
    }

    function executarRotinasInterface() {
        varrerCamposSenha();
        reiniciarAnimacaoToasts();
        configurarAtalhoEnter();
        configurarFuncoesDiscordancia();
    }

    function configurarAtalhoEnter() {
        if (window._tokstanceEnterConfigurado) return;
        window._tokstanceEnterConfigurado = true;

        document.addEventListener('keydown', function(e) {
            if (e.key !== 'Enter' || e.isComposing) return;

            // Se o usuario estiver digitando em uma textarea multilinha, respeitar a quebra de linha
            if (e.target && e.target.tagName === 'TEXTAREA') return;

            // 1. Aviso de Conteudo Sensivel aberto
            const avisoSensivel = document.querySelector('.sensitive-warning-wrapper, .sensitive-warning-card');
            if (avisoSensivel && (avisoSensivel.offsetWidth > 0 || avisoSensivel.offsetHeight > 0) && window.getComputedStyle(avisoSensivel).display !== 'none') {
                const btnContinuar = avisoSensivel.querySelector('.sensitive-btn-continue, button.sensitive-btn-continue');
                if (btnContinuar && !btnContinuar.disabled && (btnContinuar.offsetWidth > 0 || btnContinuar.offsetHeight > 0)) {
                    e.preventDefault();
                    btnContinuar.click();
                    return;
                }
            }

            // 2. Modal de Convite (Ingressar em Tarefa)
            const modalConvite = document.querySelector('.modal-overlay:not(.hide):not(.hidden), #modal_convite');
            if (modalConvite && (modalConvite.offsetWidth > 0 || modalConvite.offsetHeight > 0) && window.getComputedStyle(modalConvite).display !== 'none') {
                const btnEntrar = modalConvite.querySelector('.modal-btn-confirm, button.modal-btn-confirm, button.ufmg-btn');
                if (btnEntrar && !btnEntrar.disabled) {
                    e.preventDefault();
                    btnEntrar.click();
                    return;
                }
            }

            // 3. Etapas do Wizard de Criacao
            const wizard3 = document.querySelector('.wizard-passo-3');
            if (wizard3 && (wizard3.offsetWidth > 0 || wizard3.offsetHeight > 0) && window.getComputedStyle(wizard3).display !== 'none') {
                const btnCriar = wizard3.querySelector('.wizard-submit-btn, button.wizard-submit-btn');
                if (btnCriar && !btnCriar.disabled) {
                    e.preventDefault();
                    btnCriar.click();
                    return;
                }
            }

            const wizard2 = document.querySelector('.wizard-passo-2');
            if (wizard2 && (wizard2.offsetWidth > 0 || wizard2.offsetHeight > 0) && window.getComputedStyle(wizard2).display !== 'none') {
                const btnProx2 = wizard2.querySelector('.wizard-next-btn, button.wizard-next-btn');
                if (btnProx2 && !btnProx2.disabled) {
                    e.preventDefault();
                    btnProx2.click();
                    return;
                }
            }

            const wizard1 = document.querySelector('.wizard-passo-1');
            if (wizard1 && (wizard1.offsetWidth > 0 || wizard1.offsetHeight > 0) && window.getComputedStyle(wizard1).display !== 'none') {
                const btnProx1 = wizard1.querySelector('.wizard-next-btn, button.wizard-next-btn');
                if (btnProx1 && !btnProx1.disabled) {
                    e.preventDefault();
                    btnProx1.click();
                    return;
                }
            }

            // 4. Workspace de Rotulacao (com radio selecionado)
            const painelRotulador = document.querySelector('.labeler-panel');
            if (painelRotulador && (painelRotulador.offsetWidth > 0 || painelRotulador.offsetHeight > 0) && window.getComputedStyle(painelRotulador).display !== 'none') {
                const aviso = document.querySelector('.sensitive-warning-wrapper');
                const avisoAberto = aviso && (aviso.offsetWidth > 0 || aviso.offsetHeight > 0) && window.getComputedStyle(aviso).display !== 'none';
                if (!avisoAberto) {
                    const radioChecked = painelRotulador.querySelector('.wrap-radio input[type="radio"]:checked');
                    if (radioChecked) {
                        const btnSalvar = painelRotulador.querySelector('.annotation-controls button.ufmg-btn');
                        if (btnSalvar && !btnSalvar.disabled) {
                            e.preventDefault();
                            btnSalvar.click();
                            return;
                        }
                    }
                }
            }
        }, true);
    }

    executarRotinasInterface();
    const observadorGeral = new MutationObserver(executarRotinasInterface);
    if (document.body) {
        observadorGeral.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['data-nonce'] });
    } else {
        document.addEventListener('DOMContentLoaded', () => {
            observadorGeral.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['data-nonce'] });
        });
    }
    if (!window._tokstanceRotinasInterval) {
        window._tokstanceRotinasInterval = setInterval(executarRotinasInterface, 300);
    }
}
"""

APP_CSS = """
    /* =========================================================================
       1. TIPOGRAFIA UNIFORME DO SISTEMA (SEM MISTURA DE FONTES OU GLIFOS INCOMPLETOS)
       ========================================================================= */
    html, body, .gradio-container, .gradio-container *, button, input, textarea, select {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
    }

    /* =========================================================================
       2. FORCAR TEMA CLARO E ALTO CONTRASTE (NEUTRALIZAR MODO ESCURO)
       ========================================================================= */
    :root, html, body, .dark, html.dark, body.dark {
        color-scheme: light !important;
        background-color: #f8fafc !important;
        background: #f8fafc !important;
        color: #0f172a !important;
    }

    /* remove o espaco em branco superior em todas as telas */
    .gradio-container .main,
    .gradio-container > .main.fillable,
    .gradio-container .main.fillable.app {
        padding: 0 !important;
    }
    .gradio-container .column:has(> .shell),
    .gradio-container .column:has(.shell) {
        gap: 0 !important;
    }
    .gradio-container .form:has(+ .shell) {
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
        overflow: hidden !important;
    }

    /* Container Principal com Otimizacao Total para Telas Widescreen (16:9, 16:10, 21:9) */
    .shell {
        width: min(98%, 1880px) !important;
        max-width: 1880px !important;
        margin: 0 auto !important;
        background: #ffffff !important;
        padding: 14px 22px !important;
        border-radius: 12px !important;
        font-size: 15px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04), 0 1px 3px rgba(0, 0, 0, 0.02) !important;
        border: 1px solid #e2e8f0 !important;
        border-top: 5px solid #9c0014 !important;
        position: relative !important;
        box-sizing: border-box !important;
    }

    .gradio-container, .gradio-container .main, .gradio-container .contain {
        max-width: none !important;
        width: 100% !important;
        background: #f8fafc !important;
        overflow-x: hidden !important;
    }

    /* Exterminar containers pretos e caixas escuras do Gradio */
    .dark .block,
    .dark div[data-testid="block"],
    .dark .form,
    .dark fieldset,
    .dark .gr-box,
    .dark .gr-panel,
    .dark .gr-form,
    .dark .gap,
    .dark [data-testid="textbox"],
    .dark [data-testid="dropdown"],
    .dark .wrap,
    .dark [data-testid="dataframe"],
    .dark [role="tabpanel"],
    .block,
    div[data-testid="block"],
    .form,
    fieldset,
    .gr-box,
    .gr-panel,
    .gr-form,
    .gap,
    [role="tabpanel"] {
        background-color: #ffffff !important;
        background: #ffffff !important;
        border-color: #e2e8f0 !important;
        color: #0f172a !important;
        box-shadow: none !important;
    }

    /* Inputs, Textareas, Selects e Dropdowns com visual limpo e claro */
    .dark input:not([type="checkbox"]):not([type="radio"]),
    .dark textarea,
    .dark select,
    .dark .gr-input,
    .dark [data-testid="dropdown"] input,
    .dark .wrap-default,
    .dark .secondary-wrap,
    .dark .reference-container,
    input:not([type="checkbox"]):not([type="radio"]),
    textarea,
    select,
    .gr-input,
    .wrap-default,
    .secondary-wrap {
        background-color: #ffffff !important;
        background: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        font-size: 15px !important;
        font-weight: 500 !important;
        padding: 9px 12px !important;
    }

    input:focus,
    textarea:focus,
    select:focus {
        border-color: #9c0014 !important;
        box-shadow: 0 0 0 3px rgba(156, 0, 20, 0.12) !important;
        outline: none !important;
    }

    /* Checkboxes com visual nativo de alto contraste */
    input[type="checkbox"],
    .dark input[type="checkbox"] {
        appearance: auto !important;
        -webkit-appearance: checkbox !important;
        accent-color: #9c0014 !important;
        width: 18px !important;
        height: 18px !important;
        min-width: 18px !important;
        margin: 0 10px 0 0 !important;
        padding: 0 !important;
        cursor: pointer !important;
        border-radius: 4px !important;
        vertical-align: middle !important;
    }

    label:has(input[type="checkbox"]),
    .dark label:has(input[type="checkbox"]) {
        display: inline-flex !important;
        align-items: center !important;
        cursor: pointer !important;
        color: #0f172a !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        background: transparent !important;
        border: none !important;
        padding: 4px 0 !important;
    }

    /* Exterminar fundo escuro de tabelas e dataframes no Gradio */
    .dataframe,
    [data-testid="dataframe"],
    [data-testid="dataframe"] *,
    .dark [data-testid="dataframe"],
    .dark [data-testid="dataframe"] *,
    .table-wrap,
    .table-wrap *,
    .dark .table-wrap,
    .dark .table-wrap *,
    .virtual-table-viewport,
    .virtual-table-viewport *,
    .dark .virtual-table-viewport,
    .dark .virtual-table-viewport *,
    table,
    tbody,
    thead,
    tr,
    th,
    td,
    .dark table,
    .dark tbody,
    .dark thead,
    .dark tr,
    .dark th,
    .dark td,
    div[role="grid"],
    div[role="row"],
    div[role="gridcell"],
    div[role="columnheader"],
    .dark div[role="grid"],
    .dark div[role="row"],
    .dark div[role="gridcell"],
    .dark div[role="columnheader"],
    .cell-wrap,
    .cell-wrap input,
    .dark .cell-wrap,
    .dark .cell-wrap input {
        background-color: #ffffff !important;
        background: #ffffff !important;
        color: #0f172a !important;
        border-color: #e2e8f0 !important;
    }

    div[role="columnheader"],
    th,
    thead tr,
    .header-cell,
    .dark div[role="columnheader"],
    .dark th,
    .dark thead tr,
    .dark .header-cell {
        background-color: #f1f5f9 !important;
        background: #f1f5f9 !important;
        color: #0f172a !important;
        font-weight: 700 !important;
    }

    tbody tr:nth-child(even),
    div[role="row"]:nth-child(even),
    .dark tbody tr:nth-child(even),
    .dark div[role="row"]:nth-child(even) {
        background-color: #f8fafc !important;
        background: #f8fafc !important;
    }

    tbody tr:nth-child(odd),
    div[role="row"]:nth-child(odd),
    .dark tbody tr:nth-child(odd),
    .dark div[role="row"]:nth-child(odd) {
        background-color: #ffffff !important;
        background: #ffffff !important;
    }

    .cell-wrap input,
    .dark .cell-wrap input {
        color: #0f172a !important;
        font-weight: 600 !important;
    }

    /* Rótulos de Campos (Labels) de Alto Contraste */
    .dark label,
    .dark .block label,
    .dark label span,
    .dark .block-label,
    .dark span[data-testid="block-info"],
    label,
    .block label,
    label span,
    .block-label,
    span[data-testid="block-info"] {
        color: #0f172a !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        margin-bottom: 5px !important;
        letter-spacing: 0.01em !important;
        background: transparent !important;
    }

    /* Textos informativos de cabeçalho e markdown */
    h1, h2, h3, h4, h5, h6,
    .dark h1, .dark h2, .dark h3, .dark h4,
    strong, b, .dark strong, .dark b {
        color: #0f172a !important;
        font-weight: 700 !important;
    }

    p, span, div,
    .dark p, .dark span {
        color: #1e293b;
    }

    .brand-header {
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 14px;
        margin-bottom: 16px;
        text-align: left !important;
    }
    .brand-header h1 {
        font-size: 28px !important;
        font-weight: 800 !important;
        margin: 0 !important;
        color: #9c0014 !important;
        letter-spacing: -0.02em !important;
    }
    .brand-header p {
        color: #475569 !important;
        margin: 4px 0 0 !important;
        font-size: 14px !important;
        line-height: 1.4;
    }

    /* =========================================================================
       2. ABAS (TABS) MODERNAS ESTILO SEGMENTED CONTROL (REFERO / SPELL.SH)
       ========================================================================= */
    .tab-nav,
    div[role="tablist"],
    .dark .tab-nav,
    .dark div[role="tablist"] {
        display: flex !important;
        background: #f1f5f9 !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        padding: 4px !important;
        margin-bottom: 20px !important;
        gap: 4px !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }

    .tab-nav button,
    div[role="tablist"] button,
    .dark .tab-nav button,
    .dark div[role="tablist"] button {
        flex: 1 1 0 !important;
        font-size: 13px !important;
        font-weight: 700 !important;
        color: #475569 !important;
        background: transparent !important;
        border: none !important;
        padding: 9px 12px !important;
        border-radius: 7px !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
        text-align: center !important;
        white-space: nowrap !important;
        outline: none !important;
        box-shadow: none !important;
    }

    .tab-nav button:hover,
    div[role="tablist"] button:hover,
    .dark .tab-nav button:hover,
    .dark div[role="tablist"] button:hover {
        color: #0f172a !important;
        background: rgba(255, 255, 255, 0.7) !important;
    }

    .tab-nav button.selected,
    div[role="tablist"] button[aria-selected="true"],
    div[role="tablist"] button.selected,
    .dark .tab-nav button.selected,
    .dark div[role="tablist"] button[aria-selected="true"],
    .dark div[role="tablist"] button.selected {
        color: #9c0014 !important;
        background: #ffffff !important;
        border: 1px solid #ffd6dc !important;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08) !important;
        font-weight: 800 !important;
        outline: none !important;
    }

    /* Elimina outline / contorno preto indesejado nos botoes de tab ativos do Gradio */
    .tab-nav button:focus,
    .tab-nav button:focus-visible,
    .tab-nav button:active,
    div[role="tablist"] button:focus,
    div[role="tablist"] button:focus-visible,
    div[role="tablist"] button:active,
    div[role="tablist"] button[aria-selected="true"]:focus,
    div[role="tablist"] button[aria-selected="true"]:focus-visible,
    .dark .tab-nav button:focus,
    .dark div[role="tablist"] button:focus {
        outline: none !important;
        border: 1px solid #ffd6dc !important;
        box-shadow: 0 1px 4px rgba(156, 0, 20, 0.12) !important;
    }

    /* =========================================================================
       3. TELA DE ACESSO (CARD CENTRALIZADO ELEGANTE)
       ========================================================================= */
    .auth-card {
        max-width: 460px !important;
        width: 100% !important;
        margin: 8px auto !important;
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-top: 5px solid #9c0014 !important;
        border-radius: 12px !important;
        padding: 22px 28px !important;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04) !important;
    }

    .auth-feedback-slot, .auth-feedback-slot.block {
        padding: 0 !important;
        margin: 0 !important;
        border: none !important;
        background: transparent !important;
        min-height: 0 !important;
    }
    span[data-testid="block-info"],
    .block-info,
    label small,
    label .info {
        font-size: 11.5px !important;
        color: #64748b !important;
        font-weight: 500 !important;
        margin-top: 3px !important;
        display: block !important;
        line-height: 1.35 !important;
    }
    .auth-inline-error {
        display: flex !important;
        align-items: center !important;
        gap: 10px !important;
        background: #fff0f2 !important;
        border: 1px solid #ffd6dc !important;
        border-left: 4px solid #9c0014 !important;
        border-radius: 8px !important;
        padding: 10px 14px !important;
        margin: 10px 0 12px 0 !important;
        color: #9c0014 !important;
        font-size: 13.5px !important;
        font-weight: 600 !important;
        line-height: 1.4 !important;
    }
    .auth-inline-error .auth-inline-icon {
        font-size: 16px !important;
        flex: 0 0 auto !important;
    }
    .auth-inline-error .auth-inline-text {
        flex: 1 1 auto !important;
    }
    .auth-inline-success {
        display: flex !important;
        align-items: center !important;
        gap: 10px !important;
        background: #f0fdf4 !important;
        border: 1px solid #bbf7d0 !important;
        border-left: 4px solid #16a34a !important;
        border-radius: 8px !important;
        padding: 10px 14px !important;
        margin: 10px 0 12px 0 !important;
        color: #166534 !important;
        font-size: 13.5px !important;
        font-weight: 600 !important;
        line-height: 1.4 !important;
    }
    .auth-inline-success .auth-inline-icon {
        font-size: 16px !important;
        flex: 0 0 auto !important;
        color: #16a34a !important;
    }
    .auth-inline-success .auth-inline-text {
        flex: 1 1 auto !important;
    }

    /* =========================================================================
       4. BOTOES PRIMARIOS E SECUNDARIOS
       ========================================================================= */
    button.ufmg-btn {
        background: #9c0014 !important;
        border: none !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        padding: 10px 20px !important;
        border-radius: 8px !important;
        cursor: pointer !important;
        box-shadow: 0 2px 4px rgba(156, 0, 20, 0.2) !important;
        transition: all 0.2s ease !important;
        min-height: 42px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-sizing: border-box !important;
        width: auto !important;
    }
    button.ufmg-btn:hover {
        background: #7a0010 !important;
        box-shadow: 0 4px 10px rgba(156, 0, 20, 0.3) !important;
        transform: translateY(-1px) !important;
    }

    button.secondary-btn,
    .secondary-btn,
    .wizard-step-footer button.secondary-btn,
    .compact-actions button.secondary-btn,
    .auth-actions-row button.secondary-btn,
    button.hub-btn.secondary-btn {
        background: #f1f5f9 !important;
        background-color: #f1f5f9 !important;
        border: 1px solid #cbd5e1 !important;
        color: #475569 !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        padding: 10px 18px !important;
        border-radius: 8px !important;
        cursor: pointer !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
        transition: all 0.2s ease !important;
        min-height: 42px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-sizing: border-box !important;
    }
    button.secondary-btn:hover,
    .secondary-btn:hover,
    .wizard-step-footer button.secondary-btn:hover,
    .compact-actions button.secondary-btn:hover,
    .auth-actions-row button.secondary-btn:hover,
    button.hub-btn.secondary-btn:hover {
        background: #e2e8f0 !important;
        background-color: #e2e8f0 !important;
        border-color: #94a3b8 !important;
        color: #1e293b !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.08) !important;
        transform: translateY(-1px) !important;
    }

    .auth-actions-row {
        display: flex !important;
        flex-direction: row !important;
        gap: 12px !important;
        width: 100% !important;
        margin-top: 10px !important;
    }
    .auth-actions-row > * {
        flex: 1 1 0 !important;
        min-width: 0 !important;
        width: 100% !important;
    }

    button.error-btn {
        background: #9c0014 !important;
        border: 1px solid #7a0010 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        padding: 10px 18px !important;
        border-radius: 8px !important;
        cursor: pointer !important;
        box-shadow: 0 2px 4px rgba(156, 0, 20, 0.2) !important;
        transition: all 0.2s ease !important;
        min-height: 42px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-sizing: border-box !important;
        width: auto !important;
    }
    button.error-btn:hover {
        background: #7a0010 !important;
        border-color: #5c000c !important;
        color: #ffffff !important;
        box-shadow: 0 4px 10px rgba(156, 0, 20, 0.3) !important;
        transform: translateY(-1px) !important;
    }

    /* =========================================================================
       5. PAINEL PRINCIPAL DE TAREFAS
       ========================================================================= */
    .hub-header-bar {
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        border-bottom: 1px solid #e2e8f0 !important;
        padding-bottom: 18px !important;
        margin-bottom: 24px !important;
        flex-wrap: wrap !important;
        gap: 16px !important;
    }

    .hub-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
        gap: 14px;
        margin: 8px 0 14px;
        max-height: 240px !important;
        overflow-y: auto !important;
    }

    .hub-join-box {
        margin-top: 14px !important;
        padding: 12px 18px !important;
        background: #f8fafc !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.02) !important;
    }
    .hub-join-row {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 16px !important;
        width: 100% !important;
    }

    .hub-card {
        border: 1px solid #e2e8f0;
        border-left: 5px solid #176b87;
        padding: 20px;
        background: #ffffff;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .hub-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 14px rgba(0, 0, 0, 0.07);
    }
    .hub-card.admin {
        border-left-color: #9c0014;
    }
    .hub-card h4 {
        margin: 0;
        color: #0f172a;
        font-size: 18px;
        font-weight: 700;
    }
    .hub-card-meta {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin: 14px 0 6px;
        font-size: 14px;
        color: #334155;
    }
    .hub-card-meta code {
        background: #f1f5f9;
        color: #9c0014;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 700;
        border: 1px solid #e2e8f0;
    }
    .hub-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .hub-badge.admin {
        background: #fff0f2;
        color: #9c0014;
        border: 1px solid #ffd6dc;
    }
    .hub-badge.rotulador {
        background: #eef8fa;
        color: #176b87;
        border: 1px solid #b8d8df;
    }

    .hub-section-box {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 22px 26px;
        margin-bottom: 24px;
    }
    .hub-section-box h3 {
        margin: 0 0 14px 0;
        font-size: 19px;
        color: #0f172a;
    }

    .hub-action-row {
        align-items: flex-end !important;
        gap: 14px !important;
        margin-top: 14px !important;
    }

    /* =========================================================================
       6. WIZARD, ROTULACAO, AUDITORIA E PAINEL ADMIN
       ========================================================================= */
    .admin-header {
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        border-bottom: 1px solid #e2e8f0 !important;
        padding-bottom: 16px !important;
        margin-bottom: 24px !important;
        flex-wrap: wrap !important;
        gap: 16px !important;
    }
    .admin-header h2 {
        margin: 0 !important;
        color: #0f172a !important;
        font-size: 24px !important;
        font-weight: 800 !important;
    }
    /* Painel Principal em duas colunas com tarefas lado a lado e botoes perfeitamente alinhados */
    .hub-two-col {
        display: flex !important;
        flex-direction: row !important;
        gap: 20px !important;
        width: 100% !important;
        align-items: stretch !important;
        margin-bottom: 20px !important;
    }
    @media (max-width: 1024px) {
        .hub-two-col {
            flex-direction: column !important;
        }
    }
    .hub-section-box {
        flex: 1 1 0 !important;
        min-width: 0 !important;
        height: 100% !important;
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        padding: 18px 20px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03) !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-start !important;
        box-sizing: border-box !important;
    }
    .hub-box-header {
        margin: 0 !important;
    }
    .hub-box-header h3 {
        margin: 0 !important;
        font-size: 18px !important;
        font-weight: 800 !important;
        color: #0f172a !important;
        line-height: 1.25 !important;
    }
    .hub-box-header p {
        margin: 3px 0 0 !important;
        font-size: 13px !important;
        color: #475569 !important;
        line-height: 1.3 !important;
    }
    .hub-action-row {
        display: flex !important;
        flex-direction: row !important;
        align-items: flex-end !important;
        gap: 10px !important;
        margin-top: 14px !important;
        width: 100% !important;
    }
    .hub-action-row > div:first-child {
        flex: 1 1 auto !important;
        min-width: 0 !important;
    }
    .hub-btn {
        height: 42px !important;
        min-height: 42px !important;
        max-height: 42px !important;
        padding: 0 20px !important;
        font-size: 14px !important;
        font-weight: 700 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        white-space: nowrap !important;
        margin: 0 !important;
        border-radius: 8px !important;
        box-sizing: border-box !important;
        min-width: fit-content !important;
    }

    .admin-actions {
        display: flex !important;
        justify-content: flex-end !important;
        gap: 12px !important;
    }

    /* Cartao de Configuracao Vigente com Alto Contraste */
    .admin-config-card {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-left: 5px solid #9c0014 !important;
        border-radius: 8px !important;
        padding: 16px 20px !important;
        margin: 12px 0 16px 0 !important;
    }
    .admin-config-title {
        font-size: 13px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        color: #9c0014 !important;
        letter-spacing: 0.05em !important;
        margin-bottom: 12px !important;
    }
    .admin-config-grid {
        display: grid !important;
        grid-template-columns: repeat(4, minmax(130px, 1fr)) !important;
        gap: 12px 18px !important;
    }
    .admin-config-grid .full-width {
        grid-column: 1 / -1 !important;
    }
    .config-item {
        display: flex !important;
        flex-direction: column !important;
        gap: 4px !important;
    }
    .config-label {
        font-size: 12px !important;
        font-weight: 700 !important;
        color: #475569 !important;
    }
    .config-val-badge {
        display: inline-block !important;
        background: #f1f5f9 !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        padding: 4px 10px !important;
        border-radius: 6px !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        width: fit-content !important;
    }
    .config-val-badge.convite {
        background: #fff0f2 !important;
        color: #9c0014 !important;
        border-color: #ffd6dc !important;
        font-family: monospace !important;
    }
    .config-val-text {
        font-size: 14px !important;
        font-weight: 600 !important;
        color: #0f172a !important;
        background: #f8fafc !important;
        padding: 8px 12px !important;
        border-radius: 6px !important;
        border: 1px solid #e2e8f0 !important;
    }

    /* Barra Superior do Workspace do Rotulador: Titulo a esquerda, Sair a direita */
    .labeler-header-bar {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: space-between !important;
        margin-bottom: 14px !important;
        padding-bottom: 12px !important;
        border-bottom: 1px solid #e2e8f0 !important;
        width: 100% !important;
    }
    .labeler-exit-btn {
        margin-left: auto !important;
        width: auto !important;
        min-width: 200px !important;
        height: 40px !important;
        padding: 0 20px !important;
        font-size: 14px !important;
        font-weight: 700 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    .workspace-header-title h2 {
        margin: 0 !important;
        font-size: 20px !important;
        font-weight: 800 !important;
        color: #0f172a !important;
    }
    .labeler-info-badge {
        display: inline-flex !important;
        align-items: center !important;
        gap: 8px !important;
        font-size: 14px !important;
        color: #334155 !important;
        font-weight: 600 !important;
    }
    .user-pill {
        display: inline-block !important;
        background: #f1f5f9 !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        padding: 3px 10px !important;
        border-radius: 6px !important;
        font-weight: 800 !important;
        font-size: 14px !important;
    }

    .labeler-actions {
        display: flex !important;
        justify-content: flex-end !important;
        align-items: center !important;
        margin-bottom: 18px !important;
    }

    .labeler-warning-stack {
        display: flex !important;
        flex-direction: column !important;
        gap: 6px !important;
        background: #f8fafc !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
        padding: 10px 14px !important;
        font-size: 13px !important;
        color: #475569 !important;
        margin-bottom: 12px !important;
    }
    .annotation-controls {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        padding: 16px 20px !important;
    }

    .form-wizard-card {
        border: 1px solid #e2e8f0 !important;
        border-top: 4px solid #9c0014 !important;
        padding: 26px 30px !important;
        background: #ffffff !important;
        border-radius: 14px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04) !important;
    }
    .wizard-header-banner {
        margin-bottom: 22px !important;
        padding-bottom: 16px !important;
        border-bottom: 1px solid #f1f5f9 !important;
    }
    .wizard-header-intro {
        display: flex !important;
        justify-content: space-between !important;
        align-items: flex-end !important;
        gap: 16px !important;
        margin-top: 4px !important;
        flex-wrap: wrap !important;
    }
    .wizard-header-main-title {
        margin: 0 !important;
        font-size: 21px !important;
        font-weight: 800 !important;
        color: #0f172a !important;
        letter-spacing: -0.01em !important;
    }
    .wizard-header-desc {
        margin: 4px 0 0 0 !important;
        font-size: 13.5px !important;
        color: #64748b !important;
    }
    .wizard-grid {
        display: flex !important;
        flex-direction: row !important;
        gap: 20px !important;
        width: 100% !important;
        align-items: stretch !important;
    }
    @media (max-width: 1024px) {
        .wizard-grid {
            flex-direction: column !important;
        }
    }
    .wizard-col {
        flex: 1 1 0 !important;
        min-width: 0 !important;
        display: flex !important;
        flex-direction: column !important;
        gap: 16px !important;
    }
    /* Stepper em etapas do assistente de criacao */
    .wizard-stepper-row {
        display: flex !important;
        flex-direction: row !important;
        gap: 12px !important;
        margin-bottom: 20px !important;
        width: 100% !important;
    }
    .wizard-tab-btn,
    button.wizard-tab-btn {
        flex: 1 1 0 !important;
        height: 44px !important;
        min-height: 44px !important;
        border-radius: 8px !important;
        font-size: 13.5px !important;
        font-weight: 700 !important;
        background: #f8fafc !important;
        border: 1px solid #cbd5e1 !important;
        color: #64748b !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
    }
    .wizard-tab-btn.active,
    button.wizard-tab-btn.active {
        background: #ffffff !important;
        border: 2px solid #9c0014 !important;
        color: #9c0014 !important;
        box-shadow: 0 2px 6px rgba(156, 0, 20, 0.12) !important;
    }
    .wizard-tab-btn.completed,
    button.wizard-tab-btn.completed {
        background: #f0fdf4 !important;
        border: 1px solid #86efac !important;
        color: #166534 !important;
    }
    .wizard-step-container {
        width: 100% !important;
        animation: fadeIn 0.15s ease-in-out !important;
    }
    .wizard-step-row {
        display: flex !important;
        flex-direction: row !important;
        gap: 20px !important;
        width: 100% !important;
        align-items: flex-start !important;
    }
    .wizard-step-row > * {
        flex: 1 1 0 !important;
        min-width: 0 !important;
    }
    .wizard-step-footer {
        display: flex !important;
        flex-direction: row !important;
        justify-content: space-between !important;
        align-items: center !important;
        margin-top: 20px !important;
        padding-top: 16px !important;
        border-top: 1px solid #e2e8f0 !important;
        width: 100% !important;
        gap: 12px !important;
    }
    .wizard-step-footer button {
        min-width: fit-content !important;
        width: auto !important;
        padding: 0 20px !important;
    }
    .wizard-next-btn,
    button.wizard-next-btn,
    .wizard-submit-btn,
    button.wizard-submit-btn {
        font-size: 14px !important;
        font-weight: 700 !important;
        height: 42px !important;
        min-height: 42px !important;
    }

    .wizard-section-card {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-left: 4px solid #9c0014 !important;
        border-radius: 10px !important;
        padding: 20px 22px !important;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.03) !important;
        display: flex !important;
        flex-direction: column !important;
        gap: 16px !important;
        box-sizing: border-box !important;
        height: auto !important;
    }
    .wizard-section-card.card-equipe {
        border-left-color: #0284c7 !important;
    }
    .wizard-section-card.card-videos {
        border-left-color: #059669 !important;
    }
    .wizard-section-header {
        display: flex !important;
        align-items: flex-start !important;
        gap: 12px !important;
        padding-bottom: 12px !important;
        border-bottom: 1px solid #f1f5f9 !important;
    }
    .wizard-badge {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 28px !important;
        height: 28px !important;
        border-radius: 50% !important;
        background: #fff0f2 !important;
        color: #9c0014 !important;
        font-weight: 800 !important;
        font-size: 13px !important;
        border: 1.5px solid #ffd6dc !important;
        flex-shrink: 0 !important;
        margin-top: 2px !important;
    }
    .wizard-badge.badge-blue {
        background: #e0f2fe !important;
        color: #0284c7 !important;
        border-color: #bae6fd !important;
    }
    .wizard-badge.badge-green {
        background: #ecfdf5 !important;
        color: #059669 !important;
        border-color: #a7f3d0 !important;
    }
    .wizard-section-title {
        margin: 0 !important;
        font-size: 16px !important;
        font-weight: 800 !important;
        color: #0f172a !important;
        letter-spacing: -0.01em !important;
    }
    .wizard-section-subtitle {
        margin: 3px 0 0 0 !important;
        font-size: 12.5px !important;
        color: #64748b !important;
        font-weight: 500 !important;
    }
    .wizard-info-callout {
        background: #f0fdf4 !important;
        border: 1px solid #bbf7d0 !important;
        border-left: 4px solid #059669 !important;
        border-radius: 6px !important;
        padding: 10px 14px !important;
        font-size: 12.5px !important;
        color: #166534 !important;
        line-height: 1.45 !important;
    }
    .wizard-info-callout code {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 4px !important;
        padding: 1px 5px !important;
        font-weight: 700 !important;
        color: #0f172a !important;
    }
    /* Cards de parametros do assistente (Etapa 2 e Etapa 3) */
    .wizard-passo-2 .form {
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
        overflow: visible !important;
    }
    .wizard-step2-bottom-row {
        align-items: stretch !important;
        margin-top: 14px !important;
    }
    .wizard-slider-card {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        padding: 14px 18px !important;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03) !important;
        box-sizing: border-box !important;
    }
    .wizard-slider-card .wrap {
        display: flex !important;
        flex-direction: column !important;
        align-items: stretch !important;
        gap: 12px !important;
        width: 100% !important;
        margin: 0 !important;
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        padding: 0 !important;
    }
    .wizard-slider-card .head {
        display: flex !important;
        flex-direction: row !important;
        justify-content: space-between !important;
        align-items: flex-start !important;
        gap: 12px !important;
        width: 100% !important;
        border: none !important;
        background: transparent !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    .wizard-slider-card .head label {
        display: flex !important;
        flex-direction: column !important;
        gap: 2px !important;
        margin: 0 !important;
        flex: 1 1 auto !important;
    }
    .wizard-slider-card .head label span[data-testid="block-info"] {
        font-size: 13.5px !important;
        font-weight: 700 !important;
        color: #0f172a !important;
        line-height: 1.3 !important;
        margin: 0 !important;
    }
    .wizard-slider-card .head label span.info,
    .wizard-slider-card .info {
        font-size: 12px !important;
        font-weight: 400 !important;
        color: #64748b !important;
        line-height: 1.35 !important;
        margin: 0 !important;
    }
    .wizard-slider-card .tab-like-container {
        display: flex !important;
        align-items: center !important;
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        height: auto !important;
        overflow: visible !important;
        flex-shrink: 0 !important;
        padding: 0 !important;
    }
    .wizard-slider-card .reset-button,
    .wizard-slider-card button.reset,
    .wizard-slider-card .head button,
    .gradio-slider .reset-button,
    .gradio-slider button.reset {
        display: none !important;
    }
    .wizard-slider-card input[type="number"],
    .gradio-slider input[type="number"] {
        background: #f8fafc !important;
        border: 1.5px solid #cbd5e1 !important;
        border-radius: 7px !important;
        padding: 2px 6px !important;
        font-weight: 800 !important;
        font-size: 14px !important;
        color: #9c0014 !important;
        width: 62px !important;
        height: 34px !important;
        text-align: center !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03) !important;
    }
    .wizard-slider-card input[type="number"]:focus,
    .gradio-slider input[type="number"]:focus {
        border-color: #9c0014 !important;
        background: #ffffff !important;
        outline: none !important;
        box-shadow: 0 0 0 2px rgba(156, 0, 20, 0.12) !important;
    }
    .wizard-slider-card .slider_input_container {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 14px !important;
        width: 100% !important;
        margin: 0 !important;
        padding: 2px 2px !important;
    }
    .wizard-slider-card .min_value,
    .wizard-slider-card .max_value {
        font-size: 13px !important;
        font-weight: 700 !important;
        color: #475569 !important;
        min-width: 24px !important;
        user-select: none !important;
        flex: 0 0 auto !important;
        line-height: 1 !important;
    }
    .wizard-slider-card .min_value {
        text-align: right !important;
    }
    .wizard-slider-card .max_value {
        text-align: left !important;
    }
    .wizard-slider-card input[type="range"],
    .gradio-slider input[type="range"] {
        flex: 1 1 auto !important;
        width: 100% !important;
        margin: 0 !important;
        accent-color: #9c0014 !important;
        cursor: pointer !important;
        height: 6px !important;
    }

    /* Cards inferiores da Etapa 2 (Convite e Participacao) */
    .wizard-custom-card {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        padding: 14px 18px !important;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03) !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: space-between !important;
        gap: 10px !important;
        box-sizing: border-box !important;
    }
    .wizard-custom-card > .block,
    .wizard-custom-card .html-container {
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
        min-height: 0 !important;
        overflow: visible !important;
    }
    .wizard-custom-card-header {
        display: flex !important;
        flex-direction: column !important;
        gap: 2px !important;
        margin: 0 !important;
    }
    .wizard-custom-card-title {
        font-size: 13.5px !important;
        font-weight: 700 !important;
        color: #0f172a !important;
        line-height: 1.3 !important;
    }
    .wizard-custom-card-subtitle {
        font-size: 12px !important;
        font-weight: 400 !important;
        color: #64748b !important;
        line-height: 1.35 !important;
    }
    .wizard-convite-inline-row {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 10px !important;
        width: 100% !important;
        margin: 0 !important;
    }
    .wizard-convite-inline-row > .form,
    .wizard-convite-inline-row > .wizard-convite-input {
        flex: 1 1 auto !important;
        min-width: 0 !important;
        width: auto !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .wizard-convite-input {
        flex: 1 1 auto !important;
        min-width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
    }
    .wizard-convite-input label,
    .wizard-convite-input .wrap {
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
        background: transparent !important;
    }
    .wizard-convite-input input,
    .wizard-convite-input textarea {
        height: 42px !important;
        min-height: 42px !important;
        max-height: 42px !important;
        padding: 10px 14px !important;
        line-height: 20px !important;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
        font-size: 14.5px !important;
        font-weight: 700 !important;
        letter-spacing: 0.04em !important;
        color: #0f172a !important;
        background: #f8fafc !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        box-sizing: border-box !important;
        resize: none !important;
        overflow: hidden !important;
        box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.02) !important;
    }
    .wizard-convite-input input:focus,
    .wizard-convite-input textarea:focus {
        border-color: #9c0014 !important;
        background: #ffffff !important;
        outline: none !important;
        box-shadow: 0 0 0 2px rgba(156, 0, 20, 0.12) !important;
    }
    .wizard-copy-code-btn,
    button.wizard-copy-code-btn,
    #btn_copiar_codigo_wizard {
        height: 42px !important;
        min-height: 42px !important;
        max-height: 42px !important;
        width: auto !important;
        min-width: 112px !important;
        max-width: none !important;
        padding: 0 16px !important;
        background: #ffffff !important;
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        color: #334155 !important;
        font-size: 13px !important;
        font-weight: 700 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 7px !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
        flex: 0 0 auto !important;
        margin: 0 !important;
    }
    .wizard-copy-code-btn:hover,
    button.wizard-copy-code-btn:hover,
    #btn_copiar_codigo_wizard:hover {
        background: #fff0f2 !important;
        background-color: #fff0f2 !important;
        border-color: #9c0014 !important;
        color: #9c0014 !important;
        box-shadow: 0 2px 5px rgba(156, 0, 20, 0.12) !important;
    }
    .wizard-checkbox-clean {
        padding: 0 !important;
        margin: 0 !important;
        width: 100% !important;
        overflow: visible !important;
    }
    .wizard-checkbox-clean label {
        background: #f8fafc !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        padding: 0 14px !important;
        height: 42px !important;
        min-height: 42px !important;
        max-height: 42px !important;
        box-sizing: border-box !important;
        font-size: 13.5px !important;
        font-weight: 600 !important;
        color: #1e293b !important;
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        gap: 10px !important;
        width: 100% !important;
        margin: 0 !important;
    }
    .wizard-checkbox-clean input[type="checkbox"] {
        width: 18px !important;
        height: 18px !important;
        accent-color: #9c0014 !important;
        cursor: pointer !important;
        margin: 0 !important;
        flex-shrink: 0 !important;
    }
    .wizard-row-btn {
        height: 42px !important;
        min-height: 42px !important;
        max-height: 42px !important;
        margin: 0 !important;
        font-size: 13px !important;
        font-weight: 700 !important;
        white-space: nowrap !important;
        padding: 0 14px !important;
    }
    .wizard-inline-btn {
        height: 38px !important;
        min-height: 38px !important;
        max-height: 38px !important;
        font-size: 13px !important;
        font-weight: 700 !important;
        width: 100% !important;
    }
    .wizard-file-upload {
        margin-bottom: 14px !important;
        border-radius: 8px !important;
        position: relative !important;
    }
    .wizard-file-upload .block-label,
    .wizard-file-upload label.float,
    .block-label,
    label.float {
        background: #ffffff !important;
        padding: 2px 8px !important;
        border-radius: 6px !important;
        border: 1px solid #cbd5e1 !important;
        font-weight: 700 !important;
        font-size: 13px !important;
        color: #0f172a !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
        z-index: 2 !important;
    }
    .wizard-file-upload button[aria-label*="upload"] .wrap,
    .wizard-file-upload button.center .wrap {
        margin-top: 26px !important;
        gap: 6px !important;
    }
    .wizard-file-upload .icon-wrap {
        margin-bottom: 4px !important;
        color: #176b87 !important;
    }
    .wizard-file-upload .icon-wrap svg {
        width: 24px !important;
        height: 24px !important;
    }
    .wizard-number-input {
        margin-top: 4px !important;
        margin-bottom: 12px !important;
        width: 100% !important;
    }
    .wizard-number-input input[type="number"] {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 6px !important;
        padding: 8px 12px !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        color: #0f172a !important;
    }
    .wizard-feedback-slot {
        margin-top: 10px !important;
        width: 100% !important;
    }
    .wizard-footer-card {
        margin-top: 24px !important;
        padding-top: 20px !important;
        border-top: 1px solid #f1f5f9 !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        gap: 12px !important;
        width: 100% !important;
    }
    .wizard-submit-row {
        margin-top: 8px !important;
        display: flex !important;
        justify-content: center !important;
        width: 100% !important;
    }
    .wizard-submit-btn {
        min-width: 320px !important;
        height: 48px !important;
        font-size: 15px !important;
        font-weight: 800 !important;
        letter-spacing: 0.01em !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 14px rgba(156, 0, 20, 0.25) !important;
    }
    .pairwise-penalty-table,
    .pairwise-penalty-table * {
        font-family: inherit !important;
    }
    .pairwise-penalty-table {
        width: 100%;
        border-collapse: collapse;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        overflow: hidden;
        background: #ffffff !important;
    }
    .pairwise-penalty-table th, .pairwise-penalty-table td {
        padding: 9px 12px;
        border: 1px solid #f1f5f9;
        text-align: left;
        font-size: 13px;
        color: #0f172a !important;
    }
    .pairwise-penalty-table th {
        background: #f8fafc !important;
        color: #475569 !important;
        font-weight: 700 !important;
        font-size: 12px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
        border-bottom: 2px solid #e2e8f0 !important;
    }

    .agreement-dashboard { width: 100%; margin: 10px 0 24px; color: #0f172a; }
    .assignment-progress { margin: 0 0 22px; padding: 20px; border: 1px solid #e2e8f0; border-top: 4px solid #9c0014; background: #ffffff; }
    .section-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 14px; }
    .section-heading h3 { margin: 2px 0 0; color: #0f172a; font-size: 21px; }
    .section-eyebrow { color: #9c0014; font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
    .version-label { padding: 5px 8px; background: #f1f5f9; color: #475569; font-family: monospace; font-size: 12px; }
    .progress-table { width: 100%; border-collapse: collapse; }
    .progress-table th, .progress-table td { padding: 11px 12px; border-bottom: 1px solid #e2e8f0; text-align: left; background: #ffffff !important; color: #0f172a !important; }
    .progress-table th { background: #f8fafc !important; color: #475569 !important; font-size: 13px; text-transform: uppercase; font-weight: 700; }
    .agreement-kpis { display: grid; grid-template-columns: repeat(3, minmax(160px, 1fr)); gap: 14px; margin: 12px 0 18px; }
    .kpi { border: 1px solid #e2e8f0; border-left: 4px solid #9c0014; padding: 14px 16px; background: #fffafa; border-radius: 6px; }
    .kpi span { display: block; color: #475569; font-size: 14px; text-transform: uppercase; font-weight: 700; }
    .kpi strong { display: block; color: #9c0014; font-size: 28px; margin-top: 4px; font-weight: 800; }
    .dashboard-grid { display: grid; grid-template-columns: minmax(0, 1.12fr) minmax(0, 1.38fr); gap: 20px; align-items: stretch; }
    .analytics-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.5fr); gap: 20px; margin-top: 20px; }
    .disagreement-full-row { width: 100%; margin-top: 20px; }
    .disagreement-full-card { width: 100%; border-top: 4px solid #9c0014 !important; padding: 22px !important; box-sizing: border-box !important; }
    .penalty-leaderboard-card { border-top: 4px solid #176b87 !important; display: flex; flex-direction: column; }
    .daily-annotation-chart { border-top: 4px solid #b56b00 !important; display: flex; flex-direction: column; }
    .card-heading-block { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 2px; }
    .card-heading-block h3 { margin: 2px 0 4px !important; font-size: 19px; color: #0f172a; font-weight: 800; }

    /* Tabela de Anotadores com Maior Penalidade */
    .penalty-table { width: 100%; border-collapse: collapse; margin-top: 4px; border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden; }
    .penalty-table th { font-size: 11px !important; text-transform: uppercase !important; letter-spacing: 0.04em !important; color: #475569 !important; background: #f8fafc !important; padding: 10px 10px !important; font-weight: 700 !important; border-bottom: 2px solid #e2e8f0 !important; white-space: nowrap !important; }
    .penalty-table td { padding: 12px 10px !important; vertical-align: middle !important; border-bottom: 1px solid #f1f5f9 !important; font-size: 13.5px !important; }
    .penalty-table .th-right, .penalty-table .td-penalty-total { text-align: right !important; }
    .penalty-annotator-cell { display: inline-flex; align-items: center; gap: 8px; white-space: nowrap; }
    .penalty-rank-badge { display: inline-flex; align-items: center; justify-content: center; min-width: 24px; height: 22px; padding: 0 6px; border-radius: 6px; background: #f1f5f9 !important; color: #475569 !important; font-size: 11.5px; font-weight: 800; border: 1px solid #cbd5e1; }
    .penalty-table tbody tr:first-child .penalty-rank-badge { background: #fff0f2 !important; color: #9c0014 !important; border-color: #ffd6dc !important; }
    .penalty-user-name { color: #0f172a !important; font-weight: 700; font-size: 14px; }
    .penalty-videos-cell { display: inline-flex; align-items: center; flex-wrap: nowrap; gap: 6px; white-space: nowrap; }
    .penalty-videos-count { color: #1e293b !important; font-size: 13.5px; }
    .penalty-videos-count strong { color: #0f172a !important; font-weight: 800; }
    .penalty-divergent-pill { display: inline-block; padding: 2px 8px; border-radius: 999px; background: #fff8eb !important; color: #9a5b00 !important; border: 1px solid #fde68a !important; font-size: 11px; font-weight: 700; white-space: nowrap; }
    .penalty-avg-badge { display: inline-block; padding: 3px 8px; border-radius: 6px; background: #f8fafc !important; color: #334155 !important; border: 1px solid #e2e8f0 !important; font-size: 12.5px; font-weight: 700; white-space: nowrap; }
    .penalty-avg-badge small { color: #64748b !important; font-weight: 500; font-size: 11px; }
    .penalty-bar-wrap { display: inline-flex; align-items: center; justify-content: flex-end; gap: 10px; width: 100%; white-space: nowrap; }
    .penalty-total-val { font-size: 15px; font-weight: 800; color: #9c0014 !important; min-width: 38px; text-align: right; }
    .penalty-bar-track { width: 78px; min-width: 60px; height: 8px; background: #f1f5f9 !important; border-radius: 999px; overflow: hidden; box-shadow: inset 0 1px 2px rgba(0,0,0,0.06); }
    .penalty-bar-fill { height: 100%; background: linear-gradient(90deg, #d34758 0%, #9c0014 100%) !important; border-radius: 999px; transition: width 0.3s ease; }
    .penalty-summary-footer { margin-top: auto; padding-top: 14px; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
    .penalty-stat-item { padding: 10px 12px; border: 1px solid #e2e8f0 !important; border-radius: 6px; background: #f8fafc !important; display: flex; flex-direction: column; gap: 2px; }
    .penalty-stat-item span { font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: #64748b !important; }
    .penalty-stat-item strong { font-size: 17px; font-weight: 800; color: #0f172a !important; }

    /* Quadro Interativo de Videos com Maior Discordancia (Largura Total) */
    .disagreement-card-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 12px; flex-wrap: wrap; }
    .disagreement-card-header h3 { margin: 2px 0 4px !important; font-size: 20px; font-weight: 800; color: #0f172a; }
    .disagreement-total-badge { padding: 5px 12px; border-radius: 999px; background: #fff0f2 !important; color: #9c0014 !important; border: 1px solid #ffd6dc !important; font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.04em; white-space: nowrap; }
    .disagreement-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 14px; margin: 10px 0 16px; padding: 12px 14px; background: #f8fafc !important; border: 1px solid #e2e8f0 !important; border-radius: 8px; flex-wrap: wrap; }
    .disagreement-search-wrap { flex: 1 1 320px; min-width: 240px; }
    .disagreement-search-input { width: 100% !important; height: 38px !important; padding: 6px 12px !important; font-size: 13.5px !important; border: 1px solid #cbd5e1 !important; border-radius: 6px !important; background: #ffffff !important; color: #0f172a !important; box-sizing: border-box !important; }
    .disagreement-search-input:focus { border-color: #9c0014 !important; box-shadow: 0 0 0 3px rgba(156, 0, 20, 0.1) !important; }
    .disagreement-filter-pills { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    .disagreement-filter-btn { height: 36px !important; padding: 0 13px !important; border-radius: 6px !important; border: 1px solid #cbd5e1 !important; background: #ffffff !important; color: #475569 !important; font-size: 12.5px !important; font-weight: 700 !important; cursor: pointer !important; transition: all 0.15s ease !important; }
    .disagreement-filter-btn:hover { border-color: #94a3b8 !important; color: #0f172a !important; background: #f1f5f9 !important; }
    .disagreement-filter-btn.active { background: #9c0014 !important; color: #ffffff !important; border-color: #9c0014 !important; box-shadow: 0 2px 6px rgba(156, 0, 20, 0.2) !important; }

    .disagreement-table-wrapper { width: 100%; overflow-x: auto; border: 1px solid #e2e8f0; border-radius: 8px; background: #ffffff !important; }
    .disagreement-table { width: 100%; border-collapse: collapse; table-layout: fixed; min-width: 920px; }
    .disagreement-table th { font-size: 12px !important; text-transform: uppercase !important; letter-spacing: 0.04em !important; color: #475569 !important; background: #f8fafc !important; padding: 12px 14px !important; font-weight: 700 !important; border-bottom: 2px solid #e2e8f0 !important; }
    .disagreement-table td { padding: 14px !important; vertical-align: top !important; border-bottom: 1px solid #e2e8f0 !important; font-size: 13.5px !important; }
    .disagreement-table .th-col-video { width: 25%; }
    .disagreement-table .th-col-context { width: 41%; }
    .disagreement-table .th-col-votes { width: 22%; }
    .disagreement-table .th-col-dist { width: 12%; text-align: right !important; }

    .disagreement-target-row { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; flex-wrap: wrap; }
    .disagreement-target-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: #64748b !important; }
    .disagreement-target-pill { display: inline-block; padding: 2px 9px; border-radius: 6px; background: #fff0f2 !important; color: #9c0014 !important; border: 1px solid #ffd6dc !important; font-size: 12px; font-weight: 800; }
    .disagreement-url-link { display: inline-flex; align-items: flex-start; gap: 6px; color: #176b87 !important; font-weight: 700; font-size: 12.5px; line-height: 1.4; text-decoration: none !important; overflow-wrap: anywhere; padding: 7px 10px; background: #f0f9ff !important; border: 1px solid #bae6fd !important; border-radius: 6px; transition: all 0.15s ease; width: 100%; box-sizing: border-box; }
    .disagreement-url-link:hover { background: #e0f2fe !important; border-color: #7dd3fc !important; color: #0e4c61 !important; text-decoration: underline !important; }
    .disagreement-url-link .url-ext-icon { flex: 0 0 13px; margin-top: 2px; color: #176b87 !important; }
    .disagreement-url-actions { display: flex; align-items: center; gap: 8px; margin-top: 8px; flex-wrap: wrap; }
    .disagreement-mini-btn { padding: 5px 10px !important; font-size: 12px !important; font-weight: 700 !important; border-radius: 6px !important; border: 1px solid #cbd5e1 !important; background: #ffffff !important; color: #334155 !important; cursor: pointer !important; transition: all 0.15s ease !important; }
    .disagreement-mini-btn:hover { background: #f1f5f9 !important; border-color: #94a3b8 !important; color: #0f172a !important; }
    .disagreement-mini-btn.preview-toggle-btn { background: #fffafa !important; color: #9c0014 !important; border-color: #fecdd3 !important; }
    .disagreement-mini-btn.preview-toggle-btn:hover, .disagreement-mini-btn.preview-toggle-btn.active { background: #9c0014 !important; color: #ffffff !important; border-color: #9c0014 !important; }
    .disagreement-inline-player { margin-top: 10px; border-radius: 8px; overflow: hidden; border: 1px solid #cbd5e1; background: #000000 !important; width: 100%; max-width: 280px; }
    .disagreement-inline-player iframe { width: 100% !important; height: 460px !important; border: none !important; display: block !important; }

    .disagreement-context-grid { display: flex; flex-direction: column; gap: 8px; }
    .disagreement-context-box { padding: 9px 12px; border: 1px solid #e2e8f0 !important; border-left: 3px solid #176b87 !important; border-radius: 6px; background: #ffffff !important; }
    .disagreement-context-box.transcription { border-left-color: #9c0014 !important; background: #f8fafc !important; }
    .disagreement-context-title { font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; color: #475569 !important; margin-bottom: 3px; }
    .disagreement-context-box.transcription .disagreement-context-title { color: #9c0014 !important; }
    .disagreement-context-text { font-size: 13px; line-height: 1.48; color: #1e293b !important; max-height: 96px; overflow-y: auto; word-break: break-word; scrollbar-width: thin; }
    .disagreement-empty-meta { color: #64748b !important; font-style: italic; font-size: 12.5px; }

    .annotator-vote-list { display: flex; flex-direction: column; gap: 7px; }
    .annotator-vote-item { display: flex; align-items: center; justify-content: space-between; gap: 6px; padding: 6px 10px; border: 1px solid #e2e8f0 !important; border-radius: 6px; background: #f8fafc !important; }
    .annotator-vote-name { display: inline-flex; align-items: center; gap: 5px; font-size: 12.5px; color: #0f172a !important; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .annotator-vote-name strong { color: #0f172a !important; font-weight: 700; }
    .annotator-vote-right { display: inline-flex; align-items: center; gap: 6px; flex: 0 0 auto; }
    .vote-user-icon { flex: 0 0 12px; color: #64748b !important; }
    .annotator-vote-sep { color: #94a3b8 !important; font-weight: 700; font-size: 12px; flex: 0 0 auto; }
    .annotator-stance-pill { display: inline-block; padding: 3px 9px; border-radius: 999px; font-size: 11.5px; font-weight: 800; white-space: nowrap; border: 1px solid transparent; }
    .annotator-stance-pill.stance-favor { background: #ecfdf5 !important; color: #047857 !important; border-color: #a7f3d0 !important; }
    .annotator-stance-pill.stance-contra { background: #fff1f2 !important; color: #be123c !important; border-color: #fecdd3 !important; }
    .annotator-stance-pill.stance-neutro { background: #fffbeb !important; color: #b45309 !important; border-color: #fde68a !important; }
    .annotator-stance-pill.stance-outro { background: #f1f5f9 !important; color: #334155 !important; border-color: #cbd5e1 !important; }
    .annotator-votes-summary { margin-top: 7px; font-size: 11.5px; color: #64748b !important; font-weight: 600; }

    .disagreement-score-cell { display: flex; flex-direction: column; align-items: flex-end; gap: 6px; text-align: right; }
    .disagreement-score-val { font-size: 20px; font-weight: 800; color: #9c0014 !important; line-height: 1.1; }
    .disagreement-severity-badge { display: inline-block; padding: 3px 8px; border-radius: 999px; font-size: 10.5px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.03em; white-space: nowrap; }
    .disagreement-severity-badge.alta { background: #fff1f2 !important; color: #9c0014 !important; border: 1px solid #fecdd3 !important; }
    .disagreement-severity-badge.moderada { background: #fffbeb !important; color: #9a5b00 !important; border: 1px solid #fde68a !important; }
    .disagreement-dist-bar { width: 100%; max-width: 90px; height: 7px; background: #f1f5f9 !important; border-radius: 999px; overflow: hidden; }
    .disagreement-dist-fill { height: 100%; border-radius: 999px; }
    .disagreement-dist-fill.alta { background: #9c0014 !important; }
    .disagreement-dist-fill.moderada { background: #d97706 !important; }
    .bar-row { display: grid; grid-template-columns: 92px minmax(0, 1fr) 28px; align-items: center; gap: 8px; margin: 10px 0; font-size: 13px; }
    .bar-track { height: 12px; background: #f1f5f9; overflow: hidden; border-radius: 4px; }
    .bar-fill { height: 100%; background: #9c0014; }
    .chart-legend { display: flex; flex-wrap: wrap; gap: 12px 18px; margin: 4px 0 16px; font-size: 13px; }
    .chart-legend-item { display: inline-flex; align-items: center; gap: 6px; font-weight: 600; color: #334155; }
    .chart-legend-item i { width: 10px; height: 10px; display: inline-block; border-radius: 2px; }
    .daily-annotation-day { padding: 10px 0 12px; border-top: 1px solid #e2e8f0; }
    .daily-day-label { display: flex; justify-content: space-between; margin-bottom: 7px; color: #0f172a; font-weight: 700; font-size: 13px; }
    .daily-day-label span { color: #64748b; font-weight: 500; }
    .daily-bar-row { display: grid; grid-template-columns: 86px minmax(0, 1fr) 24px; align-items: center; gap: 8px; margin: 5px 0; font-size: 12px; }
    .daily-bar-track { height: 10px; background: #f1f5f9; overflow: hidden; border-radius: 3px; }
    .daily-bar-fill { height: 100%; min-width: 2px; }
    .dashboard-card { border: 1px solid #e2e8f0; padding: 18px; background: #ffffff; min-width: 0; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.03); }
    .dashboard-card h3 { margin: 0 0 12px; color: #0f172a; font-size: 19px; }
    .dashboard-card table { width: 100%; border-collapse: collapse; background: #ffffff !important; }
    .dashboard-card th, .dashboard-card td { padding: 11px 12px; border-bottom: 1px solid #e2e8f0; text-align: left; background: #ffffff !important; color: #0f172a !important; font-size: 15px; }
    .dashboard-card th { color: #475569 !important; font-weight: 700; background: #f8fafc !important; }
    .muted { color: #475569 !important; font-size: 14px !important; }
    .metric-note { margin: 6px 0 12px; color: #475569; font-size: 13px; line-height: 1.45; }
    .duration-alert { margin: 14px 0 20px; padding: 16px; border: 1px solid #fde047; border-left: 5px solid #ca8a04; background: #fefce8; color: #713f12; border-radius: 8px; }
    .duration-alert h3 { margin: 0 0 6px; color: #854d0e; font-size: 19px; }
    .duration-alert p { margin: 0 0 12px; font-size: 15px; }
    .duration-alert table { width: 100%; border-collapse: collapse; background: #fefce8 !important; }
    .duration-alert th, .duration-alert td { padding: 10px 12px; border-bottom: 1px solid #fef08a; text-align: left; background: #fefce8 !important; color: #713f12 !important; font-size: 15px; }
    .duration-alert th { font-weight: 700; }
    .admin-collection-overview { margin: 0 0 20px; padding: 22px; border: 1px solid #d8dde3; border-top: 5px solid #9c0014; background: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04); }
    .collection-overview-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 18px; }
    .collection-overview-header h3 { margin: 3px 0 0; color: #0f172a; font-size: 20px; font-weight: 800; }
    .collection-overview-badge { padding: 5px 11px; border: 1px solid #fecaca; color: #9c0014; background: #fff1f2; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; border-radius: 4px; }
    .collection-kpis-grid { display: grid; grid-template-columns: repeat(4, minmax(140px, 1fr)); gap: 12px; margin-bottom: 22px; }
    .collection-kpi-card { padding: 14px 16px; border: 1px solid #e2e8f0; background: #f8fafc; border-radius: 6px; display: flex; flex-direction: column; gap: 4px; }
    .collection-kpi-card.highlight-principal { border-color: #cbd5e1; background: #ffffff; border-left: 4px solid #176b87; }
    .collection-kpi-card.highlight-reserva { border-color: #cbd5e1; background: #ffffff; border-left: 4px solid #b56b00; }
    .collection-kpi-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: #475569; }
    .collection-kpi-value { font-size: 28px; line-height: 1.1; font-weight: 800; color: #0f172a; }
    .collection-kpi-note { font-size: 12px; color: #64748b; }
    .target-distribution-section { border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden; background: #ffffff; }
    .target-distribution-heading { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; }
    .target-distribution-heading h4 { margin: 0; font-size: 14px; font-weight: 700; color: #0f172a; }
    .target-distribution-count { font-size: 11px; font-weight: 700; color: #475569; background: #e2e8f0; padding: 2px 8px; border-radius: 12px; }
    .target-distribution-table { width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }
    .target-distribution-table th { background: #f1f5f9; color: #334155; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; padding: 10px 14px; border-bottom: 1px solid #cbd5e1; }
    .target-distribution-table td { padding: 10px 14px; border-bottom: 1px solid #f1f5f9; color: #1e293b; }
    .target-distribution-table tfoot td { background: #f8fafc; border-top: 2px solid #cbd5e1; font-weight: 700; color: #0f172a; padding: 12px 14px; }
    .target-distribution-table tr:hover td { background: #fbfcfe; }
    .target-distribution-table .th-num, .target-distribution-table .td-num { text-align: right !important; }
    .target-distribution-table .th-pct, .target-distribution-table .td-pct { text-align: right !important; width: 220px; }
    .target-name-badge-table { display: inline-block; font-weight: 700; color: #0f172a; }
    .target-pct-bar-wrap { display: flex; align-items: center; justify-content: flex-end; gap: 10px; }
    .target-pct-text { font-size: 12px; font-weight: 700; color: #334155; min-width: 44px; text-align: right; }
    .target-pct-track { flex: 1; height: 8px; background: #f1f5f9; border-radius: 4px; overflow: hidden; min-width: 60px; max-width: 120px; }
    .target-pct-fill { height: 100%; background: #176b87; border-radius: 4px; transition: width .3s ease; }
    .admin-command-center { margin: 0 0 22px; padding: 22px; border: 1px solid #d8dde3; border-top: 5px solid #176b87; background: #f8fafc; border-radius: 8px; }
    .admin-section-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 18px; }
    .admin-section-heading h3 { margin: 3px 0 0; color: #0f172a; font-size: 22px; }
    .admin-live-dot { padding: 6px 10px; border: 1px solid #b8d8df; color: #176b87; background: #eef8fa; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; border-radius: 4px; }
    .admin-kpi-grid { display: grid; grid-template-columns: repeat(6, minmax(130px, 1fr)); gap: 10px; }
    .admin-kpi { min-height: 98px; padding: 13px 14px; border: 1px solid #e2e8f0; background: #ffffff; border-radius: 6px; }
    .admin-kpi span, .admin-kpi small { display: block; color: #475569; }
    .admin-kpi span { min-height: 30px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }
    .admin-kpi strong { display: block; margin: 4px 0 2px; color: #176b87; font-size: 26px; line-height: 1; font-weight: 800; }
    .admin-kpi small { font-size: 11px; line-height: 1.3; }
    .admin-insight-grid { display: grid; grid-template-columns: 1fr 1fr 1.25fr; gap: 12px; margin-top: 14px; }
    .admin-chart, .admin-signals { min-width: 0; padding: 16px; border: 1px solid #e2e8f0; background: #ffffff; border-radius: 6px; }
    .admin-chart h4, .admin-signals h4 { margin: 0; color: #0f172a; font-size: 16px; }
    .insight-bar-row { display: grid; grid-template-columns: minmax(92px, .8fr) minmax(0, 1.5fr) 42px; align-items: center; gap: 8px; margin: 13px 0; font-size: 12px; }
    .insight-bar-track { height: 11px; overflow: hidden; background: #f1f5f9; border-radius: 3px; }
    .insight-bar-fill { height: 100%; min-width: 2px; background: #176b87; transition: width .35s ease; }
    .insight-signal { display: grid; gap: 4px; margin-top: 10px; padding: 10px 11px; border-left: 4px solid #176b87; background: #f1f5f9; color: #1e293b; font-size: 12px; line-height: 1.4; border-radius: 0 4px 4px 0; }
    .insight-signal strong { color: #176b87; font-size: 12px; }
    .insight-signal.warning { border-left-color: #b56b00; background: #fff8eb; }
    .insight-signal.warning strong { color: #8a5700; }
    .insight-signal.critical { border-left-color: #9c0014; background: #fff0f2; }
    .insight-signal.critical strong { color: #9c0014; }
    .insight-signal.ok { border-left-color: #4f6f52; background: #f2f8f2; }
    .insight-signal.ok strong { color: #4f6f52; }

    .assignment-table, .assignment-table *,
    .assignment-table .table-wrap, .assignment-table .dataframe,
    .assignment-table [data-testid="dataframe"], .assignment-table [role="grid"], .assignment-table [role="row"], .assignment-table [role="gridcell"] {
        background: #ffffff !important; background-color: #ffffff !important; color: #0f172a !important; color-scheme: light !important;
    }
    .assignment-table [role="columnheader"], .assignment-table th { background: #f8fafc !important; color: #0f172a !important; font-weight: 700 !important; }
    .assignment-table [role="gridcell"], .assignment-table td { border-color: #e2e8f0 !important; color: #0f172a !important; }

    .video-card { width: 100%; min-width: 0; color: #0f172a; overflow: visible; }
    .video-card iframe { display: block; width: 100% !important; max-width: 330px !important; height: 500px !important; overflow: hidden !important; border-radius: 8px !important; border: 1px solid #e2e8f0 !important; }
    .video-meta {
        padding: 10px 14px;
        margin-bottom: 10px;
        border-left: 4px solid #9c0014;
        background: #fffafa;
        font-size: 15px;
        border-radius: 6px;
        border: 1px solid #ffd6dc;
        border-left-width: 4px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .video-meta strong {
        color: #0f172a !important;
        font-weight: 700 !important;
    }
    .target-name-badge {
        color: #9c0014 !important;
        font-weight: 800 !important;
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        display: inline-block !important;
        letter-spacing: 0.2px !important;
        box-shadow: none !important;
    }
    .target-transition {
        position: relative !important;
        overflow: hidden !important;
        animation: target-highlight 15s ease-in-out !important;
        will-change: background, border-color, box-shadow, transform;
    }
    .target-transition::after {
        content: "" !important;
        position: absolute !important;
        top: -50% !important;
        left: -40% !important;
        width: 35% !important;
        height: 200% !important;
        background: linear-gradient(
            90deg,
            rgba(255, 255, 255, 0) 0%,
            rgba(255, 255, 255, 0.5) 25%,
            rgba(255, 255, 255, 1) 50%,
            rgba(255, 255, 255, 0.5) 75%,
            rgba(255, 255, 255, 0) 100%
        ) !important;
        box-shadow: 0 0 25px 10px rgba(255, 255, 255, 0.95), 0 0 40px 15px rgba(225, 29, 72, 0.35) !important;
        transform: skewX(-25deg) !important;
        pointer-events: none !important;
        z-index: 3 !important;
        animation: target-feixe-luz 2.5s ease-in-out 6 !important;
    }
    .target-transition .target-name-badge {
        animation: target-badge-pulse 15s ease-in-out !important;
        position: relative !important;
        z-index: 4 !important;
    }
    @keyframes target-feixe-luz {
        0% {
            left: -40%;
            opacity: 0;
        }
        5% {
            opacity: 1;
        }
        60% {
            left: 115%;
            opacity: 1;
        }
        65%, 100% {
            left: 115%;
            opacity: 0;
        }
    }
    @keyframes target-highlight {
        0%, 100% {
            background: #fffafa !important;
            border-color: #ffd6dc !important;
            border-left-color: #9c0014 !important;
            box-shadow: none !important;
            transform: translateY(0);
        }
        5%, 21%, 37%, 53%, 69%, 85% {
            background: #ffd6dc !important;
            border-color: #9c0014 !important;
            border-left-color: #9c0014 !important;
            box-shadow: 0 0 0 3px rgba(211, 71, 88, 0.28), 0 8px 20px rgba(156, 0, 20, 0.16) !important;
            transform: translateY(-2px);
        }
        13%, 29%, 45%, 61%, 77%, 93% {
            background: #fff8f9 !important;
            border-color: #fca5a5 !important;
            border-left-color: #9c0014 !important;
            box-shadow: 0 0 0 1px rgba(211, 71, 88, 0.18), 0 2px 8px rgba(156, 0, 20, 0.08) !important;
            transform: translateY(0);
        }
    }
    @keyframes pulse-target {
        0%, 100% {
            background: #fffafa !important;
            border-color: #ffd6dc !important;
            border-left-color: #9c0014 !important;
            box-shadow: none !important;
            transform: translateY(0);
        }
        5%, 21%, 37%, 53%, 69%, 85% {
            background: #ffe3e7 !important;
            border-color: #d34758 !important;
            border-left-color: #9c0014 !important;
            box-shadow: 0 0 0 3px rgba(211, 71, 88, 0.28), 0 8px 20px rgba(156, 0, 20, 0.16) !important;
            transform: translateY(-2px);
        }
        13%, 29%, 45%, 61%, 77%, 93% {
            background: #fff8f9 !important;
            border-color: #fca5a5 !important;
            border-left-color: #9c0014 !important;
            box-shadow: 0 0 0 1px rgba(211, 71, 88, 0.18), 0 2px 8px rgba(156, 0, 20, 0.08) !important;
            transform: translateY(0);
        }
    }
    @keyframes target-badge-pulse {
        0%, 100% {
            color: #9c0014 !important;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            transform: scale(1);
            text-shadow: none;
        }
        5%, 21%, 37%, 53%, 69%, 85% {
            color: #7f000e !important;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            transform: scale(1.06);
            text-shadow: 0 0 12px rgba(225, 29, 72, 0.45);
        }
        13%, 29%, 45%, 61%, 77%, 93% {
            color: #9c0014 !important;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            transform: scale(1);
            text-shadow: none;
        }
    }
    .video-content-grid { display: grid; grid-template-columns: 1fr 340px; gap: 16px; align-items: start; }
    .video-player-column, .video-context-column { min-width: 0; }
    .video-player-column { display: flex; justify-content: center; align-items: flex-start; height: 500px; min-height: 500px; overflow: hidden; }
    .video-description { padding: 14px 16px; margin-bottom: 12px; border: 1px solid #e2e8f0; background: #ffffff; line-height: 1.5; overflow-wrap: anywhere; font-size: 14px; border-radius: 8px; max-height: 200px; overflow-y: auto; }
    .video-description strong { display: block; color: #9c0014; margin-bottom: 6px; }
    .video-description.unavailable { color: #64748b; }
    .video-transcription { padding: 14px 16px; margin: 0; border: 1px solid #e2e8f0; background: #f8fafc; line-height: 1.5; overflow-wrap: anywhere; font-size: 14px; border-radius: 8px; max-height: 200px; overflow-y: auto; }
    .video-transcription strong { display: block; color: #9c0014; margin-bottom: 6px; }
    .transcription-note { color: #64748b !important; font-size: 0.85em !important; font-style: italic !important; font-weight: 400 !important; text-transform: none !important; }
    .video-transcription.unavailable { color: #64748b; }

    code, .dark code, pre, .dark pre, [data-testid="markdown"] code {
        background-color: #f1f5f9 !important;
        background: #f1f5f9 !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 4px !important;
        padding: 2px 6px !important;
        font-weight: 700 !important;
        font-family: ui-monospace, SFMono-Regular, monospace !important;
        font-size: 0.9em !important;
    }

    .sensitive-warning-wrapper {
        position: fixed !important; top: 0 !important; left: 0 !important; right: 0 !important; bottom: 0 !important;
        width: 100vw !important; height: 100vh !important; z-index: 99999 !important;
        display: flex !important; align-items: center !important; justify-content: center !important;
        padding: 16px !important; background: rgba(15, 23, 42, 0.5) !important;
        backdrop-filter: blur(8px) !important; -webkit-backdrop-filter: blur(8px) !important; box-sizing: border-box !important;
        margin: 0 !important;
        overflow: hidden !important;
    }
    .sensitive-warning-wrapper .sensitive-warning-card,
    div.sensitive-warning-card,
    .sensitive-warning-card {
        background: #ffffff !important; border: 1px solid #e2e8f0 !important; border-top: 5px solid #9c0014 !important;
        border-radius: 12px !important; box-shadow: 0 20px 48px rgba(0, 0, 0, 0.25) !important;
        max-width: 440px !important; width: 100% !important; height: fit-content !important;
        min-height: 0 !important; max-height: fit-content !important; flex: 0 0 auto !important; flex-grow: 0 !important;
        flex-shrink: 0 !important;
        display: flex !important; flex-direction: column !important; justify-content: center !important;
        padding: 22px 26px !important; margin: auto !important; box-sizing: border-box !important;
        align-self: center !important;
    }
    .sensitive-warning-card > *,
    .sensitive-warning-card .form,
    .sensitive-warning-card .block {
        flex-grow: 0 !important;
        min-height: 0 !important;
        height: auto !important;
    }
    .sensitive-warning-header { text-align: center !important; margin-bottom: 10px !important; }
    .sensitive-warning-badge {
        display: inline-block !important; background: #fff0f2 !important; color: #9c0014 !important;
        font-size: 11px !important; font-weight: 700 !important; text-transform: uppercase !important;
        letter-spacing: 0.06em !important; padding: 4px 12px !important; border-radius: 16px !important;
        border: 1px solid #ffd6dc !important; margin-bottom: 8px !important;
    }
    .sensitive-warning-card h2 { color: #0f172a !important; font-size: 19px !important; font-weight: 800 !important; margin: 0 0 8px 0 !important; text-align: center !important; }
    .sensitive-warning-body { text-align: center !important; margin-bottom: 4px !important; }
    .sensitive-warning-body p {
        color: #334155 !important; font-size: 14px !important; line-height: 1.5 !important;
        margin: 0 0 8px 0 !important;
    }
    .sensitive-warning-actions {
        display: flex !important; flex-direction: row !important; gap: 12px !important;
        margin-top: 16px !important; width: 100% !important;
    }
    .sensitive-warning-actions > * { margin: 0 !important; flex: 1 1 0 !important; min-width: 0 !important; }
    .sensitive-warning-actions button.sensitive-btn-stop,
    .sensitive-warning-actions .sensitive-btn-stop {
        background: #f1f5f9 !important;
        border: 1px solid #cbd5e1 !important;
        color: #475569 !important;
        font-weight: 700 !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
    }
    .sensitive-warning-actions button.sensitive-btn-stop:hover,
    .sensitive-warning-actions .sensitive-btn-stop:hover {
        background: #e2e8f0 !important;
        border-color: #94a3b8 !important;
        color: #1e293b !important;
        transform: translateY(-1px) !important;
    }

    /* Tabelas Modernas do Painel Principal (Sem Menus Suspensos) */
    .hub-table-wrapper {
        width: 100% !important;
        overflow-x: auto !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
        background: #ffffff !important;
        margin: 6px 0 12px 0 !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02) !important;
    }
    .hub-table {
        width: 100% !important;
        border-collapse: collapse !important;
        text-align: left !important;
        font-size: 14px !important;
    }
    .hub-table th {
        background: #f8fafc !important;
        color: #475569 !important;
        font-weight: 700 !important;
        font-size: 12px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        padding: 10px 14px !important;
        border-bottom: 2px solid #e2e8f0 !important;
    }
    .hub-table td {
        padding: 12px 14px !important;
        border-bottom: 1px solid #f1f5f9 !important;
        vertical-align: middle !important;
        color: #0f172a !important;
    }
    .hub-table tr:hover td {
        background: #f8fafc !important;
    }
    .hub-table tr:last-child td {
        border-bottom: none !important;
    }
    .table-bar-track {
        width: 100px !important;
        min-width: 100px !important;
        max-width: 100px !important;
        height: 8px !important;
        background: #e2e8f0 !important;
        border-radius: 999px !important;
        overflow: hidden !important;
        display: inline-block !important;
        vertical-align: middle !important;
        margin-right: 8px !important;
        box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.08) !important;
    }
    .table-bar-fill {
        display: block !important;
        height: 100% !important;
        min-height: 100% !important;
        background: #9c0014 !important;
        border-radius: 999px !important;
        transition: width 0.3s ease !important;
    }
    .hub-table-btn {
        padding: 6px 14px !important;
        font-size: 13px !important;
        font-weight: 700 !important;
        border-radius: 6px !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
        border: none !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 6px !important;
        margin-left: 6px !important;
        white-space: nowrap !important;
    }
    .hub-table-btn.primary {
        background-color: #9c0014 !important;
        color: #ffffff !important;
    }
    .hub-table-btn.primary:hover {
        background-color: #7b0010 !important;
    }
    .hub-table-btn.in-progress {
        background-color: #176b87 !important;
        color: #ffffff !important;
    }
    .hub-table-btn.in-progress:hover {
        background-color: #0e4c61 !important;
    }
    .hub-table-btn.completed {
        background-color: #2e7d32 !important;
        color: #ffffff !important;
    }
    .hub-table-btn.danger {
        background-color: #ffffff !important;
        color: #9c0014 !important;
        border: 1px solid #cbd5e1 !important;
    }
    .hub-table-btn.danger:hover {
        background-color: #fff0f2 !important;
        border-color: #ffd6dc !important;
    }
    .status-pill {
        display: inline-block !important;
        padding: 3px 10px !important;
        border-radius: 12px !important;
        font-size: 12px !important;
        font-weight: 700 !important;
        white-space: nowrap !important;
    }
    .status-pill.pending {
        background: #f1f5f9 !important;
        color: #475569 !important;
        border: 1px solid #cbd5e1 !important;
    }
    .status-pill.in-progress {
        background: #eef8fa !important;
        color: #176b87 !important;
        border: 1px solid #b8d8df !important;
    }
    .status-pill.completed {
        background: #edf7ed !important;
        color: #2e7d32 !important;
        border: 1px solid #c8e6c9 !important;
    }
    .hub-table-empty {
        flex: 1 1 auto !important;
        min-height: 88px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 18px 20px !important;
        text-align: center !important;
        color: #64748b !important;
        font-size: 13.5px !important;
        background: #f8fafc !important;
        border: 1px dashed #cbd5e1 !important;
        border-radius: 8px !important;
        margin: 4px 0 0 0 !important;
        box-sizing: border-box !important;
        line-height: 1.45 !important;
    }
    .hidden-action-trigger {
        display: none !important;
        position: absolute !important;
        width: 0 !important;
        height: 0 !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }

    .target-question {
        font-weight: 700 !important;
        font-size: 15px !important;
        line-height: 1.45 !important;
        color: #0f172a !important;
        margin: 4px 0 8px 0 !important;
        padding: 2px 0 6px 0 !important;
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        border-left: none !important;
        box-shadow: none !important;
        border-radius: 0 !important;
    }
    .target-question, .target-question strong, .target-question b, .target-question * {
        font-weight: 700 !important;
    }
    .target-question .target-name-badge {
        font-size: inherit !important;
        font-weight: inherit !important;
        color: inherit !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
        display: inline !important;
    }

    .wrap-radio form, .wrap-radio > div, .wrap-radio fieldset { display: flex !important; flex-direction: column !important; width: 100% !important; }
    .wrap-radio label {
        display: flex !important; align-items: center !important; gap: 10px !important; width: 100% !important;
        background: #ffffff !important; color: #0f172a !important; border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important; padding: 12px 16px !important; margin-bottom: 10px !important;
        box-sizing: border-box !important; cursor: pointer !important; font-size: 15px !important; font-weight: 400 !important;
        transition: all 0.15s ease !important;
    }
    .wrap-radio label span,
    .wrap-radio label div,
    .wrap-radio span {
        font-weight: 400 !important;
    }
    .wrap-radio label:hover { background: #f8fafc !important; border-color: #9c0014 !important; }
    .wrap-radio label:has(input:checked) {
        background: #fff0f2 !important;
        border-color: #9c0014 !important;
        box-shadow: inset 0 0 0 1px #9c0014 !important;
    }
    .wrap-radio input[type="radio"] { accent-color: #9c0014 !important; width: 18px !important; height: 18px !important; }

    .warning-text { color: #9c0014 !important; font-weight: 700; font-size: 14px; text-align: center; margin-top: 10px; }

    /* Rodape da Aplicacao */
    .app-footer {
        margin-top: 14px !important;
        padding-top: 10px !important;
        border-top: 1px solid #e2e8f0 !important;
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        flex-wrap: wrap !important;
        gap: 10px !important;
        font-size: 13px !important;
        color: #64748b !important;
    }
    .app-footer a {
        color: #9c0014 !important;
        text-decoration: none !important;
        font-weight: 600 !important;
    }
    .app-footer a:hover {
        text-decoration: underline !important;
    }
    .footer-links {
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        flex-wrap: wrap !important;
    }

    /* =========================================================================
       7. AJUSTES FINAIS: AVISOS EFEMEROS, BOTOES COMPACTOS, PAINEL PRINCIPAL, POPUP, CONSOLE E WORKSPACE
       ========================================================================= */
    html, body, .gradio-container { overflow-x: hidden !important; }
    .shell { overflow-x: hidden !important; }

    /* Avisos efemeros: surgem em destaque no canto e somem sozinhos */
    .toast-slot, .toast-slot.block, .toast-slot > div:not(.tokstance-toast) {
        padding: 0 !important; margin: 0 !important; border: none !important; min-height: 0 !important;
        height: 0 !important; background: transparent !important; box-shadow: none !important; overflow: visible !important;
    }
    .tokstance-toast {
        position: fixed !important; top: 20px !important; right: 20px !important; z-index: 100000 !important;
        display: flex !important; align-items: center !important; gap: 14px !important;
        min-width: 320px !important; max-width: min(480px, calc(100vw - 40px)) !important;
        padding: 16px 20px !important; border-radius: 12px !important; background: #ffffff !important;
        border: 1px solid #e2e8f0 !important; border-left: 6px solid #176b87 !important;
        box-shadow: 0 14px 36px rgba(15, 23, 42, 0.22) !important;
        font-size: 15px !important; font-weight: 600 !important; line-height: 1.45 !important; color: #0f172a !important;
    }
    .tokstance-toast.toast-curto { animation: toast-vida 5s ease forwards; }
    .tokstance-toast.toast-longo { animation: toast-vida 12s ease forwards; }
    @keyframes toast-vida {
        0% { opacity: 0; transform: translateX(32px); }
        8%, 85% { opacity: 1; transform: translateX(0); }
        100% { opacity: 0; visibility: hidden; pointer-events: none; transform: translateX(32px); }
    }
    .tokstance-toast .toast-icone {
        flex: 0 0 auto; width: 30px; height: 30px; border-radius: 50%; display: inline-flex;
        align-items: center; justify-content: center; font-weight: 900; font-size: 16px; color: #ffffff; background: #176b87;
    }
    .tokstance-toast.toast-sucesso { border-left-color: #2e7d32 !important; }
    .tokstance-toast.toast-sucesso .toast-icone { background: #2e7d32; }
    .tokstance-toast.toast-erro { border-left-color: #9c0014 !important; background: #fffafa !important; }
    .tokstance-toast.toast-erro .toast-icone { background: #9c0014; }
    .tokstance-toast .toast-texto { flex: 1 1 auto; min-width: 0; }
    .tokstance-toast .toast-acao {
        flex: 0 0 auto; background: #9c0014; color: #ffffff; border: none; border-radius: 8px; padding: 9px 14px;
        font-size: 13px; font-weight: 700; cursor: pointer; white-space: nowrap;
    }
    .tokstance-toast .toast-acao:hover { background: #7a0010; }

    /* Botoes compactos e alinhados em linha */
    .compact-actions {
        display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; gap: 10px !important;
        width: auto !important; flex: 0 0 auto !important; align-items: center !important; justify-content: flex-end !important;
        background: transparent !important; border: none !important; padding: 0 !important; min-width: 0 !important;
    }
    .compact-actions > * { flex: 0 0 auto !important; min-width: 0 !important; width: auto !important; }
    .compact-actions button, button.hub-btn {
        height: 40px !important; min-height: 40px !important; max-height: 40px !important; padding: 0 20px !important;
        font-size: 14px !important; font-weight: 700 !important; white-space: nowrap !important; width: auto !important;
        min-width: fit-content !important;
    }
    button.hub-plus-btn,
    .hub-plus-btn,
    #btn_ir_criar_tarefa,
    #btn_abrir_modal_convite {
        width: 38px !important; min-width: 38px !important; max-width: 38px !important;
        height: 38px !important; min-height: 38px !important; max-height: 38px !important;
        padding: 0 !important; font-size: 0 !important; line-height: 1 !important;
        border-radius: 10px !important; display: inline-flex !important; align-items: center !important; justify-content: center !important;
        flex: 0 0 38px !important; box-sizing: border-box !important; margin: 0 !important;
    }
    button.hub-plus-btn::before,
    .hub-plus-btn::before,
    #btn_ir_criar_tarefa::before,
    #btn_abrir_modal_convite::before {
        content: "" !important;
        display: inline-block !important;
        width: 18px !important;
        height: 18px !important;
        background-color: currentColor !important;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cline x1='12' y1='5' x2='12' y2='19'/%3E%3Cline x1='5' y1='12' x2='19' y2='12'/%3E%3C/svg%3E") no-repeat center / contain !important;
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cline x1='12' y1='5' x2='12' y2='19'/%3E%3Cline x1='5' y1='12' x2='19' y2='12'/%3E%3C/svg%3E") no-repeat center / contain !important;
    }
    .auth-card .compact-actions { justify-content: flex-start !important; width: 100% !important; }
    .auth-card .compact-actions > * { flex: 1 1 0 !important; }

    /* Painel Principal */
    .hub-header-bar { margin-bottom: 14px !important; padding-bottom: 12px !important; align-items: center !important; flex-wrap: nowrap !important; }
    .hub-header-bar > div:first-child { flex: 1 1 auto !important; min-width: 0 !important; }
    .hub-two-col { align-items: stretch !important; gap: 20px !important; }
    .hub-section-box { justify-content: flex-start !important; padding: 18px 20px !important; gap: 8px !important; min-width: 0 !important; height: 100% !important; }
    .hub-box-header h3 { font-size: 18px !important; }
    .hub-box-header p { font-size: 13px !important; }
    .hub-box-header-row { display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; align-items: center !important; justify-content: space-between !important; gap: 12px !important; background: transparent !important; border: none !important; padding: 0 !important; min-height: 48px !important; margin-bottom: 6px !important; }
    .hub-box-header-row > div:first-child { flex: 1 1 auto !important; min-width: 0 !important; }
    .hub-box-header-row > button { flex: 0 0 38px !important; width: 38px !important; height: 38px !important; }
    .hub-section-box .block, .hub-section-box .prose { padding: 0 !important; border: none !important; }
    .hub-section-box > div:not(.hub-box-header-row),
    .hub-section-box .prose,
    .hub-section-box .html-container {
        flex: 1 1 auto !important;
        display: flex !important;
        flex-direction: column !important;
        width: 100% !important;
    }
    .hub-table-wrapper { overflow-x: visible !important; margin: 4px 0 0 0 !important; }
    .hub-table { table-layout: auto !important; }
    .hub-table th { padding: 9px 10px !important; font-size: 11px !important; white-space: nowrap !important; }
    .hub-table td { padding: 10px !important; }
    .hub-table .config-val-badge { white-space: nowrap !important; font-size: 13px !important; padding: 3px 8px !important; }
    .hub-table-btn { padding: 7px 12px !important; font-size: 12.5px !important; margin-left: 4px !important; }

    /* Popup de codigo de convite */
    .modal-overlay {
        position: fixed !important; inset: 0 !important; z-index: 99998 !important; display: flex !important;
        align-items: center !important; justify-content: center !important; padding: 16px !important;
        background: rgba(15, 23, 42, 0.5) !important; backdrop-filter: blur(6px) !important; border: none !important;
        width: 100vw !important; height: 100vh !important; max-width: none !important; min-width: 0 !important;
    }
    .modal-card {
        width: min(440px, 100%) !important; max-width: 440px !important; flex: 0 0 auto !important; height: auto !important;
        background: #ffffff !important; border-radius: 14px !important; border: 1px solid #e2e8f0 !important;
        border-top: 5px solid #9c0014 !important; padding: 22px 24px !important; gap: 12px !important;
        box-shadow: 0 24px 56px rgba(0, 0, 0, 0.3) !important;
    }
    .modal-titulo h3 { margin: 0; font-size: 19px; font-weight: 800; color: #0f172a; }
    .modal-titulo p { margin: 4px 0 0; font-size: 14px; color: #475569; }
    .modal-card .compact-actions,
    .modal-actions {
        display: flex !important;
        flex-direction: row !important;
        justify-content: flex-end !important;
        align-items: center !important;
        gap: 12px !important;
        width: 100% !important;
        margin-top: 6px !important;
    }

    /* Console do administrador */
    .admin-header { margin-bottom: 12px !important; padding-bottom: 12px !important; flex-wrap: nowrap !important; }
    .admin-header > div:first-child, .admin-header > .prose { flex: 1 1 auto !important; min-width: 0 !important; }
    .config-code-row { display: flex !important; align-items: center !important; gap: 8px !important; }
    .copy-code-btn {
        width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
        border-radius: 8px; border: 1px solid #cbd5e1; background: #ffffff; color: #475569; padding: 0;
        transition: all 0.15s ease;
    }
    .copy-code-btn:hover { background: #fff0f2; border-color: #9c0014; color: #9c0014; }

    /* Assistente de criacao e botoes de acao com icones classicos */
    .wizard-icon-btn {
        width: 44px !important; min-width: 44px !important; height: 42px !important; min-height: 42px !important;
        max-height: 42px !important; padding: 0 !important; display: inline-flex !important;
        align-items: center !important; justify-content: center !important; cursor: pointer !important;
    }
    .btn-icon-copiar::before {
        content: "" !important;
        display: inline-block !important;
        width: 18px !important;
        height: 18px !important;
        background-color: currentColor !important;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='14' height='14' x='8' y='8' rx='2' ry='2'/%3E%3Cpath d='M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2'/%3E%3C/svg%3E") no-repeat center / contain !important;
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='14' height='14' x='8' y='8' rx='2' ry='2'/%3E%3Cpath d='M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2'/%3E%3C/svg%3E") no-repeat center / contain !important;
    }
    .btn-icon-refresh::before {
        content: "" !important;
        display: inline-block !important;
        width: 18px !important;
        height: 18px !important;
        background-color: currentColor !important;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8'/%3E%3Cpath d='M21 3v5h-5'/%3E%3Cpath d='M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16'/%3E%3Cpath d='M8 16H3v5'/%3E%3C/svg%3E") no-repeat center / contain !important;
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8'/%3E%3Cpath d='M21 3v5h-5'/%3E%3Cpath d='M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16'/%3E%3Cpath d='M8 16H3v5'/%3E%3C/svg%3E") no-repeat center / contain !important;
    }
    .btn-icon-alerta::before {
        content: "" !important;
        display: inline-block !important;
        width: 16px !important;
        height: 16px !important;
        margin-right: 8px !important;
        vertical-align: -2px !important;
        background-color: currentColor !important;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z'/%3E%3Cline x1='12' y1='9' x2='12' y2='13'/%3E%3Cline x1='12' y1='17' x2='12.01' y2='17'/%3E%3C/svg%3E") no-repeat center / contain !important;
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z'/%3E%3Cline x1='12' y1='9' x2='12' y2='13'/%3E%3Cline x1='12' y1='17' x2='12.01' y2='17'/%3E%3C/svg%3E") no-repeat center / contain !important;
    }
    .btn-icon-logout::before {
        content: "" !important;
        display: inline-block !important;
        width: 15px !important;
        height: 15px !important;
        margin-right: 6px !important;
        vertical-align: -2px !important;
        background-color: currentColor !important;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4'/%3E%3Cpolyline points='16 17 21 12 16 7'/%3E%3Cline x1='21' y1='12' x2='9' y2='12'/%3E%3C/svg%3E") no-repeat center / contain !important;
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4'/%3E%3Cpolyline points='16 17 21 12 16 7'/%3E%3Cline x1='21' y1='12' x2='9' y2='12'/%3E%3C/svg%3E") no-repeat center / contain !important;
    }
    .btn-icon-trash::before {
        content: "" !important;
        display: inline-block !important;
        width: 15px !important;
        height: 15px !important;
        margin-right: 6px !important;
        vertical-align: -2px !important;
        background-color: currentColor !important;
        mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='3 6 5 6 21 6'/%3E%3Cpath d='M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2'/%3E%3C/svg%3E") no-repeat center / contain !important;
        -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='3 6 5 6 21 6'/%3E%3Cpath d='M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2'/%3E%3C/svg%3E") no-repeat center / contain !important;
    }
    .hub-btn-icon {
        display: inline-block !important;
        vertical-align: -2px !important;
        flex-shrink: 0 !important;
        margin-right: 5px !important;
    }
    .btn-svg-icon {
        display: inline-block !important;
        vertical-align: middle !important;
        flex-shrink: 0 !important;
    }
    .wizard-action-row { align-items: flex-end !important; flex-wrap: nowrap !important; background: transparent !important; border: none !important; padding: 0 !important; }
    .wizard-action-row > button { flex: 0 0 auto !important; }
    .wizard-accordion { border: 1px solid #e2e8f0 !important; border-radius: 8px !important; }
    .wizard-submit-btn { min-width: 300px !important; height: 46px !important; }
    .form-wizard-card { padding: 26px 30px !important; }

    /* workspace de rotulacao com rolagem normal da pagina e rodape visivel */
    body:has(.labeler-panel:not(.hide):not(.hidden)),
    html:has(.labeler-panel:not(.hide):not(.hidden)) {
        overflow-y: auto !important;
        overflow-x: hidden !important;
        height: auto !important;
        max-height: none !important;
    }
    body:has(.labeler-panel:not(.hide):not(.hidden)) .gradio-container,
    body:has(.labeler-panel:not(.hide):not(.hidden)) main.contain {
        height: auto !important;
        max-height: none !important;
        overflow: visible !important;
    }
    body:has(.labeler-panel:not(.hide):not(.hidden)) .shell {
        width: 100% !important;
        max-width: 1640px !important;
        height: auto !important;
        max-height: none !important;
        margin: 0 auto !important;
        box-sizing: border-box !important;
        overflow: visible !important;
    }
    body:has(.labeler-panel:not(.hide):not(.hidden)) .brand-header,
    body:has(.labeler-panel:not(.hide):not(.hidden)) .block:has(.brand-header) {
        display: block !important;
    }
    .gradio-container:has(.labeler-panel:not(.hide):not(.hidden)) {
        max-width: 100% !important;
        width: 100% !important;
        height: auto !important;
        max-height: none !important;
        overflow: visible !important;
        box-sizing: border-box !important;
    }
    .labeler-panel {
        --altura-player: clamp(560px, calc(100vh - 210px), 640px);
        display: flex !important;
        flex-direction: column !important;
        height: auto !important;
        max-height: none !important;
        overflow: visible !important;
        box-sizing: border-box !important;
        padding: 0 !important;
        margin: 0 !important;
        width: 100% !important;
        max-width: 100% !important;
    }
    .labeler-workspace-container {
        display: flex !important;
        flex-direction: column !important;
        flex: 1 1 auto !important;
        width: 100% !important;
        max-width: 1560px !important;
        margin: 0 auto !important;
        height: auto !important;
        min-height: 0 !important;
        overflow: visible !important;
    }
    .labeler-header-bar {
        margin-bottom: 8px !important;
        padding-bottom: 2px !important;
        height: 36px !important;
        min-height: 36px !important;
        max-height: 36px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        flex: 0 0 auto !important;
        width: 100% !important;
        max-width: 1560px !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }
    .labeler-exit-btn {
        min-width: 160px !important;
        flex: 0 0 auto !important;
        width: auto !important;
        height: 32px !important;
        white-space: nowrap !important;
        font-size: 13px !important;
        font-weight: 700 !important;
    }
    .labeler-layout {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: flex-start !important;
        justify-content: center !important;
        gap: 32px !important;
        width: 100% !important;
        max-width: 1560px !important;
        margin: 0 auto !important;
        min-height: 0 !important;
    }
    .video-column {
        flex: 0 0 auto !important;
        width: auto !important;
        min-width: 0 !important;
        max-width: none !important;
        height: auto !important;
        min-height: 0 !important;
        display: flex !important;
        flex-direction: row !important;
    }
    .video-column > div,
    .video-column .block,
    .video-column .prose {
        width: auto !important;
        height: auto !important;
        min-height: 0 !important;
        display: flex !important;
        flex-direction: row !important;
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
    }
    .video-card {
        width: auto !important;
        height: auto !important;
        display: flex !important;
        flex-direction: row !important;
        align-items: flex-start !important;
        justify-content: flex-start !important;
        gap: 24px !important;
        padding: 0 !important;
        margin: 0 !important;
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        box-sizing: border-box !important;
        min-height: 0 !important;
    }
    .video-context-column {
        flex: 0 0 440px !important;
        width: 440px !important;
        min-width: 340px !important;
        max-width: 480px !important;
        height: auto !important;
        min-height: var(--altura-player) !important;
        max-height: none !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-start !important;
        background: #f8fafc !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        padding: 16px 18px !important;
        gap: 12px !important;
        overflow: visible !important;
        box-sizing: border-box !important;
    }
    .video-meta {
        background: #fffafa !important;
        border: 1px solid #ffd6dc !important;
        border-left: 4px solid #9c0014 !important;
        border-radius: 6px !important;
        box-shadow: none !important;
        padding: 10px 14px !important;
        margin-bottom: 8px !important;
        font-size: 14.5px !important;
        color: #0f172a !important;
        flex: 0 0 auto !important;
        display: flex !important;
        align-items: center !important;
        gap: 6px !important;
        min-height: auto !important;
        box-sizing: border-box !important;
    }
    .video-meta strong {
        color: #0f172a !important;
        font-weight: 700 !important;
    }
    .video-meta .target-name-badge {
        color: #9c0014 !important;
        font-weight: 800 !important;
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
        display: inline-block !important;
    }
    .video-meta.target-transition {
        position: relative !important;
        overflow: hidden !important;
        animation: target-highlight 15s ease-in-out !important;
        will-change: background, border-color, box-shadow, transform;
    }
    .video-meta.target-transition::after {
        content: "" !important;
        position: absolute !important;
        top: -50% !important;
        left: -40% !important;
        width: 35% !important;
        height: 200% !important;
        background: linear-gradient(
            90deg,
            rgba(255, 255, 255, 0) 0%,
            rgba(255, 255, 255, 0.5) 25%,
            rgba(255, 255, 255, 1) 50%,
            rgba(255, 255, 255, 0.5) 75%,
            rgba(255, 255, 255, 0) 100%
        ) !important;
        box-shadow: 0 0 25px 10px rgba(255, 255, 255, 0.95), 0 0 40px 15px rgba(225, 29, 72, 0.35) !important;
        transform: skewX(-25deg) !important;
        pointer-events: none !important;
        z-index: 3 !important;
        animation: target-feixe-luz 2.5s ease-in-out 6 !important;
    }
    .video-meta.target-transition .target-name-badge {
        animation: target-badge-pulse 15s ease-in-out !important;
        position: relative !important;
        z-index: 4 !important;
    }
    .video-description, .video-transcription {
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
        font-size: 13px !important;
        line-height: 1.5 !important;
        color: #334155 !important;
        overflow: visible !important;
        flex: 0 0 auto !important;
        max-height: none !important;
        min-height: 0 !important;
        box-sizing: border-box !important;
        scrollbar-width: thin !important;
    }
    .video-transcription.unavailable,
    .video-description.unavailable {
        flex: 0 0 auto !important;
        min-height: 36px !important;
        max-height: none !important;
        color: #64748b !important;
    }
    .metadata-title {
        font-size: 13px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        color: #9c0014 !important;
        margin-bottom: 4px !important;
    }
    .metadata-text {
        font-size: 13px !important;
        color: #1e293b !important;
        word-break: break-word !important;
    }
    .video-player-column {
        width: calc(var(--altura-player) * 0.5625) !important;
        height: var(--altura-player) !important;
        min-height: 560px !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
        flex: 0 0 auto !important;
    }
    .video-player-column > div,
    .video-player-column .tiktok-player-wrapper {
        height: 100% !important;
        width: 100% !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }
    .video-player-column iframe {
        height: 100% !important;
        min-height: 560px !important;
        width: 100% !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 12px !important;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12) !important;
        background: #000000 !important;
        box-sizing: border-box !important;
    }
    .labeler-controls-column {
        flex: 1 1 auto !important;
        width: auto !important;
        min-width: 380px !important;
        max-width: 500px !important;
        height: var(--altura-player) !important;
        max-height: var(--altura-player) !important;
        min-height: 560px !important;
        display: flex !important;
        flex-direction: column !important;
        flex-wrap: nowrap !important;
        gap: 6px !important;
        overflow-y: auto !important;
        scrollbar-width: thin !important;
        box-sizing: border-box !important;
    }
    .labeler-controls-column > div,
    .labeler-controls-column > .block {
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        flex: 0 0 auto !important;
    }
    .labeler-header-badge-wrapper {
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        padding: 0 0 10px 0 !important;
        margin: 0 !important;
        border-bottom: 1px solid #e2e8f0 !important;
        flex: 0 0 auto !important;
        box-sizing: border-box !important;
    }
    .labeler-info-badge {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: space-between !important;
        font-size: 12px !important;
        gap: 6px !important;
        color: #64748b !important;
        line-height: 1.3 !important;
    }
    .labeler-info-badge strong {
        color: #0f172a !important;
        font-size: 12.5px !important;
        font-weight: 700 !important;
    }
    .labeler-info-badge .user-pill {
        font-size: 11px !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
    }
    .annotation-controls {
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        padding: 0 !important;
        flex: 1 1 auto !important;
        display: flex !important;
        flex-direction: column !important;
        flex-wrap: nowrap !important;
        gap: 6px !important;
        min-height: 0 !important;
        box-sizing: border-box !important;
        width: 100% !important;
        max-width: 100% !important;
        margin: 0 !important;
    }
    .labeler-warning-stack {
        font-size: 11px !important;
        line-height: 1.4 !important;
        padding: 0 !important;
        margin-bottom: 4px !important;
        gap: 3px !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #64748b !important;
        flex: 0 0 auto !important;
    }
    .annotation-controls .prose {
        margin: 0 !important;
        padding: 0 !important;
        flex: 0 0 auto !important;
    }
    .annotation-controls .target-question {
        padding: 2px 0 6px 0 !important;
        margin-bottom: 2px !important;
        font-size: 14.5px !important;
        line-height: 1.4 !important;
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        border-left: none !important;
        box-shadow: none !important;
        border-radius: 0 !important;
    }
    .annotation-controls .target-question.target-transition {
        position: relative !important;
        overflow: hidden !important;
        padding: 6px 12px !important;
        margin-bottom: 6px !important;
        font-size: 14.5px !important;
        line-height: 1.4 !important;
        background: #fffafa !important;
        border: 1px solid #ffd6dc !important;
        border-left: 4px solid #9c0014 !important;
        border-radius: 6px !important;
        animation: target-highlight 15s ease-in-out !important;
    }
    .annotation-controls .target-question.target-transition::after {
        content: "" !important;
        position: absolute !important;
        top: -50% !important;
        left: -40% !important;
        width: 35% !important;
        height: 200% !important;
        background: linear-gradient(
            90deg,
            rgba(255, 255, 255, 0) 0%,
            rgba(255, 255, 255, 0.5) 25%,
            rgba(255, 255, 255, 1) 50%,
            rgba(255, 255, 255, 0.5) 75%,
            rgba(255, 255, 255, 0) 100%
        ) !important;
        box-shadow: 0 0 25px 10px rgba(255, 255, 255, 0.95), 0 0 40px 15px rgba(225, 29, 72, 0.35) !important;
        transform: skewX(-25deg) !important;
        pointer-events: none !important;
        z-index: 3 !important;
        animation: target-feixe-luz 2.5s ease-in-out 6 !important;
    }
    .hidden-cabecalho {
        display: none !important;
        height: 0 !important;
        width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
    }
    .annotation-controls .target-question .target-name-badge {
        font-size: inherit !important;
        font-weight: inherit !important;
        color: inherit !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
        display: inline !important;
    }
    .annotation-controls .form,
    .annotation-controls > .form,
    .annotation-controls div.form,
    .annotation-controls fieldset.wrap-radio,
    .annotation-controls .wrap-radio,
    .annotation-controls .wrap-radio.block,
    .annotation-controls .wrap-radio .wrap,
    .annotation-controls div[data-testid="block"] {
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
        padding: 0 !important;
    }
    .annotation-controls .wrap-radio {
        margin: 0 0 2px 0 !important;
        padding: 0 !important;
        flex: 0 0 auto !important;
    }
    .annotation-controls .wrap-radio > div,
    .annotation-controls .wrap-radio fieldset {
        gap: 2px !important;
        padding: 0 !important;
        margin: 0 !important;
        border: none !important;
    }
    .annotation-controls .wrap-radio label {
        padding: 4px 8px !important;
        margin-bottom: 2px !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        border-radius: 6px !important;
        min-height: 28px !important;
        gap: 6px !important;
    }
    .annotation-controls .wrap-radio label span,
    .annotation-controls .wrap-radio label div,
    .annotation-controls .wrap-radio span {
        font-weight: 500 !important;
        font-size: 12px !important;
    }
    .annotation-controls .ufmg-btn {
        height: 34px !important;
        min-height: 34px !important;
        font-size: 13px !important;
        font-weight: 700 !important;
        margin: 3px 0 2px 0 !important;
        padding: 0 10px !important;
        flex: 0 0 auto !important;
    }
    .annotation-controls button.btn-icon-alerta {
        background: #ffffff !important;
        color: #475569 !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: none !important;
        font-weight: 600 !important;
    }
    .annotation-controls button.btn-icon-alerta:hover {
        background: #f8fafc !important;
        color: #9c0014 !important;
        border-color: #9c0014 !important;
        transform: none !important;
    }
    .annotation-controls .error-btn {
        height: 26px !important;
        min-height: 26px !important;
        font-size: 11px !important;
        padding: 0 8px !important;
        margin: 0 !important;
        flex: 0 0 auto !important;
    }

    /* botao de visibilidade de senha com icone de olho */
    .container-olho-senha {
        position: relative !important;
        display: flex !important;
        align-items: center !important;
    }
    .container-olho-senha input.tem-olho-senha {
        padding-right: 42px !important;
    }
    .btn-olho-senha {
        position: absolute !important;
        right: 8px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        cursor: pointer !important;
        padding: 4px !important;
        margin: 0 !important;
        min-width: 30px !important;
        width: 30px !important;
        height: 30px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        color: #64748b !important;
        border-radius: 6px !important;
        z-index: 5 !important;
        transition: color 0.15s ease, background-color 0.15s ease !important;
    }
    .btn-olho-senha:hover {
        color: #0f172a !important;
        background-color: #f1f5f9 !important;
    }
    .btn-olho-senha:focus-visible {
        outline: 2px solid #9c0014 !important;
        outline-offset: 1px !important;
    }
    .btn-olho-senha svg {
        pointer-events: none !important;
        display: block !important;
    }

    /* Ocultar footer do Gradio */
    footer, .footer { display: none !important; }

    /* campo de nome completo em maiusculas */
    .campo-nome-maiusculo input,
    .uppercase-input input,
    input.campo-nome-maiusculo {
        text-transform: uppercase !important;
    }
"""


def obter_tema_branco() -> Any:
    """Retorna o tema Gradio limpo com fundo branco absoluto e tipografia original da versao legado."""
    return gr.themes.Base(
        primary_hue="red",
        secondary_hue="slate",
        neutral_hue="slate",
        text_size=gr.themes.sizes.text_md,
        radius_size=gr.themes.sizes.radius_md,
        font=(
            "-apple-system",
            "BlinkMacSystemFont",
            "Segoe UI",
            "Roboto",
            "Helvetica Neue",
            "Arial",
            "sans-serif",
        ),
    ).set(
        body_background_fill=COR_FUNDO,
        body_background_fill_dark=COR_FUNDO,
        background_fill_primary=COR_BRANCO,
        background_fill_primary_dark=COR_BRANCO,
        background_fill_secondary=COR_FUNDO,
        background_fill_secondary_dark=COR_FUNDO,
        block_background_fill=COR_BRANCO,
        block_background_fill_dark=COR_BRANCO,
        block_label_background_fill=COR_BRANCO,
        block_label_background_fill_dark=COR_BRANCO,
        block_label_text_color=COR_TEXTO_TITULO,
        block_label_text_color_dark=COR_TEXTO_TITULO,
        block_border_color=COR_BORDA,
        block_border_color_dark=COR_BORDA,
        body_text_color=COR_TEXTO_CORPO,
        body_text_color_dark=COR_TEXTO_CORPO,
        body_text_color_subdued=COR_TEXTO_MUTED,
        body_text_color_subdued_dark=COR_TEXTO_MUTED,
        border_color_primary=COR_BORDA,
        border_color_primary_dark=COR_BORDA,
        input_background_fill=COR_BRANCO,
        input_background_fill_dark=COR_BRANCO,
        input_border_color=COR_BORDA_INPUT,
        input_border_color_dark=COR_BORDA_INPUT,
        input_border_color_focus=COR_PRIMARIA,
        input_border_color_focus_dark=COR_PRIMARIA,
        button_primary_background_fill=COR_PRIMARIA,
        button_primary_background_fill_dark=COR_PRIMARIA,
        button_primary_background_fill_hover=COR_PRIMARIA_HOVER,
        button_primary_background_fill_hover_dark=COR_PRIMARIA_HOVER,
        button_primary_text_color=COR_BRANCO,
        button_primary_text_color_dark=COR_BRANCO,
        button_secondary_background_fill=COR_BRANCO,
        button_secondary_background_fill_dark=COR_BRANCO,
        button_secondary_border_color=COR_BORDA_INPUT,
        button_secondary_border_color_dark=COR_BORDA_INPUT,
        button_secondary_text_color=COR_TEXTO_CORPO,
        button_secondary_text_color_dark=COR_TEXTO_CORPO,
        table_border_color=COR_BORDA,
        table_border_color_dark=COR_BORDA,
        table_even_background_fill=COR_BRANCO,
        table_even_background_fill_dark=COR_BRANCO,
        table_odd_background_fill=COR_FUNDO,
        table_odd_background_fill_dark=COR_FUNDO,
        table_row_focus="#f1f5f9",
        table_row_focus_dark="#f1f5f9",
        table_text_color=COR_TEXTO_TITULO,
        table_text_color_dark=COR_TEXTO_TITULO,
        checkbox_background_color=COR_BRANCO,
        checkbox_background_color_dark=COR_BRANCO,
        checkbox_background_color_selected=COR_PRIMARIA,
        checkbox_background_color_selected_dark=COR_PRIMARIA,
        checkbox_border_color=COR_BORDA_INPUT,
        checkbox_border_color_dark=COR_BORDA_INPUT,
        checkbox_border_color_selected=COR_PRIMARIA,
        checkbox_border_color_selected_dark=COR_PRIMARIA,
        checkbox_label_text_color=COR_TEXTO_CORPO,
        checkbox_label_text_color_dark=COR_TEXTO_CORPO,
        checkbox_label_text_color_selected=COR_TEXTO_TITULO,
        checkbox_label_text_color_selected_dark=COR_TEXTO_TITULO,
    )
