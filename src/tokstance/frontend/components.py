"""Componentes visuais e renderizadores HTML (versao inicial do frontend)."""

from html import escape
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import gradio as gr
import pandas as pd

from tokstance.backend.domain.agreement import encontrar_anotacoes_rapidas


def render_tiktok(url: str) -> str:
    """Gera o iframe responsivo do player incorporado oficial do TikTok com proporcao otimizada."""
    video_id = str(url or "").rstrip("/").split("/")[-1].split("?")[0]
    player_url = f"https://www.tiktok.com/player/v1/{escape(video_id)}?music_info=1&description=1&rel=0"
    return f"""
    <div style="display: flex; justify-content: center; width: 100%; margin: 0; padding: 0;">
        <iframe
            style="width: min(100%, calc(var(--altura-player, 500px) * 0.5625)); height: var(--altura-player, 500px); border: none; overflow: hidden; display: block; background: #ffffff; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);"
            scrolling="no"
            src="{player_url}"
            title="Player do vídeo TikTok"
            allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
            allowfullscreen
        ></iframe>
    </div>
    """


def render_video_card(item: Dict[str, Any], highlight_target: bool = False) -> str:
    """Renderiza o cartao com metadados do target, descricao, transcricao e player TikTok."""
    target = str(item.get("target", "") or "").strip()
    description = str(item.get("video_description", "") or "").strip()
    transcription = str(item.get("voice_to_text", "") or "").strip()
    url = str(item.get("url", "") or "").strip()

    description_html = (
        escape(description).replace("\n", "<br>")
        if description
        else "Descrição não disponível em videos.csv."
    )
    transcription_html = (
        escape(transcription).replace("\n", "<br>")
        if transcription
        else "Transcrição indisponível para este vídeo."
    )
    description_class = "video-description" if description else "video-description unavailable"
    transcription_class = "video-transcription" if transcription else "video-transcription unavailable"
    transicao_classe = " target-transition" if highlight_target else ""

    return f"""
    <div class='video-card'>
        <div class='video-meta{transicao_classe}'><strong>Target:</strong> {escape(target)}</div>
        <div class='video-content-grid'>
            <div class='video-context-column'>
                <div class='{description_class}'><strong>Descrição do vídeo</strong><div>{description_html}</div></div>
                <div class='{transcription_class}'><strong>Transcrição do áudio <span class='transcription-note'>(pode conter erros)</span></strong><div>{transcription_html}</div></div>
            </div>
            <div class='video-player-column'>{render_tiktok(url)}</div>
        </div>
    </div>
    """


def generate_progress_bar(position: int, total: int) -> str:
    """Renderiza a barra de progresso visual com contador e percentual."""
    percent = int((position / total) * 100) if total > 0 else 100
    return f"""
    <div style="width: 100%; margin-bottom: 12px;">
        <div style="width: 100%; background-color: #e0e0e0; border-radius: 6px; height: 10px; overflow: hidden; box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);">
            <div style="width: {percent}%; background-color: #9c0014; height: 100%; transition: width 0.4s ease;"></div>
        </div>
        <div style="text-align: right; font-size: 13px; color: #333; font-weight: 600; margin-top: 4px;">
            {position} de {total} ({percent}%)
        </div>
    </div>
    """


def video_outputs(
    queue: List[Dict[str, Any]],
    position: int,
    username_clean: str = "",
    pergunta_template: Optional[str] = None,
) -> Tuple[int, str, Any, str, str]:
    """Prepara os outputs visuais do proximo video da fila do rotulador."""
    total = len(queue)
    if position >= total:
        html_fim = (
            '<div class="empty-video">'
            '<h2 style="color:#9c0014; margin-top:0;">Fila Concluída</h2>'
            '<p>Você rotulou todos os vídeos atribuídos a você nesta rodada. Aguarde novas instruções. Obrigado!</p>'
            '</div>'
        )
        pb = generate_progress_bar(total, total)
        return position, html_fim, gr.update(visible=False), "", pb

    item = queue[position]
    target = str(item.get("target", "") or "").strip()
    if pergunta_template and "{target}" in pergunta_template:
        texto_pergunta = escape(pergunta_template.replace("{target}", target))
    elif pergunta_template:
        texto_pergunta = escape(pergunta_template)
    else:
        texto_pergunta = f'Com relação ao target <strong>"{escape(target)}"</strong>, como você classifica a posição deste vídeo?'

    pergunta_markdown = f'<div class="target-question">{texto_pergunta}</div>'
    pb = generate_progress_bar(position, total)

    previous_target = (
        str(queue[position - 1].get("target", "") or "").strip()
        if position > 0
        else ""
    )
    target_changed = position > 0 and previous_target != target
    video_html = render_video_card(item, target_changed)
    return position, video_html, gr.update(visible=True), pergunta_markdown, pb


