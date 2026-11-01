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
    assert "target-transition" not in html0
    assert 'Com relação ao target <strong>"Alvo 1"</strong>' in pergunta0
    assert "0 de 2 (0%)" in pb0

    #posicao 1 (mudanca de target de Alvo 1 para Alvo 2)
    pos1, html1, update1, pergunta1, pb1 = video_outputs(fila, 1)
    assert pos1 == 1
    assert "Alvo 2" in html1
    assert "target-transition" in html1
    assert 'Com relação ao target <strong>"Alvo 2"</strong>' in pergunta1

    #posicao 2 (conclusao da fila)
    pos2, html2, update2, pergunta2, pb2 = video_outputs(fila, 2)
    assert pos2 == 2
    assert "Fila Concluída" in html2
    assert "2 de 2 (100%)" in pb2


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
