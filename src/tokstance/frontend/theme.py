"""Tema visual branco e estilos CSS globais (versao inicial do frontend)."""

from typing import Any
import gradio as gr

COR_PRIMARIA = "#9c0014"
COR_PRIMARIA_HOVER = "#7a0010"
COR_SECUNDARIA = "#176b87"
COR_ALERTA = "#b56b00"
COR_SUCESSO = "#4f6f52"
COR_FUNDO = "#ffffff"
COR_FUNDO_PAINEL = "#f7fafb"
COR_TEXTO = "#232323"
COR_BORDA = "#cccccc"

APP_CSS = """
    /* Exterminio Total de Fundos Escuros/Cinzas (Textboxes, Tables, Wrappers) */
    html, body, .gradio-container, .gr-form, .gr-box, .gr-panel, fieldset, .gap {
        background-color: #ffffff !important; background: #ffffff !important; color: #232323 !important; color-scheme: light !important;
    }

    input, textarea, select, .gr-input, table, th, td, tr, tbody, thead {
        background-color: #ffffff !important; background: #ffffff !important; color: #232323 !important;
    }

    .shell {
        width: calc(100vw - 24px) !important; max-width: none !important; margin: 12px auto !important; background: #ffffff !important;
        padding: 28px 36px !important; border-radius: 8px !important; font-size: 17px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08) !important; border-top: 6px solid #9c0014 !important;
    }

    .gradio-container, .gradio-container .main, .gradio-container .contain { max-width: none !important; width: 100% !important; }
    .agreement-dashboard { width: 100%; margin: 10px 0 24px; color: #232323; }
    .assignment-progress { margin: 0 0 22px; padding: 20px; border: 1px solid #dedede; border-top: 4px solid #9c0014; background: #ffffff; }
    .section-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 14px; }
    .section-heading h3 { margin: 2px 0 0; color: #232323; font-size: 21px; }
    .section-eyebrow { color: #9c0014; font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
    .version-label { padding: 5px 8px; background: #f7f7f7; color: #666; font-family: monospace; font-size: 12px; }
    .progress-table { width: 100%; border-collapse: collapse; }
    .progress-table th, .progress-table td { padding: 11px 12px; border-bottom: 1px solid #ededed; text-align: left; background: #ffffff !important; color: #232323 !important; }
    .progress-table th { background: #f7f7f7 !important; color: #666 !important; font-size: 13px; text-transform: uppercase; }
    .agreement-kpis { display: grid; grid-template-columns: repeat(3, minmax(160px, 1fr)); gap: 14px; margin: 12px 0 18px; }
    .kpi { border: 1px solid #e1e1e1; border-left: 4px solid #9c0014; padding: 14px 16px; background: #fffafa; }
    .kpi span { display: block; color: #666; font-size: 15px; text-transform: uppercase; }
    .kpi strong { display: block; color: #9c0014; font-size: 28px; margin-top: 4px; }
    .dashboard-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.5fr); gap: 20px; }
    .analytics-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.5fr); gap: 20px; margin-top: 20px; }
    .bar-row { display: grid; grid-template-columns: 92px minmax(0, 1fr) 28px; align-items: center; gap: 8px; margin: 10px 0; font-size: 13px; }
    .bar-track { height: 12px; background: #f0e5e7; overflow: hidden; }
    .bar-fill { height: 100%; background: #9c0014; }
    .chart-legend { display: flex; flex-wrap: wrap; gap: 12px 18px; margin: 4px 0 16px; font-size: 13px; }
    .chart-legend-item { display: inline-flex; align-items: center; gap: 6px; }
    .chart-legend-item i { width: 10px; height: 10px; display: inline-block; }
    .daily-annotation-day { padding: 10px 0 12px; border-top: 1px solid #ededed; }
    .daily-day-label { display: flex; justify-content: space-between; margin-bottom: 7px; color: #333; font-weight: 700; font-size: 13px; }
    .daily-day-label span { color: #888; font-weight: 400; }
    .daily-bar-row { display: grid; grid-template-columns: 86px minmax(0, 1fr) 24px; align-items: center; gap: 8px; margin: 5px 0; font-size: 12px; }
    .daily-bar-track { height: 10px; background: #f0f0f0; overflow: hidden; }
    .daily-bar-fill { height: 100%; min-width: 2px; }
    .dashboard-card { border: 1px solid #e1e1e1; padding: 16px; background: #ffffff; min-width: 0; }
    .dashboard-card h3 { margin: 0 0 12px; color: #333; font-size: 19px; }
    .dashboard-card table { width: 100%; border-collapse: collapse; background: #ffffff !important; }
    .dashboard-card th, .dashboard-card td { padding: 11px 12px; border-bottom: 1px solid #ededed; text-align: left; background: #ffffff !important; color: #232323 !important; font-size: 16px; }
    .dashboard-card th { color: #666 !important; font-weight: 700; }
    .muted { color: #888 !important; }
    .metric-note { margin: 6px 0 12px; color: #666; font-size: 13px; line-height: 1.45; }
    .duration-alert { margin: 14px 0 20px; padding: 16px; border: 1px solid #e0a400; border-left: 5px solid #c48700; background: #fff9e6; color: #4a3a00; }
    .duration-alert h3 { margin: 0 0 6px; color: #8a6200; font-size: 20px; }
    .duration-alert p { margin: 0 0 12px; font-size: 16px; }
    .duration-alert table { width: 100%; border-collapse: collapse; background: #fff9e6 !important; }
    .duration-alert th, .duration-alert td { padding: 10px 12px; border-bottom: 1px solid #eadcae; text-align: left; background: #fff9e6 !important; color: #4a3a00 !important; font-size: 16px; }
    .duration-alert th { font-weight: 700; }
    .admin-command-center { margin: 0 0 22px; padding: 22px; border: 1px solid #d8dde3; border-top: 5px solid #176b87; background: #f7fafb; }
    .admin-section-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 18px; }
    .admin-section-heading h3 { margin: 3px 0 0; color: #1f2933; font-size: 23px; }
    .admin-live-dot { padding: 6px 10px; border: 1px solid #b8d8df; color: #176b87; background: #eef8fa; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; }
    .admin-kpi-grid { display: grid; grid-template-columns: repeat(6, minmax(130px, 1fr)); gap: 10px; }
    .admin-kpi { min-height: 98px; padding: 13px 14px; border: 1px solid #dfe5e8; background: #ffffff; }
    .admin-kpi span, .admin-kpi small { display: block; color: #66737c; }
    .admin-kpi span { min-height: 30px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }
    .admin-kpi strong { display: block; margin: 4px 0 2px; color: #176b87; font-size: 27px; line-height: 1; }
    .admin-kpi small { font-size: 11px; line-height: 1.3; }
    .admin-insight-grid { display: grid; grid-template-columns: 1fr 1fr 1.25fr; gap: 12px; margin-top: 14px; }
    .admin-chart, .admin-signals { min-width: 0; padding: 16px; border: 1px solid #dfe5e8; background: #ffffff; }
    .admin-chart h4, .admin-signals h4 { margin: 0; color: #1f2933; font-size: 16px; }
    .insight-bar-row { display: grid; grid-template-columns: minmax(92px, .8fr) minmax(0, 1.5fr) 42px; align-items: center; gap: 8px; margin: 13px 0; font-size: 12px; }
    .insight-bar-track { height: 11px; overflow: hidden; background: #e8eef0; }
    .insight-bar-fill { height: 100%; min-width: 2px; background: #176b87; transition: width .35s ease; }
    .insight-signal { display: grid; gap: 4px; margin-top: 10px; padding: 10px 11px; border-left: 4px solid #176b87; background: #f2f8fa; color: #33434d; font-size: 12px; line-height: 1.4; }
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
        background: #ffffff !important; background-color: #ffffff !important; color: #232323 !important; color-scheme: light !important;
    }
    .assignment-table, .assignment-table [data-testid="dataframe"] { --color-background-fill-primary: #ffffff !important; --color-background-fill-secondary: #f7f7f7 !important; --color-block-background-fill: #ffffff !important; --color-border-primary: #e5e5e5 !important; }
    .assignment-table [role="columnheader"], .assignment-table th { background: #f7f7f7 !important; color: #333333 !important; }
    .assignment-table [role="gridcell"], .assignment-table td { border-color: #e5e5e5 !important; color: #232323 !important; }
    .assignment-table input, .assignment-table textarea { background: #ffffff !important; color: #232323 !important; }
    html, body { overflow-x: hidden !important; }
    .labeler-panel, .labeler-panel .wrap, .labeler-panel .block { overflow-x: visible !important; }
    .labeler-panel { position: static !important; font-size: 19px !important; }
    .video-card { width: 100%; min-width: 0; color: #232323; overflow: visible; }
    .video-card > div:first-child { margin-top: 0; }
    .video-card iframe { display: block; width: min(100%, 600px) !important; max-width: 600px !important; height: 720px !important; overflow: hidden !important; }
    .video-meta { padding: 14px 16px; margin-bottom: 14px; border-left: 4px solid #9c0014; background: #fffafa; font-size: 16px; }
    .target-transition { animation: target-highlight 12s ease-in-out; will-change: background, border-color, box-shadow, transform; }
    @keyframes target-highlight {
        0%, 100% { background: #fffafa; border-left-color: #9c0014; box-shadow: none; transform: translateY(0); }
        8% { background: #ffd6dc; border-left-color: #d34758; box-shadow: 0 0 0 3px rgba(211, 71, 88, 0.28), 0 8px 20px rgba(156, 0, 20, 0.16); transform: translateY(-3px); }
        28% { background: #fff0f2; border-left-color: #b51f35; box-shadow: 0 0 0 2px rgba(211, 71, 88, 0.22), 0 5px 14px rgba(156, 0, 20, 0.12); transform: translateY(0); }
        55% { background: #ffe1e5; border-left-color: #c12d42; box-shadow: 0 0 0 3px rgba(211, 71, 88, 0.24), 0 6px 16px rgba(156, 0, 20, 0.14); }
        78% { background: #fff1f3; border-left-color: #ae1c32; box-shadow: 0 0 0 2px rgba(211, 71, 88, 0.18), 0 4px 12px rgba(156, 0, 20, 0.1); }
    }
    .video-content-grid { display: grid; grid-template-columns: minmax(360px, 0.8fr) minmax(0, 1.2fr); gap: 28px; align-items: start; }
    .video-player-column, .video-context-column { min-width: 0; }
    .video-player-column { display: flex; justify-content: center; align-items: flex-start; height: 720px; overflow: hidden; }
    .video-description { padding: 18px; margin-bottom: 18px; border: 1px solid #e1e1e1; background: #ffffff; line-height: 1.55; overflow-wrap: anywhere; font-size: 16px; }
    .video-description strong { display: block; color: #9c0014; margin-bottom: 6px; }
    .video-description.unavailable { color: #777; }
    .video-transcription { padding: 18px; margin: 0 0 14px; border: 1px solid #e1e1e1; background: #fbfbfb; line-height: 1.55; overflow-wrap: anywhere; font-size: 16px; }
    .video-transcription strong { display: block; color: #9c0014; margin-bottom: 6px; }
    .transcription-note { color: #666; font-size: 0.82em; font-style: italic; font-weight: 400; }
    .video-transcription.unavailable { color: #777; }
    .labeler-layout { align-items: flex-start !important; }
    .video-column, .labeler-controls-column { min-width: 0 !important; }
    .shell { position: relative !important; }
    .brand-header { border-bottom: 1px solid #eaeaea; padding-bottom: 25px; margin-bottom: 30px; text-align: left !important; padding-left: 8px; }
    .brand-header h1 { font-size: 28px !important; font-weight: 700 !important; margin: 0 !important; color: #9c0014 !important; }
    .brand-header p { color: #444444 !important; margin: 10px 0 0 !important; font-size: 16px !important; line-height: 1.5; }

    .labeler-actions { position: absolute !important; top: 24px; right: 36px; width: 440px !important; z-index: 60 !important; }
    .labeler-actions button { margin-top: 0 !important; }
    .admin-actions { position: absolute !important; top: 24px; right: 36px; width: 220px !important; margin: 0 !important; z-index: 10; }
    .admin-actions button { margin-top: 0 !important; }
    .annotation-controls { gap: 0 !important; row-gap: 0 !important; }
    .annotation-controls > .form, .annotation-controls > .block { margin-top: 0 !important; }
    .labeler-warning-stack { font-size: 15px; font-style: italic; font-weight: 400; color: #666; line-height: 1.5; margin: 0 0 8px; padding: 0; }
    .labeler-warning-stack div + div { margin-top: 2px; }
    .target-question { margin: 4px 0 12px; color: #232323; font-size: 18px; line-height: 1.5; font-weight: 400; }
    .target-question strong { font-weight: 700 !important; color: #171717; }

    .labeler-workspace-container { position: relative !important; width: 100% !important; min-height: 800px !important; }
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
        max-width: 520px !important; width: 100% !important; height: auto !important; min-height: 0 !important;
        max-height: fit-content !important; flex: 0 0 auto !important; flex-grow: 0 !important; align-self: center !important;
        padding: 28px 32px !important; margin: auto !important; box-sizing: border-box !important;
    }
    .sensitive-warning-card > .gap,
    .sensitive-warning-card > .form,
    .sensitive-warning-card > div {
        min-height: 0 !important; height: auto !important; flex-grow: 0 !important;
    }
    .sensitive-warning-header { text-align: center !important; margin-bottom: 16px !important; }
    .sensitive-warning-badge {
        display: inline-block !important; background: #fff0f2 !important; color: #9c0014 !important;
        font-size: 13px !important; font-weight: 700 !important; text-transform: uppercase !important;
        letter-spacing: 0.06em !important; padding: 6px 14px !important; border-radius: 20px !important;
        border: 1px solid #ffd6dc !important; margin-bottom: 12px !important;
    }
    .sensitive-warning-card h2 { color: #1a202c !important; font-size: 22px !important; font-weight: 700 !important; margin: 0 0 12px 0 !important; text-align: center !important; }
    .sensitive-warning-body { text-align: justify !important; margin-bottom: 8px !important; }
    .sensitive-warning-body p {
        color: #4a5568 !important; font-size: 15px !important; line-height: 1.6 !important;
        text-align: justify !important; text-justify: inter-word !important; margin: 0 0 12px 0 !important;
    }
    .sensitive-warning-body p:last-child { margin-bottom: 0 !important; }
    .sensitive-warning-actions {
        display: flex !important; flex-direction: row !important; gap: 14px !important;
        margin-top: 24px !important; margin-bottom: 0 !important; padding: 0 !important;
        justify-content: center !important; align-items: stretch !important; width: 100% !important; min-height: 0 !important;
    }
    .sensitive-warning-actions > * { margin: 0 !important; flex: 1 1 0 !important; min-width: 0 !important; }
    .sensitive-warning-actions button,
    .sensitive-warning-actions button.ufmg-btn,
    .sensitive-warning-actions button.error-btn,
    .sensitive-warning-actions .sensitive-btn-continue,
    .sensitive-warning-actions .sensitive-btn-stop {
        margin: 0 !important; margin-top: 0 !important; margin-bottom: 0 !important;
        height: 46px !important; min-height: 46px !important; max-height: 46px !important; line-height: 46px !important;
        padding: 0 16px !important; display: flex !important; align-items: center !important; justify-content: center !important;
        font-size: 15px !important; font-weight: 600 !important; border-radius: 6px !important; box-sizing: border-box !important;
        width: 100% !important;
    }
    .sensitive-btn-continue { background: #9c0014 !important; color: #ffffff !important; border: none !important; cursor: pointer !important; }
    .sensitive-btn-continue:hover { background: #7a0010 !important; }
    .sensitive-btn-stop { background: #ffffff !important; color: #4a5568 !important; border: 1px solid #cbd5e0 !important; cursor: pointer !important; }
    .sensitive-btn-stop:hover { background: #f7fafc !important; color: #9c0014 !important; border-color: #9c0014 !important; }
    .labeler-workspace-container:has(.sensitive-warning-wrapper:not([style*="display: none"]):not(.hide-container):not([hidden])) .labeler-layout,
    .labeler-workspace-container:has(.sensitive-warning-wrapper:not([style*="display: none"]):not(.hide-container):not([hidden])) iframe,
    .labeler-workspace-container:has(.sensitive-warning-wrapper:not([style*="display: none"]):not(.hide-container):not([hidden])) .video-card {
        filter: blur(28px) !important; opacity: 0.15 !important; pointer-events: none !important; user-select: none !important; transition: filter 0.3s ease, opacity 0.3s ease;
    }

    @media (max-width: 850px) {
        .shell { width: calc(100vw - 24px) !important; padding: 22px 16px !important; margin: 12px auto !important; }
        .agreement-kpis, .dashboard-grid, .analytics-grid { grid-template-columns: 1fr; }
        .admin-kpi-grid, .admin-insight-grid { grid-template-columns: 1fr; }
        .admin-section-heading { align-items: flex-start; flex-direction: column; }
        .labeler-layout { flex-direction: column !important; }
        .video-content-grid { grid-template-columns: 1fr; }
        .video-card iframe { width: 100% !important; max-width: 650px !important; }
        .labeler-actions { position: static !important; width: 100% !important; margin-bottom: 16px; }
        .admin-actions { position: static !important; width: 100% !important; margin-bottom: 16px !important; }
    }

    button.ufmg-btn {
        background: #9c0014 !important; border: none !important; color: #ffffff !important;
        font-weight: 600 !important; font-size: 17px !important; padding: 13px 21px !important; width: 100% !important;
    }
    .admin-panel { gap: 10px !important; }
    .admin-panel, .admin-panel label, .admin-panel input, .admin-panel textarea, .admin-panel button { font-size: 15px !important; }
    .admin-panel h2, .admin-panel h3 { font-size: 20px !important; }
    .admin-header { align-items: center !important; justify-content: space-between !important; margin: 0 0 8px !important; min-height: 36px !important; }
    .admin-header h2 { margin: 0 !important; }
    .admin-configuration, .admin-configuration * { color: #33434d !important; }
    .admin-configuration { min-height: 0 !important; padding: 14px 18px; border: 1px solid #d8dde3; border-left: 4px solid #176b87; background: #f7fafb !important; line-height: 1.55; }
    .admin-configuration strong { color: #1f2933 !important; }
    .admin-configuration code { display: inline-block; margin: 2px 5px 2px 2px; padding: 3px 7px; border: 1px solid #c9dce1; border-radius: 3px; background: #eaf5f7 !important; color: #176b87 !important; font-family: inherit; font-weight: 700; }
    .admin-configuration p { margin: 2px 0 !important; }
    .admin-status { margin: 8px 0; padding: 9px 12px; border-left: 4px solid #9c0014; background: #fff5f6; }
    .admin-downloads { margin: 10px 0 16px; padding: 8px; border-top: 1px solid #e5e5e5; border-bottom: 1px solid #e5e5e5; }
    .admin-audit { margin: 16px 0 6px !important; }
    button.ufmg-btn:hover { background: #7a0010 !important; }

    button.error-btn {
        background: #ffffff !important; border: 1px solid #dcdcdc !important; color: #555555 !important;
        font-weight: 500 !important; font-size: 16px !important; padding: 11px !important; margin-top: 10px !important; width: 100% !important;
    }
    button.error-btn:hover { background: #f5f5f5 !important; color: #9c0014 !important; }

    .center-form { max-width: 450px; margin: 0 auto; }
    .empty-video { padding: 60px; text-align: center; color: #888; background: #ffffff; border: 1px dashed #ccc; border-radius: 8px; }

    /* Estilos do Hub Inicial de Tarefas e Criador de Nova Tarefa */
    .hub-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 18px; margin-top: 14px; }
    .hub-card { border: 1px solid #e1e1e1; border-top: 4px solid #176b87; padding: 18px; background: #ffffff; border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
    .hub-card.admin { border-top-color: #9c0014; }
    .hub-card h4 { margin: 0 0 8px; color: #1f2933; font-size: 18px; }
    .hub-card-meta { display: flex; flex-direction: column; gap: 6px; margin: 10px 0 16px; font-size: 14px; color: #555; }
    .hub-card-meta span code { background: #eef8fa; color: #176b87; padding: 2px 6px; border-radius: 3px; font-weight: 700; }
    .hub-badge { display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .hub-badge.admin { background: #fff0f2; color: #9c0014; border: 1px solid #ffd6dc; }
    .hub-badge.rotulador { background: #eef8fa; color: #176b87; border: 1px solid #b8d8df; }
    .form-wizard-card { border: 1px solid #d8dde3; border-top: 5px solid #9c0014; padding: 24px; background: #ffffff; border-radius: 6px; }
    .pairwise-penalty-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    .pairwise-penalty-table th, .pairwise-penalty-table td { padding: 9px 12px; border: 1px solid #e5e5e5; text-align: left; font-size: 14px; }
    .pairwise-penalty-table th { background: #f7fafb; color: #1f2933; font-weight: 700; }
"""