def _garantir_dataframe(dados: Union[pd.DataFrame, List[Dict[str, Any]], None]) -> pd.DataFrame:
    """Assegura a conversao segura de listas/nulos para DataFrame."""
    if dados is None:
        return pd.DataFrame()
    if isinstance(dados, pd.DataFrame):
        return dados
    return pd.DataFrame(dados)


def fast_annotations_html(fast_annotations: List[Dict[str, Any]]) -> str:
    """Renderiza a secao de alerta para anotacoes feitas em tempo suspeito."""
    if not fast_annotations:
        return ""
    fast_rows = "".join(
        f"<tr><td>{escape(str(item.get('video_id', '')))}</td>"
        f"<td>{escape(str(item.get('labeler', '')))}</td>"
        f"<td>{float(item.get('video_duration', 0.0)):.1f}s</td>"
        f"<td>{float(item.get('tempo_analise_segundos', 0.0)):.1f}s</td>"
        f"<td>{float(item.get('diferenca_segundos', 0.0)):.1f}s</td></tr>"
        for item in fast_annotations[:20]
    )
    return f"""
    <section class='duration-alert'>
        <h3>⚠️ Anotações mais rápidas que o vídeo</h3>
        <p>Foram sinalizadas análises com mais de 5 segundos abaixo da duração do vídeo.</p>
        <table>
            <thead><tr><th>Vídeo</th><th>Rotulador</th><th>Duração</th><th>Análise</th><th>Diferença</th></tr></thead>
            <tbody>{fast_rows}</tbody>
        </table>
    </section>
    """


def annotation_daily_chart(results: Union[pd.DataFrame, List[Dict[str, Any]], None]) -> str:
    """Gera o grafico visual de barras por dia e por rotulador."""
    df_results = _garantir_dataframe(results)
    if df_results.empty or not {"timestamp", "labeler"}.issubset(df_results.columns):
        return "<p class='muted'>Ainda não há anotações para desenhar a série diária.</p>"

    daily = df_results.copy()
    daily["timestamp"] = pd.to_datetime(daily["timestamp"], errors="coerce")
    daily = daily.dropna(subset=["timestamp"])
    if daily.empty:
        return "<p class='muted'>Ainda não há anotações para desenhar a série diária.</p>"

    daily["dia"] = daily["timestamp"].dt.strftime("%Y-%m-%d")
    counts = daily.groupby(["dia", "labeler"]).size().reset_index(name="quantidade")
    labelers = sorted(counts["labeler"].astype(str).unique())
    colors = ["#9c0014", "#176b87", "#b56b00", "#4f6f52", "#704c8a", "#8b5e3c"]
    color_map = {labeler: colors[idx % len(colors)] for idx, labeler in enumerate(labelers)}
    max_count = max(int(counts["quantidade"].max()), 1)

    legend = "".join(
        f"<span class='chart-legend-item'><i style='background:{color_map[labeler]}'></i>{escape(labeler)}</span>"
        for labeler in labelers
    )
    days = []
    for day, day_rows in counts.groupby("dia", sort=True):
        values = dict(zip(day_rows["labeler"].astype(str), day_rows["quantidade"]))
        bars = "".join(
            f"<div class='daily-bar-row'><span>{escape(labeler)}</span>"
            f"<div class='daily-bar-track'><div class='daily-bar-fill' style='width:{values.get(labeler, 0) / max_count:.0%}; background:{color_map[labeler]}'></div></div>"
            f"<strong>{int(values.get(labeler, 0))}</strong></div>"
            for labeler in labelers
        )
        total_dia = int(day_rows["quantidade"].sum())
        days.append(
            f"<div class='daily-annotation-day'><div class='daily-day-label'>{escape(str(day))}<span>{total_dia} no total</span></div>{bars}</div>"
        )
    return f"<div class='chart-legend'>{legend}</div>{''.join(days)}"


