"""Testes unitários dos renderizadores e componentes HTML do frontend (versao inicial do frontend)."""

from typing import Any, Dict, List
import pandas as pd
import pytest

from tokstance.frontend.components import (
    access_statistics,
    admin_insights_html,
    agreement_summary,
    annotation_daily_chart,
    fast_annotations_html,
    formatar_pergunta_com_target,
    generate_progress_bar,
    render_tiktok,
    render_video_card,
    video_outputs,
)


def test_render_tiktok_iframe_and_escaping() -> None:
    """Verifica extracao do ID do video TikTok, escapamento seguro e atributos do iframe."""
    url_simples = "https://www.tiktok.com/@canal/video/7123456789012345678"
    html_simples = render_tiktok(url_simples)
    assert "https://www.tiktok.com/player/v1/7123456789012345678" in html_simples
    assert 'title="Player do vídeo TikTok"' in html_simples
    assert 'scrolling="no"' in html_simples
    assert "allowfullscreen" in html_simples

    url_com_query = "https://www.tiktok.com/@canal/video/7999999999999999999?is_from_webapp=1&sender_device=pc/"
    html_query = render_tiktok(url_com_query)
    assert "7999999999999999999" in html_query
    assert "is_from_webapp" not in html_query


def test_render_video_card_target_transition_and_metadata() -> None:
    """Verifica renderizacao de metadados, descricao, transcricao e classe target-transition."""
    item = {
        "target": "Reforma Tributária",
        "video_description": "Vídeo explicando os impactos da reforma.",
        "voice_to_text": "O texto da proposta tramita no Senado...",
        "url": "https://www.tiktok.com/@noticias/video/7111222333444555666",
    }
    html_sem_transicao = render_video_card(item, highlight_target=False)
    assert "Reforma Tributária" in html_sem_transicao
    assert "Vídeo explicando os impactos da reforma." in html_sem_transicao
    assert "O texto da proposta tramita no Senado..." in html_sem_transicao
    assert "target-transition" not in html_sem_transicao

    html_com_transicao = render_video_card(item, highlight_target=True)
    assert "target-transition" in html_com_transicao
    assert "video-meta target-transition" in html_com_transicao

    #item sem descricao e sem transcricao
    item_vazio = {"target": "Outro Alvo", "url": "https://www.tiktok.com/@canal/video/7000000"}
    html_vazio = render_video_card(item_vazio, highlight_target=False)
    assert "unavailable" in html_vazio
    assert "Descrição não disponível" in html_vazio


def test_generate_progress_bar_and_video_outputs() -> None:
    """Valida geracao da barra de progresso e fluxo de saidas do video na fila."""
    pb_zero = generate_progress_bar(0, 10)
    assert "0 de 10 (0%)" in pb_zero
    assert "width: 0%" in pb_zero

    pb_metade = generate_progress_bar(5, 10)
    assert "5 de 10 (50%)" in pb_metade
    assert "width: 50%" in pb_metade

    pb_concluido = generate_progress_bar(10, 10)
    assert "10 de 10 (100%)" in pb_concluido
    assert "width: 100%" in pb_concluido

    #video_outputs com fila e mudanca de target
    fila = [
        {"target": "Alvo 1", "url": "https://www.tiktok.com/@c/video/7001"},
        {"target": "Alvo 2", "url": "https://www.tiktok.com/@c/video/7002"},
    ]
    #posicao 0
    pos0, html0, update0, pergunta0, pb0 = video_outputs(fila, 0)
    assert pos0 == 0
    assert "Alvo 1" in html0
    assert "target-name-badge" in html0
    assert "target-transition" not in html0
    assert 'Com relação ao target "Alvo 1"' in pergunta0
    assert "target-name-badge" not in pergunta0
    assert "0 de 2 (0%)" in pb0

    #posicao 1 (mudanca de target de Alvo 1 para Alvo 2)
    pos1, html1, update1, pergunta1, pb1 = video_outputs(fila, 1)
    assert pos1 == 1
    assert "Alvo 2" in html1
    assert "target-name-badge" in html1
    assert "target-transition" in html1
    assert 'Com relação ao target "Alvo 2"' in pergunta1
    assert "target-name-badge" not in pergunta1
    assert "target-transition" in pergunta1

    #posicao 2 (conclusao da fila)
    pos2, html2, update2, pergunta2, pb2 = video_outputs(fila, 2)
    assert pos2 == 2
    assert "Fila Concluída" in html2
    assert "2 de 2 (100%)" in pb2


