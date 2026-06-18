# ─────────────────────────────────────────────────────────────────────────────
# Helper: extract audio timestamps from additional_meta JSON
# ─────────────────────────────────────────────────────────────────────────────
def get_audio_meta(question):
    """Return (audio_start_seconds, audio_end_seconds) from additional_meta."""
    meta = question.additional_meta or {}
    return float(meta.get("audio_start", 0.0)), float(meta.get("audio_end", 0.0))