def access_statistics(log_df: Union[pd.DataFrame, List[Dict[str, Any]], None] = None) -> Dict[str, Any]:
    """Calcula estatisticas de acesso e sessoes a partir do historico de logs."""
    log = _garantir_dataframe(log_df)
    colunas_necessarias = {"timestamp", "usuario", "acao", "tempo_desde_login_segundos"}
    if log.empty or not colunas_necessarias.issubset(log.columns):
        return {
            "session_rows": "<p class='muted'>Ainda não há dados de acesso.</p>",
            "daily_rows": "<p class='muted'>Ainda não há dados de acesso.</p>",
            "avg_minutes": 0.0,
        }

    log = log.copy()
    log["timestamp"] = pd.to_datetime(log["timestamp"], errors="coerce")
    log["tempo_desde_login_segundos"] = pd.to_numeric(log["tempo_desde_login_segundos"], errors="coerce").fillna(0.0)
    log = log.dropna(subset=["timestamp"])
    if log.empty:
        return {
            "session_rows": "<p class='muted'>Ainda não há dados de acesso.</p>",
            "daily_rows": "<p class='muted'>Ainda não há dados de acesso.</p>",
            "avg_minutes": 0.0,
        }

    login_events = log[log["acao"].isin(["LOGIN_LABELER", "LOGIN_ADMIN", "login"])].copy()
    if login_events.empty:
        login_events = log.copy()

    daily = login_events.assign(dia=login_events["timestamp"].dt.strftime("%Y-%m-%d")).groupby("dia").size().to_dict()
    daily_max = max(daily.values(), default=1)
    daily_rows = "".join(
        f"<div class='bar-row'><span>{escape(day)}</span><div class='bar-track'><div class='bar-fill' style='width:{count / daily_max:.0%}'></div></div><strong>{count}</strong></div>"
        for day, count in sorted(daily.items())
    ) or "<p class='muted'>Nenhum login registrado.</p>"

    sessions = []
    for index, login in login_events.iterrows():
        next_login = login_events[login_events.index > index]
        end = next_login.iloc[0]["timestamp"] if not next_login.empty else None
        events = log[(log.index >= index) & (log["usuario"] == login["usuario"])]
        events = events[events["timestamp"] >= login["timestamp"]]
        if end is not None:
            events = events[events["timestamp"] < end]
        duracao = float(events["tempo_desde_login_segundos"].max()) if not events.empty else 0.0
        sessions.append({"usuario": login["usuario"], "timestamp": login["timestamp"], "duracao": duracao})

    session_frame = pd.DataFrame(sessions)
    avg_minutes = float(session_frame["duracao"].mean() / 60.0) if not session_frame.empty else 0.0
    user_rows = "".join(
        f"<tr><td>{escape(str(user))}</td><td>{len(rows)}</td><td>{rows['duracao'].mean() / 60.0:.1f} min</td><td>{rows['timestamp'].dt.strftime('%Y-%m-%d').nunique()}</td></tr>"
        for user, rows in session_frame.groupby("usuario")
    )
    session_rows = (
        f"<table class='progress-table'><thead><tr><th>Usuário</th><th>Logins</th><th>Média logado</th><th>Dias ativos</th></tr></thead><tbody>{user_rows}</tbody></table>"
        if user_rows
        else "<p class='muted'>Ainda não há sessões registradas.</p>"
    )
    return {"session_rows": session_rows, "daily_rows": daily_rows, "avg_minutes": avg_minutes}


