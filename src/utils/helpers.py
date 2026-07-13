# ─────────────────────────────────────────────────────────────────────────────
# Helper: extract audio timestamps from additional_meta JSON
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import base64
import html
import mimetypes
import re
import shutil
from pathlib import Path
from typing import Any, Optional
from urllib.parse import unquote
from urllib.request import Request, urlopen

from platformdirs import user_data_dir
from slugify import slugify
from src.models.exam import ExamQuestion


def get_audio_meta(question: Optional[ExamQuestion]) -> tuple[float, float]:
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


def _meta_float(meta: Any, key: str) -> float:
    try:
        if isinstance(meta, dict):
            value = meta.get(key, 0.0)
        elif hasattr(meta, "model_dump"):
            dumped = meta.model_dump()
            value = dumped.get(key, 0.0) if isinstance(dumped, dict) else 0.0
        else:
            value = getattr(meta, key, 0.0)
        return float(value or 0.0)
    except (AttributeError, TypeError, ValueError):
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
    media_dir = Path(user_data_dir("jun-toeic", appauthor=False, roaming=True))
    media_dir.mkdir(parents=True, exist_ok=True)
    return media_dir


def get_local_media_path(filename: str) -> Path:
    return get_local_media_dir() / get_valid_name(filename)


def is_local_media_path(path: str | Path) -> bool:
    try:
        return Path(path).resolve().parent == get_local_media_dir().resolve()
    except (OSError, RuntimeError):
        return False


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


def local_media_filename_from_source(
    source: str | Path, filename: str | None = None
) -> str:
    """Copy or download an audio source into local media and return its filename."""
    source_text = str(source or "").strip()
    if not source_text:
        return ""

    if re.match(r"^https?://", source_text, flags=re.IGNORECASE):
        guessed_name = filename or Path(source_text.split("?", 1)[0]).name or "audio"
        unique_filename = unique_media_filename(guessed_name)
        target_path = get_local_media_path(unique_filename)
        request = Request(source_text, headers={"User-Agent": "JunEdu/1.0"})
        with urlopen(request, timeout=60) as response:
            target_path.write_bytes(response.read())
        return unique_filename

    local_path = Path(source_text)
    if not local_path.is_absolute() and not local_path.exists():
        media_path = get_local_media_path(source_text)
        if media_path.exists():
            return get_valid_name(source_text)

    if not local_path.is_file():
        raise ValueError(f"Audio file does not exist: {local_path}")

    if is_local_media_path(local_path):
        return get_valid_name(local_path.name)

    unique_filename = unique_media_filename(filename or local_path.name)
    shutil.copy2(local_path, get_local_media_path(unique_filename))
    return unique_filename


def optimize_image_to_webp_file(
    source_path: str | Path, filename: str | None = None
) -> str:
    """Optimize an image into the local temp media folder and return its filename."""
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise ValueError(
            "Pillow is required to optimize diagram images. Please install requirements.txt."
        ) from exc

    source = Path(source_path)
    if not source.is_file():
        raise ValueError(f"Image file does not exist: {source}")

    output_name = filename or f"{source.stem}.webp"
    output_path = Path(output_name)
    output_name = f"{output_path.stem}.webp"
    unique_filename = unique_media_filename(output_name)
    target_path = get_local_media_path(unique_filename)

    try:
        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image)
            if max(image.size) > 1800:
                image.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
            image.save(target_path, format="WEBP", quality=90, method=6)
    except Exception as exc:
        raise ValueError(f"Could not optimize image: {exc}") from exc

    return unique_filename


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
