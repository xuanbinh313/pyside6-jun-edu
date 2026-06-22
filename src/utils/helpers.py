# ─────────────────────────────────────────────────────────────────────────────
# Helper: extract audio timestamps from additional_meta JSON
# ─────────────────────────────────────────────────────────────────────────────
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
