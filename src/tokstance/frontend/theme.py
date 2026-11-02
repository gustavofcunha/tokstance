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
    function travarModoClaro() {
        document.documentElement.classList.remove('dark');
        document.body.classList.remove('dark');
        document.documentElement.setAttribute('data-theme', 'light');
    }
    travarModoClaro();
    const observer = new MutationObserver(() => {
        if (document.documentElement.classList.contains('dark') || document.body.classList.contains('dark')) {
            travarModoClaro();
        }
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });
}
"""

APP_CSS = """
    /* =========================================================================
       1. FORCAR TEMA CLARO E ALTO CONTRASTE (NEUTRALIZAR MODO ESCURO)
       ========================================================================= */
    :root, html, body, .dark, html.dark, body.dark {
        color-scheme: light !important;
        background-color: #f8fafc !important;
        background: #f8fafc !important;
        color: #0f172a !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", Helvetica, Arial, sans-serif !important;
    }

    /* Container Principal com Otimizacao Total para Telas Widescreen (16:9, 16:10, 21:9) */
    .shell {
        width: min(98%, 1880px) !important;
        max-width: 1880px !important;
        margin: 4px auto !important;
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

    button.error-btn {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        color: #334155 !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 10px 18px !important;
        border-radius: 8px !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        min-height: 42px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-sizing: border-box !important;
        width: auto !important;
    }
    button.error-btn:hover {
        background: #f8fafc !important;
        border-color: #9c0014 !important;
        color: #9c0014 !important;
    }

    /* =========================================================================
       5. HUB INICIAL DE TAREFAS
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
    /* Hub em duas colunas com tarefas lado a lado e botoes perfeitamente alinhados */
    .hub-two-col {
        display: flex !important;
        flex-direction: row !important;
        gap: 24px !important;
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
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        padding: 20px 22px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03) !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: space-between !important;
    }
    .hub-box-header {
        margin-bottom: 12px !important;
    }
    .hub-box-header h3 {
        margin: 0 !important;
        font-size: 19px !important;
        font-weight: 800 !important;
        color: #0f172a !important;
    }
    .hub-box-header p {
        margin: 4px 0 0 !important;
        font-size: 14px !important;
        color: #475569 !important;
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
        padding: 0 16px !important;
        font-size: 14px !important;
        font-weight: 700 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        white-space: nowrap !important;
        margin: 0 !important;
        border-radius: 8px !important;
        box-sizing: border-box !important;
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

    .labeler-layout {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: flex-start !important;
        gap: 22px !important;
        width: 100% !important;
    }
    .video-column {
        flex: 1.25 1 0 !important;
        min-width: 480px !important;
        max-width: 63% !important;
    }
    .labeler-controls-column {
        flex: 0.85 1 0 !important;
        min-width: 320px !important;
        max-width: 39% !important;
    }
    @media (max-width: 1024px) {
        .labeler-layout {
            flex-direction: column !important;
        }
        .video-column, .labeler-controls-column {
            max-width: 100% !important;
            width: 100% !important;
        }
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
        border: 1px solid #e2e8f0;
        border-top: 5px solid #9c0014;
        padding: 24px;
        background: #f8fafc;
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
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
    .wizard-section-card {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        padding: 20px 22px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02) !important;
        display: flex !important;
        flex-direction: column !important;
        gap: 14px !important;
        box-sizing: border-box !important;
    }
    .wizard-section-header {
        display: flex !important;
        align-items: center !important;
        gap: 10px !important;
        padding-bottom: 12px !important;
        border-bottom: 1px solid #f1f5f9 !important;
    }
    .wizard-badge {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 26px !important;
        height: 26px !important;
        border-radius: 50% !important;
        background: #fff0f2 !important;
        color: #9c0014 !important;
        font-weight: 800 !important;
        font-size: 13px !important;
        border: 1px solid #ffd6dc !important;
        flex-shrink: 0 !important;
    }
    .wizard-section-title {
        margin: 0 !important;
        font-size: 15px !important;
        font-weight: 800 !important;
        color: #0f172a !important;
        letter-spacing: -0.01em !important;
    }
    .wizard-section-subtitle {
        margin: 2px 0 0 0 !important;
        font-size: 12px !important;
        color: #64748b !important;
        font-weight: 500 !important;
    }
    .wizard-info-callout {
        background: #f8fafc !important;
        border: 1px solid #e2e8f0 !important;
        border-left: 4px solid #9c0014 !important;
        border-radius: 6px !important;
        padding: 10px 14px !important;
        font-size: 13px !important;
        color: #334155 !important;
        line-height: 1.4 !important;
    }
    .wizard-info-callout code {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 4px !important;
        padding: 1px 5px !important;
        font-weight: 700 !important;
        color: #0f172a !important;
    }
    .wizard-action-row {
        display: flex !important;
        flex-direction: row !important;
        align-items: flex-end !important;
        gap: 8px !important;
        width: 100% !important;
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
    .wizard-slider-row {
        display: flex !important;
        flex-direction: row !important;
        gap: 16px !important;
        align-items: flex-start !important;
        width: 100% !important;
    }
    .wizard-slider-row > * {
        flex: 1 1 0 !important;
        min-width: 0 !important;
    }
    .wizard-pool-row {
        display: flex !important;
        flex-direction: row !important;
        gap: 16px !important;
        align-items: flex-start !important;
        width: 100% !important;
    }
    .wizard-checkbox {
        margin-top: 4px !important;
    }
    .wizard-checkbox label {
        font-size: 13px !important;
        font-weight: 600 !important;
        color: #334155 !important;
    }
    .wizard-submit-row {
        margin-top: 20px !important;
        display: flex !important;
        justify-content: center !important;
        width: 100% !important;
    }
    .wizard-submit-btn {
        min-width: 320px !important;
        height: 48px !important;
        font-size: 15px !important;
        font-weight: 800 !important;
        letter-spacing: 0.02em !important;
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
    .dashboard-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.5fr); gap: 20px; }
    .analytics-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.5fr); gap: 20px; margin-top: 20px; }
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
    .video-meta { padding: 10px 14px; margin-bottom: 12px; border-left: 4px solid #9c0014; background: #fffafa; font-size: 15px; border-radius: 0 6px 6px 0; border: 1px solid #ffd6dc; border-left-width: 4px; }
    .target-transition { animation: target-highlight 12s ease-in-out; will-change: background, border-color, box-shadow, transform; }
    @keyframes target-highlight {
        0%, 100% { background: #fffafa; border-left-color: #9c0014; box-shadow: none; transform: translateY(0); }
        8% { background: #ffd6dc; border-left-color: #d34758; box-shadow: 0 0 0 3px rgba(211, 71, 88, 0.28), 0 8px 20px rgba(156, 0, 20, 0.16); transform: translateY(-3px); }
        28% { background: #fff0f2; border-left-color: #b51f35; box-shadow: 0 0 0 2px rgba(211, 71, 88, 0.22), 0 5px 14px rgba(156, 0, 20, 0.12); transform: translateY(0); }
        55% { background: #ffe1e5; border-left-color: #c12d42; box-shadow: 0 0 0 3px rgba(211, 71, 88, 0.24), 0 6px 16px rgba(156, 0, 20, 0.14); }
        78% { background: #fff1f3; border-left-color: #ae1c32; box-shadow: 0 0 0 2px rgba(211, 71, 88, 0.18), 0 4px 12px rgba(156, 0, 20, 0.1); }
    }
    .video-content-grid { display: grid; grid-template-columns: 1fr 340px; gap: 16px; align-items: start; }
    .video-player-column, .video-context-column { min-width: 0; }
    .video-player-column { display: flex; justify-content: center; align-items: flex-start; height: 500px; min-height: 500px; overflow: hidden; }
    .video-description { padding: 14px 16px; margin-bottom: 12px; border: 1px solid #e2e8f0; background: #ffffff; line-height: 1.5; overflow-wrap: anywhere; font-size: 14px; border-radius: 8px; max-height: 200px; overflow-y: auto; }
    .video-description strong { display: block; color: #9c0014; margin-bottom: 6px; }
    .video-description.unavailable { color: #64748b; }
    .video-transcription { padding: 14px 16px; margin: 0; border: 1px solid #e2e8f0; background: #f8fafc; line-height: 1.5; overflow-wrap: anywhere; font-size: 14px; border-radius: 8px; max-height: 200px; overflow-y: auto; }
    .video-transcription strong { display: block; color: #9c0014; margin-bottom: 6px; }
    .transcription-note { color: #64748b; font-size: 0.82em; font-style: italic; font-weight: 400; }
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

    /* Tabelas Modernas do Hub (Sem Menus Suspensos) */
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
        width: 100% !important;
        max-width: 110px !important;
        height: 7px !important;
        background: #f1f5f9 !important;
        border-radius: 4px !important;
        overflow: hidden !important;
        display: inline-block !important;
        vertical-align: middle !important;
        margin-right: 6px !important;
    }
    .table-bar-fill {
        height: 100% !important;
        background: #9c0014 !important;
        border-radius: 4px !important;
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
        padding: 24px 18px !important;
        text-align: center !important;
        color: #64748b !important;
        font-size: 14px !important;
        background: #f8fafc !important;
        border: 1px dashed #cbd5e1 !important;
        border-radius: 8px !important;
        margin: 6px 0 12px 0 !important;
    }
    .hidden-action-trigger {
        display: none !important;
        position: absolute !important;
        width: 0 !important;
        height: 0 !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }

    .wrap-radio form, .wrap-radio > div, .wrap-radio fieldset { display: flex !important; flex-direction: column !important; width: 100% !important; }
    .wrap-radio label {
        display: flex !important; align-items: center !important; gap: 10px !important; width: 100% !important;
        background: #ffffff !important; color: #0f172a !important; border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important; padding: 12px 16px !important; margin-bottom: 10px !important;
        box-sizing: border-box !important; cursor: pointer !important; font-size: 15px !important; font-weight: 600 !important;
        transition: all 0.15s ease !important;
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
       7. AJUSTES FINAIS: AVISOS EFEMEROS, BOTOES COMPACTOS, HUB, POPUP, CONSOLE E WORKSPACE
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
        opacity: 0; visibility: hidden; pointer-events: none;
    }
    .tokstance-toast.toast-curto { animation: toast-vida 5s ease forwards; }
    .tokstance-toast.toast-longo { animation: toast-vida 12s ease forwards; }
    @keyframes toast-vida {
        0% { opacity: 0; visibility: visible; pointer-events: auto; transform: translateX(32px); }
        5%, 90% { opacity: 1; visibility: visible; pointer-events: auto; transform: translateX(0); }
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
        height: 40px !important; min-height: 40px !important; max-height: 40px !important; padding: 0 18px !important;
        font-size: 14px !important; font-weight: 700 !important; white-space: nowrap !important; width: auto !important;
    }
    button.hub-plus-btn {
        width: 40px !important; min-width: 40px !important; height: 40px !important; min-height: 40px !important;
        max-height: 40px !important; padding: 0 !important; font-size: 24px !important; line-height: 1 !important;
        border-radius: 10px !important;
    }
    .auth-card .compact-actions { justify-content: flex-start !important; width: 100% !important; }
    .auth-card .compact-actions > * { flex: 1 1 0 !important; }

    /* Hub */
    .hub-header-bar { margin-bottom: 14px !important; padding-bottom: 12px !important; align-items: center !important; flex-wrap: nowrap !important; }
    .hub-header-bar > div:first-child { flex: 1 1 auto !important; min-width: 0 !important; }
    .hub-two-col { align-items: flex-start !important; gap: 18px !important; }
    .hub-section-box { justify-content: flex-start !important; padding: 16px 18px !important; gap: 8px !important; min-width: 0 !important; }
    .hub-box-header h3 { font-size: 18px !important; }
    .hub-box-header p { font-size: 13px !important; }
    .hub-box-header-row { display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; align-items: flex-start !important; justify-content: space-between !important; gap: 10px !important; background: transparent !important; border: none !important; padding: 0 !important; }
    .hub-box-header-row > div:first-child { flex: 1 1 auto !important; min-width: 0 !important; }
    .hub-box-header-row > button { flex: 0 0 auto !important; }
    .hub-section-box .block, .hub-section-box .prose { padding: 0 !important; border: none !important; }
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
    .modal-card .compact-actions { justify-content: flex-end !important; }

    /* Console do administrador */
    .admin-header { margin-bottom: 12px !important; padding-bottom: 12px !important; flex-wrap: nowrap !important; }
    .admin-header > div:first-child, .admin-header > .prose { flex: 1 1 auto !important; min-width: 0 !important; }
    .config-code-row { display: flex !important; align-items: center !important; gap: 8px !important; }
    .copy-code-btn {
        width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
        border-radius: 8px; border: 1px solid #cbd5e1; background: #ffffff; font-size: 15px; padding: 0;
    }
    .copy-code-btn:hover { background: #fff0f2; border-color: #9c0014; }

    /* Assistente de criacao */
    .wizard-icon-btn { width: 44px !important; min-width: 44px !important; height: 42px !important; min-height: 42px !important; padding: 0 !important; font-size: 17px !important; }
    .wizard-action-row { align-items: flex-end !important; flex-wrap: nowrap !important; background: transparent !important; border: none !important; padding: 0 !important; }
    .wizard-action-row > button { flex: 0 0 auto !important; }
    .wizard-accordion { border: 1px solid #e2e8f0 !important; border-radius: 8px !important; }
    .wizard-submit-btn { min-width: 280px !important; height: 44px !important; }
    .form-wizard-card { padding: 16px !important; }

    /* Workspace de rotulacao sem rolagem vertical: o player usa a altura disponivel da janela */
    .labeler-panel { --altura-player: clamp(420px, calc(100vh - 290px), 820px); }
    .labeler-layout { align-items: flex-start !important; gap: 18px !important; }
    .video-column { flex: 1.5 1 0 !important; min-width: 0 !important; max-width: none !important; }
    .labeler-controls-column { flex: 1 1 0 !important; min-width: 320px !important; max-width: none !important; }
    .video-content-grid { grid-template-columns: minmax(200px, 1fr) auto !important; gap: 14px !important; }
    .video-player-column { height: var(--altura-player) !important; min-height: 0 !important; justify-content: center !important; }
    .video-card iframe { height: var(--altura-player) !important; max-width: none !important; width: calc(var(--altura-player) * 0.5625) !important; }
    .video-description, .video-transcription { max-height: calc(var(--altura-player) / 2 - 20px) !important; }
    .video-meta { margin-bottom: 8px !important; padding: 8px 12px !important; }
    .labeler-header-bar { margin-bottom: 8px !important; padding-bottom: 8px !important; }
    .labeler-exit-btn { min-width: 190px !important; flex: 0 0 auto !important; width: auto !important; height: 40px !important; white-space: nowrap !important; }
    .annotation-controls { padding: 12px 16px !important; }
    .labeler-warning-stack { margin-bottom: 8px !important; padding: 8px 12px !important; }
    .wrap-radio label { padding: 9px 14px !important; }
    body:has(.labeler-panel:not(.hide):not(.hidden)) .brand-header,
    body:has(.labeler-panel:not(.hide):not(.hidden)) .app-footer { display: none !important; }

    /* Ocultar footer do Gradio */
    footer, .footer { display: none !important; }
"""


def obter_tema_branco() -> Any:
    """Retorna o tema Gradio limpo com fundo branco absoluto e tipografia uniforme de alto contraste."""
    return gr.themes.Soft(
        primary_hue="red",
        secondary_hue="slate",
        neutral_hue="slate",
        text_size=gr.themes.sizes.text_md,
        radius_size=gr.themes.sizes.radius_md,
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
