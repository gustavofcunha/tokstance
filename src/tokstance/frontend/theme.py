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

    /* Container Principal */
    .shell {
        width: min(100%, 1380px) !important;
        max-width: 1380px !important;
        margin: 8px auto !important;
        background: #ffffff !important;
        padding: 20px 28px !important;
        border-radius: 12px !important;
        font-size: 15px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0, 0, 0, 0.02) !important;
        border: 1px solid #e2e8f0 !important;
        border-top: 6px solid #9c0014 !important;
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
       2. ABAS (TABS) MODERNAS COM ALTO CONTRASTE (REFERO / SPELL.SH)
       ========================================================================= */
    .tab-nav,
    div[role="tablist"],
    .dark .tab-nav,
    .dark div[role="tablist"] {
        display: flex !important;
        border-bottom: 2px solid #e2e8f0 !important;
        margin-bottom: 22px !important;
        gap: 8px !important;
        background: transparent !important;
    }

    .tab-nav button,
    div[role="tablist"] button,
    .dark .tab-nav button,
    .dark div[role="tablist"] button {
        font-size: 14px !important;
        font-weight: 700 !important;
        color: #334155 !important; /* Total contraste para aba inativa: cinza escuro legivel! */
        background: #f1f5f9 !important;
        border: 1px solid #cbd5e1 !important;
        border-bottom: none !important;
        padding: 10px 22px !important;
        border-radius: 8px 8px 0 0 !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
    }

    .tab-nav button:hover,
    div[role="tablist"] button:hover,
    .dark .tab-nav button:hover,
    .dark div[role="tablist"] button:hover {
        color: #9c0014 !important;
        background: #fdf2f4 !important;
    }

    .tab-nav button.selected,
    div[role="tablist"] button[aria-selected="true"],
    div[role="tablist"] button.selected,
    .dark .tab-nav button.selected,
    .dark div[role="tablist"] button[aria-selected="true"],
    .dark div[role="tablist"] button.selected {
        color: #9c0014 !important;
        background: #ffffff !important;
        border: 2px solid #9c0014 !important;
        border-bottom: 2px solid #ffffff !important;
        margin-bottom: -2px !important;
        font-weight: 800 !important;
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
        grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
        gap: 20px;
        margin: 14px 0 24px;
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
    .admin-actions {
        display: flex !important;
        justify-content: flex-end !important;
        gap: 12px !important;
    }

    .labeler-header-bar {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: space-between !important;
        margin-bottom: 16px !important;
        padding-bottom: 12px !important;
        border-bottom: 1px solid #e2e8f0 !important;
        width: 100% !important;
    }
    .labeler-header-bar button,
    .compact-action-btn,
    .labeler-actions button {
        width: auto !important;
        min-width: 150px !important;
        max-width: 240px !important;
        flex: 0 0 auto !important;
        padding: 8px 16px !important;
        margin: 0 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    .workspace-header-title {
        margin: 0 !important;
    }
    .workspace-header-title h3 {
        margin: 0 !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        color: #0f172a !important;
    }

    .labeler-layout {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: flex-start !important;
        gap: 20px !important;
        width: 100% !important;
    }
    .video-column {
        flex: 1.15 1 0 !important;
        min-width: 320px !important;
        max-width: 58% !important;
    }
    .labeler-controls-column {
        flex: 0.85 1 0 !important;
        min-width: 280px !important;
        max-width: 45% !important;
    }
    @media (max-width: 900px) {
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
        gap: 8px !important;
        background: #f8fafc !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
        font-size: 13px !important;
        color: #475569 !important;
        margin-bottom: 16px !important;
    }
    .annotation-controls {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        padding: 20px !important;
    }

    .form-wizard-card {
        border: 1px solid #e2e8f0;
        border-top: 5px solid #9c0014;
        padding: 28px 32px;
        background: #ffffff;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
    }
    .pairwise-penalty-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
        background: #ffffff !important;
    }
    .pairwise-penalty-table th, .pairwise-penalty-table td {
        padding: 10px 14px;
        border: 1px solid #e2e8f0;
        text-align: left;
        font-size: 14px;
        color: #0f172a !important;
    }
    .pairwise-penalty-table th {
        background: #f1f5f9 !important;
        color: #0f172a !important;
        font-weight: 700;
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
    .video-card iframe { display: block; width: 100% !important; max-width: 360px !important; height: 600px !important; overflow: hidden !important; border-radius: 8px !important; border: 1px solid #e2e8f0 !important; }
    .video-meta { padding: 14px 16px; margin-bottom: 14px; border-left: 4px solid #9c0014; background: #fffafa; font-size: 16px; border-radius: 0 6px 6px 0; border: 1px solid #ffd6dc; border-left-width: 4px; }
    .target-transition { animation: target-highlight 12s ease-in-out; will-change: background, border-color, box-shadow, transform; }
    @keyframes target-highlight {
        0%, 100% { background: #fffafa; border-left-color: #9c0014; box-shadow: none; transform: translateY(0); }
        8% { background: #ffd6dc; border-left-color: #d34758; box-shadow: 0 0 0 3px rgba(211, 71, 88, 0.28), 0 8px 20px rgba(156, 0, 20, 0.16); transform: translateY(-3px); }
        28% { background: #fff0f2; border-left-color: #b51f35; box-shadow: 0 0 0 2px rgba(211, 71, 88, 0.22), 0 5px 14px rgba(156, 0, 20, 0.12); transform: translateY(0); }
        55% { background: #ffe1e5; border-left-color: #c12d42; box-shadow: 0 0 0 3px rgba(211, 71, 88, 0.24), 0 6px 16px rgba(156, 0, 20, 0.14); }
        78% { background: #fff1f3; border-left-color: #ae1c32; box-shadow: 0 0 0 2px rgba(211, 71, 88, 0.18), 0 4px 12px rgba(156, 0, 20, 0.1); }
    }
    .video-content-grid { display: grid; grid-template-columns: minmax(180px, 0.9fr) minmax(280px, 1.1fr); gap: 16px; align-items: start; }
    .video-player-column, .video-context-column { min-width: 0; }
    .video-player-column { display: flex; justify-content: center; align-items: flex-start; height: auto; min-height: 500px; overflow: hidden; }
    .video-description { padding: 18px; margin-bottom: 18px; border: 1px solid #e2e8f0; background: #ffffff; line-height: 1.55; overflow-wrap: anywhere; font-size: 15px; border-radius: 8px; }
    .video-description strong { display: block; color: #9c0014; margin-bottom: 6px; }
    .video-description.unavailable { color: #64748b; }
    .video-transcription { padding: 18px; margin: 0 0 14px; border: 1px solid #e2e8f0; background: #f8fafc; line-height: 1.55; overflow-wrap: anywhere; font-size: 15px; border-radius: 8px; }
    .video-transcription strong { display: block; color: #9c0014; margin-bottom: 6px; }
    .transcription-note { color: #64748b; font-size: 0.82em; font-style: italic; font-weight: 400; }
    .video-transcription.unavailable { color: #64748b; }

    .sensitive-warning-wrapper {
        position: absolute !important; top: 0 !important; left: 0 !important; right: 0 !important; bottom: 0 !important;
        width: 100% !important; height: 100% !important; min-height: 100% !important; z-index: 50 !important;
        display: flex !important; align-items: center !important; justify-content: center !important;
        padding: 24px !important; background: rgba(255, 255, 255, 0.88) !important;
        backdrop-filter: blur(18px) !important; -webkit-backdrop-filter: blur(18px) !important; box-sizing: border-box !important;
    }
    .sensitive-warning-card {
        background: #ffffff !important; border: 1px solid #e2e8f0 !important; border-top: 5px solid #9c0014 !important;
        border-radius: 12px !important; box-shadow: 0 16px 40px rgba(0, 0, 0, 0.16) !important;
        max-width: 520px !important; width: 100% !important; height: auto !important;
        padding: 28px 32px !important; margin: auto !important; box-sizing: border-box !important;
    }
    .sensitive-warning-header { text-align: center !important; margin-bottom: 16px !important; }
    .sensitive-warning-badge {
        display: inline-block !important; background: #fff0f2 !important; color: #9c0014 !important;
        font-size: 13px !important; font-weight: 700 !important; text-transform: uppercase !important;
        letter-spacing: 0.06em !important; padding: 6px 14px !important; border-radius: 20px !important;
        border: 1px solid #ffd6dc !important; margin-bottom: 12px !important;
    }
    .sensitive-warning-card h2 { color: #0f172a !important; font-size: 22px !important; font-weight: 800 !important; margin: 0 0 12px 0 !important; text-align: center !important; }
    .sensitive-warning-body { text-align: justify !important; margin-bottom: 8px !important; }
    .sensitive-warning-body p {
        color: #334155 !important; font-size: 15px !important; line-height: 1.6 !important;
        margin: 0 0 12px 0 !important;
    }
    .sensitive-warning-actions {
        display: flex !important; flex-direction: row !important; gap: 14px !important;
        margin-top: 24px !important; width: 100% !important;
    }
    .sensitive-warning-actions > * { margin: 0 !important; flex: 1 1 0 !important; min-width: 0 !important; }

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
        margin-top: 28px !important;
        padding-top: 16px !important;
        border-top: 1px solid #e2e8f0 !important;
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        flex-wrap: wrap !important;
        gap: 12px !important;
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
