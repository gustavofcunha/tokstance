"""Componentes visuais e renderizadores HTML (versao inicial do frontend)."""

from html import escape
from typing import Any, Dict, List, Optional, Tuple
import gradio as gr


def render_tiktok(url: str) -> str:
    """Gera o iframe responsivo do player incorporado oficial do TikTok."""
    video_id = str(url or "").rstrip("/").split("/")[-1].split("?")[0]
    player_url = f"https://www.tiktok.com/player/v1/{escape(video_id)}?music_info=1&description=1&rel=0"
    return f"""
    <div style="display: flex; justify-content: center; width: 100%; margin: 0; padding: 0;">
        <iframe
            style="width: min(100%, 600px); height: 720px; border: none; overflow: hidden; display: block; background: #ffffff; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);"
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
    <div style="width: 100%; margin-bottom: 25px;">
        <div style="width: 100%; background-color: #e0e0e0; border-radius: 6px; height: 12px; overflow: hidden; box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);">
            <div style="width: {percent}%; background-color: #9c0014; height: 100%; transition: width 0.4s ease;"></div>
        </div>
        <div style="text-align: right; font-size: 14px; color: #333; font-weight: 600; margin-top: 6px;">
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