def test_formatar_pergunta_com_target_embedado() -> None:
    """Valida substituicao do target embedado na pergunta com diferentes formatos."""
    #caso padrao com ao target
    res_padrao = formatar_pergunta_com_target(
        "Qual a posição expressa no vídeo em relação ao target?", "Inteligência Artificial"
    )
    assert 'ao target "Inteligência Artificial"?' in res_padrao
    assert "target-name-badge" not in res_padrao

    #caso com placeholder {target}
    res_placeholder = formatar_pergunta_com_target(
        "O criador apoia {target}?", "Vacina"
    )
    assert 'apoia "Vacina"?' in res_placeholder
    assert "target-name-badge" not in res_placeholder

    #caso nulo ou vazio
    res_vazio = formatar_pergunta_com_target(None, "Clima")
    assert 'Com relação ao target "Clima"' in res_vazio
    assert "target-name-badge" not in res_vazio

    #caso personalizado sem target
    res_custom = formatar_pergunta_com_target("Classifique este post.", "Eleições")
    assert 'Classifique este post. (Target: "Eleições")' in res_custom
    assert "target-name-badge" not in res_custom


def test_admin_insights_html_and_agreement_summary() -> None:
    """Valida KPIs operacionais, sinais de acao, serie diaria e painel de concordancia do Admin."""
    atribuicoes = pd.DataFrame([
        {"assignment_id": "v1:rot1:vid1", "labeler": "rot1", "video_id": "vid1"},
        {"assignment_id": "v1:rot1:vid2", "labeler": "rot1", "video_id": "vid2"},
        {"assignment_id": "v1:rot2:vid1", "labeler": "rot2", "video_id": "vid1"},
    ])
    anotacoes = pd.DataFrame([
        {
            "assignment_id": "v1:rot1:vid1",
            "labeler": "rot1",
            "video_id": "vid1",
            "stance": "A Favor",
            "tempo_analise_segundos": "12.5",
            "timestamp": "2026-10-31 10:00:00",
        },
        {
            "assignment_id": "v1:rot2:vid1",
            "labeler": "rot2",
            "video_id": "vid1",
            "stance": "Contra",
            "tempo_analise_segundos": "15.0",
            "timestamp": "2026-10-31 11:30:00",
        },
    ])
    erros = pd.DataFrame([
        {
            "assignment_id": "v1:rot1:vid2",
            "labeler": "rot1",
            "original_video_id": "vid2",
            "replacement_video_id": "res1",
            "replacement_status": "SUBSTITUIDO_OVERLAP",
        }
    ])
    videos = pd.DataFrame([
        {"id": "vid1", "target": "Alvo A", "video_duration": "20.0"},
        {"id": "vid2", "target": "Alvo A", "video_duration": "25.0"},
    ])
    concordancia = {
        "alfa": 0.812,
        "videos_com_multiplas_anotacoes": 1,
        "anotacoes_consideradas": 2,
        "videos_com_discordancia": [{"video_id": "vid1", "anotacoes": ["A Favor", "Contra"], "discordancia_ordinal": 4.0}],
        "labelers_com_maior_discordancia": [{"labeler": "rot1", "penalidade": 4.0}, {"labeler": "rot2", "penalidade": 4.0}],
    }
    anotacoes_rapidas = [
        {
            "video_id": "vid1",
            "labeler": "rot1",
            "video_duration": 20.0,
            "tempo_analise_segundos": 12.5,
            "diferenca_segundos": 7.5,
        }
    ]

    html_insights = admin_insights_html(
        assignments=atribuicoes,
        results=anotacoes,
        errors=erros,
        videos=videos,
        agreement=concordancia,
        fast_annotations=anotacoes_rapidas,
        total_reservas=5,
    )
    assert "admin-command-center" in html_insights
    assert "Cobertura da rodada" in html_insights
    assert "Erros reportados" in html_insights
    assert "Reservas disponíveis" in html_insights
    assert "rot1" in html_insights

    logs = pd.DataFrame([
        {"timestamp": "2026-10-31 09:00:00", "usuario": "rot1", "acao": "LOGIN_LABELER", "tempo_desde_login_segundos": 360.0},
        {"timestamp": "2026-10-31 09:30:00", "usuario": "rot2", "acao": "LOGIN_LABELER", "tempo_desde_login_segundos": 420.0},
    ])
    html_dashboard = agreement_summary(
        agreement_data=concordancia,
        assignments_df=atribuicoes,
        results_df=anotacoes,
        errors_df=erros,
        videos_df=videos,
        logs_df=logs,
        version_name="rodada_piloto",
        fast_annotations=anotacoes_rapidas,
        total_reservas=5,
    )
    assert "agreement-dashboard" in html_dashboard
    assert "0.812" in html_dashboard
    assert "rodada_piloto" in html_dashboard
    assert "Anotações mais rápidas que o vídeo" in html_dashboard
    assert "Vídeos concluídos por dia e rotulador" in html_dashboard


