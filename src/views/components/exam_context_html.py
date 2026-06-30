import html
import json
import re
from pathlib import Path
from typing import Any

from src.models.exam import ExamContext
from src.utils.helpers import get_local_media_path


def _coerce_content(content: object) -> Any:
    if isinstance(content, str):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"text": content}
    if isinstance(content, dict):
        return content
    if hasattr(content, "model_dump"):
        return content.model_dump()
    if hasattr(content, "dict"):
        return content.dict()
    return content


def _content_get(content: object, key: str, default: object = "") -> object:
    content = _coerce_content(content)
    if isinstance(content, dict):
        return content.get(key, default)
    return getattr(content, key, default)


def context_content_html(ctx: ExamContext) -> str:
    content = _coerce_content(ctx.content)
    if ctx.context_type == "AUDIO_SRT":
        return audio_srt_context_html(content)
    if ctx.context_type == "IMAGE_DIAGRAM":
        return image_diagram_context_html(content)

    raw = str(_content_get(content, "text", content or ""))
    safe = html.escape(raw)

    def replace_placeholder(match: re.Match[str]) -> str:
        num = match.group(1)
        return (
            f'<a href="{num}" style="text-decoration:none; color:#0078d4;">'
            f"({num}) ________</a>"
        )

    safe = re.sub(r"\[\[(\d+)\]\]", replace_placeholder, safe)
    return safe.replace("\n", "<br>") or ""


def audio_srt_context_html(content: object) -> str:
    try:
        content = _coerce_content(content)
        if isinstance(content, dict):
            entries = content.get("srt_lines") or []
            if not entries and content.get("text"):
                return html.escape(str(content.get("text", ""))).replace("\n", "<br>")
        else:
            entries = content or []

        lines: list[str] = []
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


def image_diagram_context_html(content: object) -> str:
    content = _coerce_content(content)
    image_path = _content_get(content, "image_path", "")
    image_filename = _content_get(content, "image_filename", "")
    text = html.escape(str(_content_get(content, "text", ""))).replace("\n", "<br>")
    parts: list[str] = []
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
