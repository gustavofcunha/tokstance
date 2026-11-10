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
    <div style="display: flex; justify-content: center; width: 100%; height: 100%; margin: 0; padding: 0;">
        <iframe
            style="width: min(100%, calc(var(--altura-player, 500px) * 0.5625)); height: var(--altura-player, 500px); min-height: 560px; border: none; overflow: hidden; display: block; background: #ffffff; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);"
            scrolling="no"
            src="{player_url}"
            title="Player do vídeo TikTok"
            allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
            allowfullscreen
        ></iframe>
    </div>
    """


def formatar_pergunta_com_target(pergunta_template: Optional[str], target: str) -> str:
    """Formata a pergunta embutindo o nome do target com a mesma formatacao da pergunta."""
    alvo = escape(str(target or "").strip())
    target_formatado = f'"{alvo}"'
    template = str(pergunta_template or "").strip()

    if not template:
        return f'Com relação ao target {target_formatado}, como você classifica a posição deste vídeo?'

    #se o template tiver {target} com ou sem aspas
    if "{target}" in template:
        for aspas_target in ['"{target}"', "'{target}'", "“{target}”", "”{target}”"]:
            if aspas_target in template:
                template = template.replace(aspas_target, target_formatado)
        return template.replace("{target}", target_formatado)

    #se contiver literal ao target
    padrao_ao_target = re.compile(r'\bao\s+target\b', re.IGNORECASE)
    if padrao_ao_target.search(template):
        return padrao_ao_target.sub(f'ao target {target_formatado}', template)

    #se contiver literal ao alvo
    padrao_ao_alvo = re.compile(r'\bao\s+alvo\b', re.IGNORECASE)
    if padrao_ao_alvo.search(template):
        return padrao_ao_alvo.sub(f'ao alvo {target_formatado}', template)

    #se contiver a palavra target isolada
    padrao_target = re.compile(r'\btarget\b', re.IGNORECASE)
    if padrao_target.search(template):
        return padrao_target.sub(f'target {target_formatado}', template)

    #se contiver a palavra alvo isolada
    padrao_alvo = re.compile(r'\balvo\b', re.IGNORECASE)
    if padrao_alvo.search(template):
        return padrao_alvo.sub(f'alvo {target_formatado}', template)

    #caso a pergunta nao mencione target nem alvo
    return f'{template} (Target: {target_formatado})'


def render_video_card(
    item: Dict[str, Any],
    highlight_target: bool = False,
    tarefa_titulo: str = "",
    rotulador_nome: str = "",
) -> str:
    """Renderiza os blocos independentes de metadados (tarefa, target, descricao, transcricao) e o player TikTok."""
    target = str(item.get("target", "") or "").strip()
    description = str(item.get("video_description", "") or "").strip()
    transcription = str(item.get("voice_to_text", "") or "").strip()
    url = str(item.get("url", "") or "").strip()

    titulo_t = str(tarefa_titulo or item.get("tarefa_titulo", "") or "").strip()
    nome_r = str(rotulador_nome or item.get("rotulador_nome", "") or item.get("labeler", "") or "").strip()

    cabecalho_html = ""
    if titulo_t or nome_r:
        labeler_badge = f"<span class='user-pill'>{escape(nome_r)}</span>" if nome_r else ""
        cabecalho_html = (
            f"<div class='labeler-header-badge-wrapper'>"
            f"<div class='labeler-info-badge'>"
            f"<div><span>Tarefa:</span> <strong>{escape(titulo_t)}</strong></div>"
            f"<div><span>Rotulador:</span> {labeler_badge}</div>"
            f"</div>"
            f"</div>"
        )

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
    target_badge_html = f"<span class='target-name-badge'>{escape(target)}</span>" if target else ""

    return f"""
    <div class='video-card'>
        <div class='video-context-column'>
            {cabecalho_html}
            <div class='video-meta{transicao_classe}'><strong>Target:</strong> {target_badge_html}</div>
            <div class='{description_class}'>
                <div class='metadata-title'>Descrição do vídeo</div>
                <div class='metadata-text'>{description_html}</div>
            </div>
            <div class='{transcription_class}'>
                <div class='metadata-title'>Transcrição do áudio <span class='transcription-note'>(pode conter erros)</span></div>
                <div class='metadata-text'>{transcription_html}</div>
            </div>
        </div>
        <div class='video-player-column'>
            {render_tiktok(url)}
        </div>
    </div>
    """


def generate_progress_bar(position: int, total: int) -> str:
    """Renderiza a barra de progresso visual com contador e percentual."""
    percent = int((position / total) * 100) if total > 0 else 100
    return f"""
    <div style="width: 100%; margin: 2px 0 4px 0;">
        <div style="width: 100%; background-color: #e2e8f0; border-radius: 4px; height: 6px; overflow: hidden; box-shadow: inset 0 1px 2px rgba(0,0,0,0.06);">
            <div style="width: {percent}%; background-color: #9c0014; height: 100%; transition: width 0.4s ease;"></div>
        </div>
        <div style="text-align: right; font-size: 11px; color: #475569; font-weight: 700; margin-top: 2px;">
            {position} de {total} ({percent}%)
        </div>
    </div>
    """


def video_outputs(
    queue: List[Dict[str, Any]],
    position: int,
    username_clean: str = "",
    pergunta_template: Optional[str] = None,
    highlight_first: bool = False,
    tarefa_titulo: str = "",
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
    texto_pergunta = formatar_pergunta_com_target(pergunta_template, target)

    previous_target = (
        str(queue[position - 1].get("target", "") or "").strip()
        if position > 0
        else ""
    )
    target_changed = (position == 0 and highlight_first) or (
        position > 0 and previous_target != target
    )
    transicao_classe = " target-transition" if target_changed else ""
    pergunta_markdown = f'<div class="target-question{transicao_classe}"><strong>{texto_pergunta}</strong></div>'
    pb = generate_progress_bar(position, total)
    video_html = render_video_card(
        item,
        target_changed,
        tarefa_titulo=tarefa_titulo,
        rotulador_nome=username_clean,
    )
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
        f"<td>{escape(str(item.get('rotulador') or item.get('labeler') or ''))}</td>"
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
    """Gera grafico de linhas SVG: uma linha por rotulador, eixo x em dias e eixo y em videos concluidos."""
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
    dias = sorted(counts["dia"].unique())
    colors = ["#9c0014", "#176b87", "#b56b00", "#4f6f52", "#704c8a", "#8b5e3c"]
    color_map = {labeler: colors[idx % len(colors)] for idx, labeler in enumerate(labelers)}

    max_count = max(int(counts["quantidade"].max()), 1)
    #topo do eixo y arredondado para inteiro com ticks inteiros
    passo = max(1, -(-max_count // 5))
    topo = passo * (-(-max_count // passo))

    largura, altura = 760, 320
    margem_esq, margem_dir, margem_top, margem_base = 48, 24, 16, 48
    area_l = largura - margem_esq - margem_dir
    area_a = altura - margem_top - margem_base

    def pos_x(i: int) -> float:
        if len(dias) == 1:
            return margem_esq + area_l / 2
        return margem_esq + area_l * i / (len(dias) - 1)

    def pos_y(valor: float) -> float:
        return margem_top + area_a * (1 - valor / topo)

    grade = []
    for tick in range(0, topo + 1, passo):
        y = pos_y(tick)
        grade.append(
            f"<line x1='{margem_esq}' y1='{y:.1f}' x2='{largura - margem_dir}' y2='{y:.1f}' stroke='#e2e8f0' stroke-width='1'/>"
            f"<text x='{margem_esq - 8}' y='{y + 4:.1f}' text-anchor='end' font-size='11' fill='#64748b'>{tick}</text>"
        )
    passo_rotulo = max(1, -(-len(dias) // 8))
    for i, dia in enumerate(dias):
        if i % passo_rotulo == 0 or i == len(dias) - 1:
            rotulo = f"{dia[8:10]}/{dia[5:7]}"
            grade.append(
                f"<text x='{pos_x(i):.1f}' y='{altura - margem_base + 18}' text-anchor='middle' font-size='11' fill='#64748b'>{escape(rotulo)}</text>"
            )

    series = []
    for labeler in labelers:
        valores = dict(zip(
            counts.loc[counts["labeler"].astype(str) == labeler, "dia"],
            counts.loc[counts["labeler"].astype(str) == labeler, "quantidade"],
        ))
        pontos = [(pos_x(i), pos_y(int(valores.get(dia, 0))), int(valores.get(dia, 0)), dia) for i, dia in enumerate(dias)]
        cor = color_map[labeler]
        caminho = " ".join(f"{x:.1f},{y:.1f}" for x, y, _, _ in pontos)
        linha = f"<polyline points='{caminho}' fill='none' stroke='{cor}' stroke-width='2.5' stroke-linejoin='round' stroke-linecap='round'/>"
        marcas = "".join(
            f"<circle cx='{x:.1f}' cy='{y:.1f}' r='4' fill='{cor}' stroke='#ffffff' stroke-width='1.5'>"
            f"<title>{escape(labeler)}: {qtd} vídeo(s) em {escape(dia)}</title></circle>"
            for x, y, qtd, dia in pontos
        )
        series.append(f"<g class='line-series'>{linha}{marcas}</g>")

    legend = "".join(
        f"<span class='chart-legend-item'><i style='background:{color_map[labeler]}'></i>{escape(labeler)}</span>"
        for labeler in labelers
    )
    svg = (
        f"<svg class='daily-line-chart' viewBox='0 0 {largura} {altura}' width='100%' role='img' "
        f"aria-label='Vídeos concluídos por dia e rotulador' preserveAspectRatio='xMidYMid meet'>"
        f"{''.join(grade)}"
        f"<line x1='{margem_esq}' y1='{margem_top}' x2='{margem_esq}' y2='{margem_top + area_a}' stroke='#94a3b8'/>"
        f"<line x1='{margem_esq}' y1='{margem_top + area_a}' x2='{largura - margem_dir}' y2='{margem_top + area_a}' stroke='#94a3b8'/>"
        f"{''.join(series)}"
        f"<text x='{margem_esq + area_l / 2:.1f}' y='{altura - 6}' text-anchor='middle' font-size='12' fill='#475569'>Data</text>"
        f"<text transform='translate(12 {margem_top + area_a / 2:.1f}) rotate(-90)' text-anchor='middle' font-size='12' fill='#475569'>Vídeos concluídos</text>"
        f"</svg>"
    )
    return f"<div class='chart-legend'>{legend}</div>{svg}"


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


def _classe_cor_posicao(stance: str) -> str:
    """Retorna a classe CSS semantica para o badge de uma posicao de anotacao."""
    texto = str(stance or "").strip().lower()
    if any(k in texto for k in ("favor", "positiv", "concord", "apoia", "sim")):
        return "stance-favor"
    if any(k in texto for k in ("contra", "negativ", "discord", "oposi", "tóxic", "toxic", "não", "nao")):
        if "não relacionado" not in texto and "nao relacionado" not in texto:
            return "stance-contra"
    if any(k in texto for k in ("neutr", "incert", "moderad", "imparcial")):
        return "stance-neutro"
    return "stance-outro"


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
    contagem_concluidos_por_rotulador: Dict[str, int] = {}
    if df_assignments.empty or "labeler" not in df_assignments.columns:
        assignment_progress = "<p class='muted'>Nenhuma atribuição ativa nesta rodada.</p>"
    else:
        progress_rows = []
        for labeler, labeler_assignments in df_assignments.groupby("labeler", sort=False):
            assigned = len(labeler_assignments)
            completed = int(labeler_assignments["assignment_id"].astype(str).isin(completed_ids).sum()) if "assignment_id" in labeler_assignments.columns else 0
            contagem_concluidos_por_rotulador[str(labeler).strip()] = completed
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

    #mapa consolidado de metadados de videos (url, target, descricao e transcricao)
    mapa_videos: Dict[str, Dict[str, str]] = {}
    for quadro, col_id in (
        (df_videos, "id"),
        (df_videos, "video_id"),
        (df_assignments, "video_id"),
        (df_results, "video_id"),
    ):
        if quadro.empty or col_id not in quadro.columns:
            continue
        for _, row in quadro.iterrows():
            vid_key = str(row.get(col_id, "") or "").strip()
            if not vid_key:
                continue
            reg = mapa_videos.setdefault(
                vid_key,
                {"url": "", "target": "", "video_description": "", "voice_to_text": ""},
            )
            for campo in ("url", "target", "video_description", "voice_to_text"):
                if not reg[campo] and campo in row:
                    val = str(row.get(campo, "") or "").strip()
                    if val:
                        reg[campo] = val

    #mapa de votos por video e contagem de videos avaliados por rotulador
    votos_por_video: Dict[str, List[Dict[str, str]]] = {}
    contagem_resultados_por_rotulador: Dict[str, int] = {}
    if not df_results.empty and "labeler" in df_results.columns:
        if "video_id" in df_results.columns:
            contagem_resultados_por_rotulador = (
                df_results.groupby("labeler")["video_id"].nunique().astype(int).to_dict()
            )
        else:
            contagem_resultados_por_rotulador = (
                df_results.groupby("labeler").size().astype(int).to_dict()
            )
    if not df_results.empty and {"video_id", "stance"}.issubset(df_results.columns):
        for _, row in df_results.iterrows():
            vid_key = str(row.get("video_id", "") or "").strip()
            pos_val = str(row.get("stance", "") or "").strip()
            rot_val = str(row.get("labeler", "") or "").strip()
            if vid_key and pos_val:
                votos_por_video.setdefault(vid_key, []).append(
                    {"rotulador": rot_val, "stance": pos_val}
                )

    daily_chart = annotation_daily_chart(df_results)
    alfa_val = agreement_data.get("alfa")
    alfa_str = "ainda não calculável" if alfa_val is None else f"{float(alfa_val):.3f}"

    lista_videos_discordantes = list(agreement_data.get("videos_com_discordancia", []) or [])
    divergencias_por_rotulador_fallback: Dict[str, int] = {}
    for item_v in lista_videos_discordantes:
        v_id_tmp = str(item_v.get("video_id", "") or "").strip()
        votos_tmp = item_v.get("anotacoes_por_rotulador") or votos_por_video.get(v_id_tmp, [])
        for r_unica in {str(v.get("rotulador", "") or "").strip() for v in votos_tmp if v.get("rotulador")}:
            divergencias_por_rotulador_fallback[r_unica] = divergencias_por_rotulador_fallback.get(r_unica, 0) + 1

    lista_penalidades = (
        agreement_data.get("rotuladores_com_maior_discordancia")
        or agreement_data.get("labelers_com_maior_discordancia")
        or []
    )
    max_penalidade = max((float(it.get("penalidade", 0.0)) for it in lista_penalidades), default=1.0) or 1.0

    linhas_penalidade_html = []
    for idx, item in enumerate(lista_penalidades[:10], start=1):
        nome_rot = str(item.get("rotulador") or item.get("labeler") or "").strip()
        pen_val = float(item.get("penalidade", 0.0))
        qtd_videos_raw = item.get("quantidade_videos")
        if qtd_videos_raw is None:
            qtd_videos_raw = (
                contagem_resultados_por_rotulador.get(nome_rot)
                or contagem_concluidos_por_rotulador.get(nome_rot)
                or divergencias_por_rotulador_fallback.get(nome_rot)
                or (1 if pen_val > 0 else 0)
            )
        qtd_videos = int(qtd_videos_raw)
        qtd_div_raw = item.get("videos_divergentes")
        if qtd_div_raw is None:
            qtd_div_raw = divergencias_por_rotulador_fallback.get(nome_rot, 0)
        qtd_div = int(qtd_div_raw)
        pen_media_raw = item.get("penalidade_media")
        if pen_media_raw is None:
            pen_media_raw = pen_val / max(1, qtd_videos)
        pen_media = float(pen_media_raw)
        pct_bar = min(100.0, max(8.0, (pen_val / max_penalidade) * 100.0)) if pen_val > 0 else 0.0
        rotulo_unid = "vídeo" if qtd_videos == 1 else "vídeos"
        pill_div = (
            f"<span class='penalty-divergent-pill' title='Vídeos em que houve divergência com outros anotadores'>"
            f"{qtd_div} {'divergente' if qtd_div == 1 else 'divergentes'}</span>"
            if qtd_div > 0
            else ""
        )
        linhas_penalidade_html.append(
            f"<tr>"
            f"<td class='td-penalty-user'><div class='penalty-annotator-cell'><span class='penalty-rank-badge'>{idx}º</span><strong class='penalty-user-name'>{escape(nome_rot)}</strong></div></td>"
            f"<td class='td-penalty-videos'><div class='penalty-videos-cell'><span class='penalty-videos-count'><strong>{qtd_videos}</strong> {rotulo_unid}</span>{pill_div}</div></td>"
            f"<td class='td-penalty-avg'><span class='penalty-avg-badge'>{pen_media:.2f} <small>/ vídeo</small></span></td>"
            f"<td class='td-penalty-total'><div class='penalty-bar-wrap'><strong class='penalty-total-val'>{pen_val:.2f}</strong><div class='penalty-bar-track'><div class='penalty-bar-fill' style='width:{pct_bar:.0f}%;'></div></div></div></td>"
            f"</tr>"
        )

    labeler_rows = "".join(linhas_penalidade_html) or "<tr><td colspan='4' class='muted'>Ainda não há discordâncias mensuráveis.</td></tr>"

    max_dist_video = max((float(it.get("discordancia_ordinal", 0.0)) for it in lista_videos_discordantes), default=1.0) or 1.0
    linhas_videos_html = []
    for idx_v, item in enumerate(lista_videos_discordantes[:30], start=1):
        vid_id = str(item.get("video_id", "") or "").strip()
        meta = mapa_videos.get(vid_id, {})
        url_raw = str(item.get("url", "") or meta.get("url", "") or "").strip()
        if url_raw:
            url_href = url_raw
            url_display = url_raw
        elif vid_id.isdigit():
            url_href = f"https://www.tiktok.com/video/{vid_id}"
            url_display = url_href
        else:
            url_href = f"https://www.tiktok.com/video/{vid_id}"
            url_display = f"{url_href} ({vid_id})"

        target_val = str(item.get("target", "") or meta.get("target", "") or "").strip()
        desc_val = str(item.get("video_description", "") or meta.get("video_description", "") or "").strip()
        trans_val = str(item.get("voice_to_text", "") or meta.get("voice_to_text", "") or "").strip()

        desc_html = (
            escape(desc_val).replace("\n", "<br>")
            if desc_val
            else "<span class='disagreement-empty-meta'>Descrição não informada no acervo.</span>"
        )
        trans_html = (
            escape(trans_val).replace("\n", "<br>")
            if trans_val
            else "<span class='disagreement-empty-meta'>Transcrição indisponível para este vídeo.</span>"
        )

        votos_det = (
            votos_por_video.get(vid_id)
            or item.get("anotacoes_por_rotulador")
            or [
                {"rotulador": f"Rotulador {i + 1}", "stance": str(r)}
                for i, r in enumerate(item.get("anotacoes", []))
            ]
        )
        chips_votos = []
        for voto in votos_det:
            r_nome = str(voto.get("rotulador", "") or "").strip() or "Rotulador"
            p_nome = str(voto.get("stance", "") or "").strip()
            classe_cor = _classe_cor_posicao(p_nome)
            chips_votos.append(
                f"<div class='annotator-vote-item'>"
                f"<span class='annotator-vote-name' title='Rotulador'>"
                f"<svg class='vote-user-icon' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'><path d='M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2'/><circle cx='12' cy='7' r='4'/></svg>"
                f"<strong>{escape(r_nome)}</strong></span>"
                f"<span class='annotator-vote-right'>"
                f"<span class='annotator-vote-sep'>→</span>"
                f"<span class='annotator-stance-pill {classe_cor}'>{escape(p_nome)}</span>"
                f"</span>"
                f"</div>"
            )
        lista_anotacoes_bruta = item.get("anotacoes") or [v.get("stance", "") for v in votos_det]
        resumo_anotacoes_str = " · ".join(escape(str(r)) for r in lista_anotacoes_bruta if str(r).strip())
        votos_cell_html = (
            f"<div class='annotator-vote-list'>{''.join(chips_votos)}</div>"
            f"<div class='annotator-votes-summary'>Posições: {resumo_anotacoes_str}</div>"
        )

        dist_val = float(item.get("discordancia_ordinal", 0.0))
        sev_tipo = "alta" if dist_val >= 1.5 else "moderada"
        sev_rotulo = "Alta divergência" if dist_val >= 1.5 else "Divergência moderada"
        pct_dist = min(100.0, max(14.0, (dist_val / max_dist_video) * 100.0))

        target_pill_html = (
            f"<div class='disagreement-target-row'>"
            f"<span class='disagreement-target-label'>Target:</span>"
            f"<span class='disagreement-target-pill'>{escape(target_val)}</span>"
            f"</div>"
            if target_val
            else ""
        )

        busca_indexada = (
            f"{vid_id} {url_display} {target_val} {desc_val} {trans_val} "
            + " ".join(f"{v.get('rotulador', '')} {v.get('stance', '')}" for v in votos_det)
        ).lower()
        player_dom_id = f"disagreement-player-{re.sub(r'[^a-zA-Z0-9_-]', '_', vid_id)}_{idx_v}"

        linhas_videos_html.append(
            f"<tr class='disagreement-row' data-severity='{sev_tipo}' data-video-id='{escape(vid_id)}' data-search='{escape(busca_indexada)}'>"
            f"<td class='td-disagreement-video'>"
            f"{target_pill_html}"
            f"<a href='{escape(url_href)}' target='_blank' rel='noopener noreferrer' class='disagreement-url-link' title='Abrir vídeo em nova aba ({escape(vid_id)})'>"
            f"<svg class='url-ext-icon' width='13' height='13' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'><path d='M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6'/><polyline points='15 3 21 3 21 9'/><line x1='10' y1='14' x2='21' y2='3'/></svg>"
            f"<span>{escape(url_display)}</span></a>"
            f"<div class='disagreement-url-actions'>"
            f"<button type='button' class='disagreement-mini-btn' onclick=\"window.tokstanceCopiar('{escape(url_href)}')\">Copiar URL</button>"
            f"<button type='button' class='disagreement-mini-btn preview-toggle-btn' onclick=\"window.tokstanceAlternarPlayer(this, '{escape(player_dom_id)}', '{escape(url_href)}')\">▶ Assistir vídeo</button>"
            f"</div>"
            f"<div id='{escape(player_dom_id)}' class='disagreement-inline-player' style='display:none;'></div>"
            f"</td>"
            f"<td class='td-disagreement-context'>"
            f"<div class='disagreement-context-grid'>"
            f"<div class='disagreement-context-box'>"
            f"<div class='disagreement-context-title'>Descrição do vídeo</div>"
            f"<div class='disagreement-context-text'>{desc_html}</div>"
            f"</div>"
            f"<div class='disagreement-context-box transcription'>"
            f"<div class='disagreement-context-title'>Transcrição do áudio</div>"
            f"<div class='disagreement-context-text'>{trans_html}</div>"
            f"</div>"
            f"</div>"
            f"</td>"
            f"<td class='td-disagreement-votes'>{votos_cell_html}</td>"
            f"<td class='td-disagreement-distance'>"
            f"<div class='disagreement-score-cell'>"
            f"<strong class='disagreement-score-val'>{dist_val:.2f}</strong>"
            f"<span class='disagreement-severity-badge {sev_tipo}'>{sev_rotulo}</span>"
            f"<div class='disagreement-dist-bar'><div class='disagreement-dist-fill {sev_tipo}' style='width:{pct_dist:.0f}%;'></div></div>"
            f"</div>"
            f"</td>"
            f"</tr>"
        )

    video_rows = (
        "".join(linhas_videos_html)
        or "<tr><td colspan='4' class='muted'>Ainda não há vídeos com múltiplas anotações discordantes.</td></tr>"
    )
    qtd_discordantes = len(lista_videos_discordantes)
    qtd_alta_sev = sum(1 for it in lista_videos_discordantes if float(it.get("discordancia_ordinal", 0.0)) >= 1.5)
    qtd_mod_sev = qtd_discordantes - qtd_alta_sev

    media_pen_equipe = (
        sum(float(it.get("penalidade", 0.0)) for it in lista_penalidades) / len(lista_penalidades)
        if lista_penalidades
        else 0.0
    )
    rodape_penalidades_html = (
        f"<div class='penalty-summary-footer'>"
        f"<div class='penalty-stat-item'><span>Anotadores com desvio</span><strong>{len(lista_penalidades)}</strong></div>"
        f"<div class='penalty-stat-item'><span>Penalidade média da equipe</span><strong>{media_pen_equipe:.2f}</strong></div>"
        f"<div class='penalty-stat-item'><span>Vídeos em disputa</span><strong>{qtd_discordantes}</strong></div>"
        f"</div>"
        if lista_penalidades
        else ""
    )

    toolbar_discordancia_html = (
        f"<div class='disagreement-toolbar'>"
        f"<div class='disagreement-search-wrap'>"
        f"<input type='search' class='disagreement-search-input' placeholder='Filtrar por URL, target, rotulador, posição, descrição ou transcrição...' oninput='window.tokstanceFiltrarDiscordancia(this)' aria-label='Filtrar vídeos com discordância' />"
        f"</div>"
        f"<div class='disagreement-filter-pills'>"
        f"<button type='button' class='disagreement-filter-btn active' data-filter='all' onclick=\"window.tokstanceFiltrarSeveridade(this, 'all')\">Todos ({qtd_discordantes})</button>"
        f"<button type='button' class='disagreement-filter-btn' data-filter='alta' onclick=\"window.tokstanceFiltrarSeveridade(this, 'alta')\">Alta divergência ({qtd_alta_sev})</button>"
        f"<button type='button' class='disagreement-filter-btn' data-filter='moderada' onclick=\"window.tokstanceFiltrarSeveridade(this, 'moderada')\">Moderada ({qtd_mod_sev})</button>"
        f"</div>"
        f"</div>"
        if qtd_discordantes > 0
        else ""
    )

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
            <section class='dashboard-card penalty-leaderboard-card'>
                <div class='card-heading-block'>
                    <div>
                        <span class='section-eyebrow'>Consistência por anotador</span>
                        <h3>Anotadores com maior penalidade</h3>
                    </div>
                </div>
                <p class='metric-note'>Relação entre a quantidade de vídeos avaliados, a frequência de divergência e a penalidade acumulada.</p>
                <table class='penalty-table'>
                    <thead>
                        <tr>
                            <th>Anotador</th>
                            <th>Qtd. de Vídeos</th>
                            <th>Média / Vídeo</th>
                            <th class='th-right'>Penalidade acumulada</th>
                        </tr>
                    </thead>
                    <tbody>{labeler_rows}</tbody>
                </table>
                {rodape_penalidades_html}
            </section>
            <section class='dashboard-card daily-annotation-chart'>
                <div class='card-heading-block'>
                    <div>
                        <span class='section-eyebrow'>Ritmo de execução</span>
                        <h3>Vídeos concluídos por dia e rotulador</h3>
                    </div>
                </div>
                <p class='metric-note'>Cada linha representa um rotulador: o eixo x mostra a data e o eixo y a quantidade de vídeos concluídos no dia.</p>
                {daily_chart}
            </section>
        </div>
        <section class='disagreement-full-row'>
            <section class='dashboard-card disagreement-full-card'>
                <div class='disagreement-card-header'>
                    <div>
                        <span class='section-eyebrow'>Diagnóstico de consenso e adjudicação</span>
                        <h3>Vídeos com maior discordância</h3>
                        <p class='metric-note'>Inspeção detalhada dos vídeos com divergência entre rotuladores, exibindo URL direta, descrição, transcrição e a posição atribuída por cada anotador.</p>
                    </div>
                    <span class='disagreement-total-badge'>{qtd_discordantes} {'vídeo divergente' if qtd_discordantes == 1 else 'vídeos divergentes'}</span>
                </div>
                {toolbar_discordancia_html}
                <div class='disagreement-table-wrapper'>
                    <table class='disagreement-table'>
                        <thead>
                            <tr>
                                <th class='th-col-video'>Vídeo (URL e Target)</th>
                                <th class='th-col-context'>Descrição e Transcrição</th>
                                <th class='th-col-votes'>Anotações por Rotulador</th>
                                <th class='th-col-dist'>Distância</th>
                            </tr>
                        </thead>
                        <tbody>
                            {video_rows}
                            <tr class='disagreement-no-match-row' style='display:none;'>
                                <td colspan='4' class='muted'>Nenhum vídeo divergente corresponde ao filtro informado.</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
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
    dispara o mesmo canal usado pelas tabelas do painel principal.
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


def renderizar_visao_geral_acervo_html(
    metricas: Dict[str, Any],
    tarefa_meta: Optional[Dict[str, Any]] = None,
) -> str:
    """Renderiza a visao geral oficial do acervo de videos da tarefa e a distribuicao por target."""
    tot_p = int(metricas.get("total_videos_principais", 0))
    tot_r = int(metricas.get("total_videos_reservas", 0))
    tot_acervo = int(metricas.get("total_videos_acervo", tot_p + tot_r))
    tot_atrib = int(metricas.get("total_atribuicoes", 0))
    distribuicao = metricas.get("distribuicao_targets", [])

    kpi_cards = f"""
    <div class="collection-kpis-grid">
        <div class="collection-kpi-card">
            <span class="collection-kpi-label">Total no Acervo</span>
            <strong class="collection-kpi-value">{tot_acervo}</strong>
            <small class="collection-kpi-note">vídeos englobados na tarefa</small>
        </div>
        <div class="collection-kpi-card highlight-principal">
            <span class="collection-kpi-label">Vídeos a Distribuir</span>
            <strong class="collection-kpi-value">{tot_p}</strong>
            <small class="collection-kpi-note">pool principal para rotulação</small>
        </div>
        <div class="collection-kpi-card highlight-reserva">
            <span class="collection-kpi-label">Vídeos de Reserva</span>
            <strong class="collection-kpi-value">{tot_r}</strong>
            <small class="collection-kpi-note">reserva técnica balanceada</small>
        </div>
        <div class="collection-kpi-card">
            <span class="collection-kpi-label">Atribuições Geradas</span>
            <strong class="collection-kpi-value">{tot_atrib}</strong>
            <small class="collection-kpi-note">alocações nesta rodada</small>
        </div>
    </div>
    """

    if distribuicao:
        linhas_tabela = []
        for item in distribuicao:
            alvo = escape(str(item.get("target", "")))
            qtd_p = int(item.get("principais", 0))
            qtd_r = int(item.get("reservas", 0))
            qtd_t = int(item.get("total", 0))
            pct = float(item.get("percentual", 0.0))
            linhas_tabela.append(
                f"""
                <tr>
                    <td class="td-target"><span class="target-name-badge-table">{alvo}</span></td>
                    <td class="td-num">{qtd_p}</td>
                    <td class="td-num">{qtd_r}</td>
                    <td class="td-num"><strong>{qtd_t}</strong></td>
                    <td class="td-pct">
                        <div class="target-pct-bar-wrap">
                            <span class="target-pct-text">{pct:.1f}%</span>
                            <div class="target-pct-track">
                                <div class="target-pct-fill" style="width: {pct:.1f}%;"></div>
                            </div>
                        </div>
                    </td>
                </tr>
                """
            )
        corpo_tabela = "".join(linhas_tabela)
        total_p_sum = sum(int(it.get("principais", 0)) for it in distribuicao)
        total_r_sum = sum(int(it.get("reservas", 0)) for it in distribuicao)
        total_t_sum = sum(int(it.get("total", 0)) for it in distribuicao)
        tfoot_tabela = f"""
        <tfoot>
            <tr>
                <td><strong>Total Geral</strong></td>
                <td class="td-num"><strong>{total_p_sum}</strong></td>
                <td class="td-num"><strong>{total_r_sum}</strong></td>
                <td class="td-num"><strong>{total_t_sum}</strong></td>
                <td class="td-pct"><strong>100.0%</strong></td>
            </tr>
        </tfoot>
        """
    else:
        corpo_tabela = "<tr><td colspan='5' class='muted' style='text-align:center; padding:16px;'>Nenhum vídeo cadastrado nesta tarefa.</td></tr>"
        tfoot_tabela = ""

    tabela_html = f"""
    <div class="target-distribution-section">
        <div class="target-distribution-heading">
            <h4>Distribuição Temática por Target</h4>
            <span class="target-distribution-count">{len(distribuicao)} targets</span>
        </div>
        <table class="target-distribution-table">
            <thead>
                <tr>
                    <th class="th-target">Target (Tema)</th>
                    <th class="th-num">Vídeos Principais</th>
                    <th class="th-num">Vídeos Reserva</th>
                    <th class="th-num">Total no Acervo</th>
                    <th class="th-pct">Proporção no Acervo</th>
                </tr>
            </thead>
            <tbody>
                {corpo_tabela}
            </tbody>
            {tfoot_tabela}
        </table>
    </div>
    """

    return f"""
    <section class="admin-collection-overview">
        <div class="collection-overview-header">
            <div>
                <span class="section-eyebrow">Acervo da Tarefa</span>
                <h3>Visão Geral do Acervo e Distribuição Temática</h3>
            </div>
            <span class="collection-overview-badge">Visão Oficial</span>
        </div>
        {kpi_cards}
        {tabela_html}
    </section>
    """