def admin_insights_html(
    assignments: Union[pd.DataFrame, List[Dict[str, Any]], None],
    results: Union[pd.DataFrame, List[Dict[str, Any]], None],
    errors: Union[pd.DataFrame, List[Dict[str, Any]], None],
    videos: Union[pd.DataFrame, List[Dict[str, Any]], None],
    agreement: Dict[str, Any],
    fast_annotations: Optional[List[Dict[str, Any]]] = None,
    opcoes_tarefa: Optional[List[str]] = None,
    total_reservas: Optional[int] = None,
) -> str:
    """Gera o painel de comando do administrador com metricas, graficos e sinais de acao."""
    df_assignments = _garantir_dataframe(assignments)
    df_results = _garantir_dataframe(results)
    df_errors = _garantir_dataframe(errors)
    df_videos = _garantir_dataframe(videos)
    if fast_annotations is None:
        fast_annotations = []

    completed_ids = set(df_results.get("assignment_id", pd.Series(dtype=str)).astype(str).str.strip())
    completed_ids.update(df_errors.get("assignment_id", pd.Series(dtype=str)).astype(str).str.strip())
    assigned = len(df_assignments)
    completed = int(df_assignments["assignment_id"].astype(str).isin(completed_ids).sum()) if assigned and "assignment_id" in df_assignments.columns else len(completed_ids)
    pending = max(0, assigned - completed)
    completion_percent = (completed / assigned) if assigned > 0 else 0.0

    used_reserve_ids = set(df_errors.get("replacement_video_id", pd.Series(dtype=str)).astype(str).str.strip()) - {""}
    if total_reservas is not None:
        pool_reserva_count = total_reservas
    else:
        pool_reserva_count = len(df_videos)
    remaining_reserves = max(pool_reserva_count - len(used_reserve_ids), 0)

    analysis_times = pd.to_numeric(df_results.get("tempo_analise_segundos", pd.Series(dtype=str)), errors="coerce").dropna()
    median_analysis = float(analysis_times.median()) if not analysis_times.empty else None
    error_count = len(df_errors)
    replacement_count = len(used_reserve_ids)
    critical_overlap_count = int(df_errors.get("replacement_status", pd.Series(dtype=str)).astype(str).str.startswith("CRITICO_").sum())

    kpis = [
        ("Cobertura da rodada", f"{completion_percent:.0%}", f"{completed} concluídos de {assigned}"),
        ("Pendências", str(pending), "atribuições ainda abertas"),
        ("Erros reportados", str(error_count), f"{replacement_count} substituídos por reserva"),
        ("Reservas disponíveis", str(remaining_reserves), f"{pool_reserva_count} no pool total"),
        ("Tempo mediano", f"{median_analysis:.1f}s" if median_analysis is not None else "n/d", "por anotação registrada"),
        ("Discordâncias", str(len(agreement.get("videos_com_discordancia", []))), "vídeos com posições diferentes"),
    ]
    kpi_html = "".join(
        f"<div class='admin-kpi'><span>{escape(label)}</span><strong>{escape(value)}</strong><small>{escape(note)}</small></div>"
        for label, value, note in kpis
    )

    labeler_rows = []
    if not df_assignments.empty and "labeler" in df_assignments.columns:
        for labeler, labeler_assignments in df_assignments.groupby("labeler", sort=False):
            labeler_assigned = len(labeler_assignments)
            labeler_completed = int(labeler_assignments["assignment_id"].astype(str).isin(completed_ids).sum()) if "assignment_id" in labeler_assignments.columns else 0
            labeler_rows.append((str(labeler), labeler_completed / labeler_assigned if labeler_assigned else 0, labeler_completed, labeler_assigned))
    labeler_rows.sort(key=lambda item: (item[1], item[0]))
    labeler_chart = "".join(
        f"<div class='insight-bar-row'><span>{escape(labeler)}</span><div class='insight-bar-track'><div class='insight-bar-fill' style='width:{percent:.0%}'></div></div><strong>{done}/{total}</strong></div>"
        for labeler, percent, done, total in labeler_rows
    ) or "<p class='muted'>Ainda não há atribuições para comparar.</p>"

    opcoes = opcoes_tarefa or ["Contra", "A Favor", "Neutro", "Vídeo não relacionado ao target"]
    stance_series = df_results.get("stance", pd.Series(dtype=str)).astype(str) if not df_results.empty and "stance" in df_results.columns else pd.Series(dtype=str)
    stance_counts = stance_series.value_counts().to_dict() if not stance_series.empty else {}
    stance_max = max(stance_counts.values()) if stance_counts else 1
    palette = ["#9c0014", "#176b87", "#b56b00", "#626b73", "#4f6f52", "#704c8a"]
    stance_colors = {opc: palette[idx % len(palette)] for idx, opc in enumerate(opcoes)}

    stance_chart = "".join(
        f"<div class='insight-bar-row'><span>{escape(label)}</span><div class='insight-bar-track'><div class='insight-bar-fill' style='width:{stance_counts.get(label, 0) / stance_max:.0%}; background:{stance_colors.get(label, '#626b73')}'></div></div><strong>{stance_counts.get(label, 0)}</strong></div>"
        for label in opcoes
    )

    signals = []
    if critical_overlap_count:
        signals.append(("Alerta crítico de overlap", f"{critical_overlap_count} atribuição(ões) não puderam preservar o overlap porque já havia anotação no vídeo original. Revise a rodada antes de continuar.", "critical"))
    if remaining_reserves <= max(1, pool_reserva_count // 5) and pool_reserva_count > 0:
        signals.append(("Atenção", "O estoque de reservas está baixo. Reponha o pool antes que novas falhas parem a rodada.", "warning"))
    if fast_annotations:
        signals.append(("Revisar qualidade", f"{len(fast_annotations)} análise(s) ficaram mais de 5 segundos abaixo da duração do vídeo.", "warning"))
    if agreement.get("videos_com_discordancia"):
        signals.append(("Revisar concordância", f"{len(agreement['videos_com_discordancia'])} vídeo(s) têm discordância entre anotadores; priorize os maiores escores.", "info"))
    if pending and assigned and completion_percent < 0.25:
        signals.append(("Ritmo da rodada", "Menos de 25% da rodada foi concluída. Confirme se todos os anotadores conseguiram iniciar a sessão.", "info"))
    if not signals:
        signals.append(("Operação estável", "Nenhum sinal preventivo relevante foi detectado nesta rodada.", "ok"))

    signals_html = "".join(
        f"<div class='insight-signal {kind}'><strong>{escape(title)}</strong><span>{escape(message)}</span></div>"
        for title, message, kind in signals
    )

    return f"""
    <section class='admin-command-center'>
        <div class='admin-section-heading'>
            <div><span class='section-eyebrow'>Painel de controle</span><h3>Leitura operacional da rodada</h3></div>
            <span class='admin-live-dot'>dados locais</span>
        </div>
        <div class='admin-kpi-grid'>{kpi_html}</div>
        <div class='admin-insight-grid'>
            <section class='admin-chart'><h4>Conclusão por rotulador</h4><p class='metric-note'>Carga concluída comparada ao total atribuído.</p>{labeler_chart}</section>
            <section class='admin-chart'><h4>Distribuição das posições</h4><p class='metric-note'>Ajuda a detectar concentração ou classes sem cobertura.</p>{stance_chart}</section>
            <section class='admin-signals'><h4>Sinais para ação</h4>{signals_html}</section>
        </div>
    </section>
    """


def agreement_summary(
    agreement_data: Dict[str, Any],
    assignments_df: Union[pd.DataFrame, List[Dict[str, Any]], None] = None,
    results_df: Union[pd.DataFrame, List[Dict[str, Any]], None] = None,
    errors_df: Union[pd.DataFrame, List[Dict[str, Any]], None] = None,
    videos_df: Union[pd.DataFrame, List[Dict[str, Any]], None] = None,
    logs_df: Union[pd.DataFrame, List[Dict[str, Any]], None] = None,
    version_name: str = "v1",
    fast_annotations: Optional[List[Dict[str, Any]]] = None,
    opcoes_tarefa: Optional[List[str]] = None,
    total_reservas: Optional[int] = None,
) -> str:
    """Renderiza a secao completa do dashboard de concordancia e auditoria do administrador."""
    df_assignments = _garantir_dataframe(assignments_df)
    df_results = _garantir_dataframe(results_df)
    df_errors = _garantir_dataframe(errors_df)
    df_videos = _garantir_dataframe(videos_df)
    if fast_annotations is None:
        todos_videos = df_videos
        fast_annotations = encontrar_anotacoes_rapidas(df_results, todos_videos) if not df_results.empty and not todos_videos.empty else []

    completed_ids = set(df_results.get("assignment_id", pd.Series(dtype=str)).astype(str).str.strip())
    completed_ids.update(df_errors.get("assignment_id", pd.Series(dtype=str)).astype(str).str.strip())

    assignment_progress = ""
    if df_assignments.empty or "labeler" not in df_assignments.columns:
        assignment_progress = "<p class='muted'>Nenhuma atribuição ativa nesta rodada.</p>"
    else:
        progress_rows = []
        for labeler, labeler_assignments in df_assignments.groupby("labeler", sort=False):
            assigned = len(labeler_assignments)
            completed = int(labeler_assignments["assignment_id"].astype(str).isin(completed_ids).sum()) if "assignment_id" in labeler_assignments.columns else 0
            pending = assigned - completed
            prog_pct = (completed / assigned) if assigned > 0 else 0.0
            progress_rows.append(
                f"<tr><td><strong>{escape(str(labeler))}</strong></td><td>{assigned}</td><td>{completed}</td><td>{pending}</td><td><strong>{prog_pct:.0%}</strong></td></tr>"
            )
        assignment_progress = f"""
        <table class='progress-table'>
            <thead><tr><th>Rotulador</th><th>Atribuídos</th><th>Concluídos</th><th>Pendentes</th><th>Progresso</th></tr></thead>
            <tbody>{''.join(progress_rows)}</tbody>
        </table>
        """

    access = access_statistics(logs_df)
    daily_chart = annotation_daily_chart(df_results)
    alfa_val = agreement_data.get("alfa")
    alfa_str = "ainda não calculável" if alfa_val is None else f"{float(alfa_val):.3f}"

    labeler_rows = "".join(
        f"<tr><td>{escape(str(item.get('labeler', '')))}</td><td>{float(item.get('penalidade', 0.0)):.2f}</td></tr>"
        for item in agreement_data.get("labelers_com_maior_discordancia", [])[:10]
    ) or "<tr><td colspan='2' class='muted'>Ainda não há discordâncias mensuráveis.</td></tr>"

    video_rows = "".join(
        f"<tr><td>{escape(str(item.get('video_id', '')))}</td><td>{' · '.join(escape(str(r)) for r in item.get('anotacoes', []))}</td><td>{float(item.get('discordancia_ordinal', 0.0)):.2f}</td></tr>"
        for item in agreement_data.get("videos_com_discordancia", [])[:10]
    ) or "<tr><td colspan='3' class='muted'>Ainda não há vídeos com múltiplas anotações discordantes.</td></tr>"

    fast_warning = fast_annotations_html(fast_annotations)
    admin_insights = admin_insights_html(
        assignments=df_assignments,
        results=df_results,
        errors=df_errors,
        videos=df_videos,
        agreement=agreement_data,
        fast_annotations=fast_annotations,
        opcoes_tarefa=opcoes_tarefa,
        total_reservas=total_reservas,
    )

    return f"""
    <section class='agreement-dashboard'>
        {admin_insights}
        <section class='assignment-progress'>
            <div class='section-heading'>
                <div><span class='section-eyebrow'>Rodada ativa</span><h3>Progresso dos rotuladores</h3></div>
                <span class='version-label'>{escape(str(version_name))}</span>
            </div>
            {assignment_progress}
        </section>
        <p class='metric-note'><strong>Como calculamos:</strong> pares iguais = 0; penalidades definidas na matriz par-a-par de distâncias. A penalidade do anotador é a média da distância entre sua resposta e as demais no mesmo vídeo.</p>
        {fast_warning}
        <div class='agreement-kpis'>
            <div class='kpi'><span>Concordância ponderada</span><strong>{alfa_str}</strong></div>
            <div class='kpi'><span>Vídeos comparáveis</span><strong>{agreement_data.get('videos_com_multiplas_anotacoes', 0)}</strong></div>
            <div class='kpi'><span>Anotações consideradas</span><strong>{agreement_data.get('anotacoes_consideradas', 0)}</strong></div>
        </div>
        <div class='dashboard-grid'>
            <section class='dashboard-card'>
                <h3>Anotadores com maior penalidade</h3>
                <table><thead><tr><th>Anotador</th><th>Penalidade acumulada</th></tr></thead><tbody>{labeler_rows}</tbody></table>
            </section>
            <section class='dashboard-card'>
                <h3>Vídeos com maior discordância</h3>
                <table><thead><tr><th>Vídeo</th><th>Anotações</th><th>Distância</th></tr></thead><tbody>{video_rows}</tbody></table>
            </section>
        </div>
        <section class='analytics-grid'>
            <section class='dashboard-card daily-annotation-chart'>
                <h3>Vídeos concluídos por dia e rotulador</h3>
                <p class='metric-note'>Cada barra mostra quantos vídeos foram registrados por pessoa em cada dia da rodada selecionada.</p>
                {daily_chart}
            </section>
        </section>
        <section class='analytics-grid'>
            <section class='dashboard-card'>
                <h3>Logins por dia</h3>
                <p class='metric-note'>Barras representam a quantidade diária de entradas.</p>
                {access['daily_rows']}
            </section>
            <section class='dashboard-card'>
                <h3>Sessões por anotador</h3>
                <p class='metric-note'>Média geral: {access['avg_minutes']:.1f} min por sessão.</p>
                {access['session_rows']}
            </section>
        </section>
    </section>
    """


_ICONES_TOAST = {"sucesso": "✓", "erro": "!", "info": "i"}


def renderizar_toast_html(
    mensagem: str,
    tipo: Optional[str] = None,
    acao_rotulo: str = "",
    acao_tipo: str = "",
    acao_tarefa_id: Any = "",
) -> str:
    """Renderiza um aviso efemero no canto da tela que some sozinho por animacao CSS.

    O tipo e inferido pelo prefixo da mensagem quando nao informado. Quando ha acao, o botao
    dispara o mesmo canal usado pelas tabelas do hub.
    """
    texto = str(mensagem or "").strip()
    if not texto:
        return ""
    if tipo is None:
        tipo = "sucesso" if texto.startswith("✅") else "erro" if texto.startswith("⚠️") else "info"
    for prefixo in ("✅", "⚠️"):
        if texto.startswith(prefixo):
            texto = texto[len(prefixo):].strip()
    corpo = escape(texto).replace("\n", "<br>")
    for trecho in sorted(set(re.findall(r"\*\*(.+?)\*\*", corpo))):
        corpo = corpo.replace(f"**{trecho}**", f"<strong>{trecho}</strong>")
    botao = ""
    classe_vida = "toast-curto"
    if acao_rotulo and acao_tipo:
        classe_vida = "toast-longo"
        botao = (
            f"<button type='button' class='toast-acao' "
            f"onclick=\"window.tokstanceAcao('{escape(acao_tipo)}', '{escape(str(acao_tarefa_id))}')\">"
            f"{escape(acao_rotulo)}</button>"
        )
    nonce = f"{time.time_ns()}"
    return (
        f"<div class='tokstance-toast toast-{tipo} {classe_vida}' role='status' data-nonce='{nonce}'>"
        f"<span class='toast-icone'>{_ICONES_TOAST.get(tipo, 'i')}</span>"
        f"<div class='toast-texto'>{corpo}</div>{botao}</div>"
    )
