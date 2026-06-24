import html
import json
import re
from pathlib import Path

from src.utils.helpers import get_local_media_path


def context_content_html(ctx) -> str:
    content = ctx.content
    if ctx.context_type == "AUDIO_SRT":
        return audio_srt_context_html(content)
    if ctx.context_type == "IMAGE_DIAGRAM":
        return image_diagram_context_html(content)

    if isinstance(content, dict):
        raw = str(content.get("text", ""))
    else:
        raw = str(content or "")
    safe = html.escape(raw)

    def replace_placeholder(match):
        num = match.group(1)
        return (
            f'<a href="{num}" style="text-decoration:none; color:#0078d4;">'
            f"({num}) ________</a>"
        )

    safe = re.sub(r"\[\[(\d+)\]\]", replace_placeholder, safe)
    return safe.replace("\n", "<br>") or "<i>No context text saved.</i>"


def audio_srt_context_html(content) -> str:
    try:
        if isinstance(content, str):
            content = json.loads(content)
        if isinstance(content, dict):
            entries = content.get("srt_lines") or []
            if not entries and content.get("text"):
                return html.escape(str(content.get("text", ""))).replace("\n", "<br>")
        else:
            entries = content or []

        lines = []
        for entry in entries:
            if isinstance(entry, dict):
                lines.append(
                    f"[{entry.get('start', 0):.2f}s - {entry.get('end', 0):.2f}s] "
                    f"{html.escape(str(entry.get('text', '')))}"
                )
            else:
                lines.append(html.escape(str(entry)))
        return "<br>".join(lines) or "<i>No transcript context saved.</i>"
    except Exception as exc:
        return f"<i>Error reading audio context: {html.escape(str(exc))}</i>"


def image_diagram_context_html(content) -> str:
    content = content if isinstance(content, dict) else {}
    image_path = content.get("image_path", "")
    image_filename = content.get("image_filename", "")
    text = html.escape(str(content.get("text", ""))).replace("\n", "<br>")
    parts = []
    image_source = ""
    if image_filename:
        image_source = get_local_media_path(str(image_filename)).resolve().as_uri()
    elif image_path:
        image_source = Path(str(image_path)).resolve().as_uri()
    if image_source:
        parts.append(
            f'<img src="{html.escape(image_source, quote=True)}" '
            'style="max-width:100%; height:auto; margin-bottom:10px;" />'
        )
    parts.append(text or "<i>No diagram image saved.</i>")
    return "<br>".join(parts)