def test_construir_interface_and_hub_cards() -> None:
    """Verifica geracao de cartoes do hub e instanciacao do app Gradio Blocks."""
    from tokstance.frontend.gradio_ui import (
        construir_interface,
        converter_df_para_distancias,
        gerar_tabela_penalidades_df,
        renderizar_hub_cards_html,
    )
    import gradio as gr

    #teste de cartoes vazios e preenchidos
    h_adm_vazio, h_rot_vazio = renderizar_hub_cards_html([], [])
    assert "Você ainda não criou nenhuma tarefa" in h_adm_vazio
    assert "Você ainda não está inscrito" in h_rot_vazio

    t_adm = [{"tarefa_id": 1, "titulo": "Tarefa Teste", "codigo_convite": "TOK-123", "vagas_ocupadas": 2, "numero_vagas": 3, "progresso_percentual": 66.7}]
    t_rot = [{"tarefa_id": 1, "titulo": "Tarefa Teste", "videos_concluidos": 5, "total_videos_fila": 10}]
    h_adm, h_rot = renderizar_hub_cards_html(t_adm, t_rot)
    assert "TOK-123" in h_adm
    assert "5 de 10 (50%)" in h_rot

    #teste de geracao de matriz de penalidades
    df_pares = gerar_tabela_penalidades_df("Contra\nA Favor\nNeutro")
    assert len(df_pares) == 3
    distancias = converter_df_para_distancias(df_pares)
    assert len(distancias) == 3

    #teste de montagem dos Blocks
    app = construir_interface()
    assert isinstance(app, gr.Blocks)
    assert app.title == "TokStance!"


def test_grafico_diario_e_de_linhas_uma_por_rotulador() -> None:
    dados = [
        {"timestamp": "2026-11-01 10:00:00", "labeler": "ana"},
        {"timestamp": "2026-11-01 11:00:00", "labeler": "ana"},
        {"timestamp": "2026-11-02 09:00:00", "labeler": "ana"},
        {"timestamp": "2026-11-02 09:30:00", "labeler": "bia"},
    ]
    html = annotation_daily_chart(dados)
    assert "<svg" in html and html.count("<polyline") == 2
    assert "daily-bar" not in html
    assert "01/11" in html and "02/11" in html


def test_console_admin_config_antes_do_acervo_sem_download_de_logs_e_com_target() -> None:
    from pathlib import Path
    fonte = Path("src/tokstance/frontend/gradio_ui.py").read_text(encoding="utf-8")
    assert fonte.index("admin_configuracao_view = gr.HTML") < fonte.index("admin_visao_acervo_html = gr.HTML")
    assert "Metadados e Tempos" not in fonte
    assert '"labeler", "video_id", "target"' in fonte


def test_campo_nome_completo_nao_reescreve_valor_pelo_servidor() -> None:
    from pathlib import Path
    fonte = Path("src/tokstance/frontend/gradio_ui.py").read_text(encoding="utf-8")
    assert "cadastro_nome_completo.change(" not in fonte