def obter_tema_branco() -> Any:
    """Retorna o tema Gradio limpo com fundo branco absoluto e tipografia uniforme."""
    return gr.themes.Base().set(
        body_background_fill=COR_FUNDO,
        body_background_fill_dark=COR_FUNDO,
        background_fill_primary=COR_FUNDO,
        background_fill_primary_dark=COR_FUNDO,
        background_fill_secondary=COR_FUNDO,
        background_fill_secondary_dark=COR_FUNDO,
        block_background_fill=COR_FUNDO,
        block_background_fill_dark=COR_FUNDO,
        border_color_primary=COR_BORDA,
        border_color_primary_dark=COR_BORDA,
        body_text_color=COR_TEXTO,
        body_text_color_dark=COR_TEXTO,
        block_label_text_color=COR_TEXTO,
        block_label_text_color_dark=COR_TEXTO,
        block_title_text_color=COR_TEXTO,
        block_title_text_color_dark=COR_TEXTO,
        input_background_fill=COR_FUNDO,
        input_background_fill_dark=COR_FUNDO,
        input_background_fill_focus=COR_FUNDO,
        input_background_fill_focus_dark=COR_FUNDO,
        button_secondary_background_fill=COR_FUNDO,
        button_secondary_background_fill_dark=COR_FUNDO,
    )
