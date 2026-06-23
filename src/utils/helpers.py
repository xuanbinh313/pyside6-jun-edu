# ─────────────────────────────────────────────────────────────────────────────
# Helper: extract audio timestamps from additional_meta JSON
# ─────────────────────────────────────────────────────────────────────────────
import base64
import html
import mimetypes
import re
import tempfile
from pathlib import Path
from urllib.parse import unquote

from slugify import slugify


def get_audio_meta(question):
    """Return (audio_start_seconds, audio_end_seconds) from additional_meta."""
    if not question:
        return 0.0, 0.0
    context = getattr(question, "context", None)
    if context:
        meta = context.additional_meta or {}
        audio_start = _meta_float(meta, "audio_start")
        audio_end = _meta_float(meta, "audio_end")
        if audio_start > 0.0 or audio_end > 0.0:
            return audio_start, audio_end
    meta = question.additional_meta or {}
    return _meta_float(meta, "audio_start"), _meta_float(meta, "audio_end")


def _meta_float(meta, key):
    try:
        return float(meta.get(key, 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def extract_plain_text(content: str) -> str:
    """Remove HTML tags and decode entities from user/imported content."""
    if not content:
        return ""
    without_tags = re.sub(r"<[^>]*>", " ", content)
    decoded = html.unescape(without_tags)
    return re.sub(r"\s+", " ", decoded).strip()


def get_valid_name(filename: str) -> str:
    """Return a lowercase slugified filename while preserving its extension."""
    raw_name = Path((filename or "media")).name
    stem = Path(raw_name).stem
    suffix = Path(raw_name).suffix.lower()
    valid_stem = slugify(extract_plain_text(stem), separator="-").lower()
    if not valid_stem:
        valid_stem = "media"
    return f"{valid_stem}{suffix}"


def get_local_media_dir() -> Path:
    media_dir = Path(tempfile.gettempdir()) / "jun_edu_media"
    media_dir.mkdir(parents=True, exist_ok=True)
    return media_dir


def get_local_media_path(filename: str) -> Path:
    return get_local_media_dir() / get_valid_name(filename)


def unique_media_filename(filename: str) -> str:
    valid_name = get_valid_name(filename)
    candidate = valid_name
    counter = 1
    media_dir = get_local_media_dir()
    path = media_dir / candidate
    stem = Path(valid_name).stem
    suffix = Path(valid_name).suffix
    while path.exists():
        candidate = f"{stem}-{counter}{suffix}"
        path = media_dir / candidate
        counter += 1
    return candidate


def extension_from_data_url(data_url: str) -> str:
    match = re.match(r"data:([^;,]+)", data_url or "")
    if not match:
        return ".bin"
    return mimetypes.guess_extension(match.group(1)) or ".bin"


def decode_data_url(data_url: str) -> bytes:
    header, separator, payload = data_url.partition(",")
    if not separator:
        raise ValueError("Invalid data URL.")
    if ";base64" in header:
        return base64.b64decode(payload)
    return unquote(payload).encode("utf-8")
