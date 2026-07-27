"""Out-of-process Agent worker.

Protocol: read one JSON object per line from stdin and write one JSON object per
line to stdout. Heavy Agent dependencies are imported here, not by JunEdu.exe.
"""

from __future__ import annotations

import json
import mimetypes
import sys
from pathlib import Path
from typing import Any, Mapping


def generate_content(payload: Mapping[str, Any]) -> dict[str, Any]:
    api_key = str(payload.get("api_key") or "").strip()
    model_name = str(payload.get("model_name") or "gemini-2.5-flash").strip()
    prompt_text = str(payload.get("prompt_text") or "").strip()
    file_paths = _string_list(payload.get("file_paths"))
    temperature = _float_value(payload.get("temperature"), 0.1)
    thinking_budget = _int_value(payload.get("thinking_budget"), 0)

    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing from application config.")
    if not prompt_text:
        raise ValueError("Agent prompt text is empty.")

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise ImportError(
            "google-genai is required in the Agent worker environment."
        ) from exc

    client = genai.Client(api_key=api_key)
    parts: list[Any] = [prompt_text]
    for file_path in file_paths:
        uploaded_file = client.files.upload(file=file_path)
        file_uri = str(getattr(uploaded_file, "uri", "") or "").strip()
        mime_type = str(getattr(uploaded_file, "mime_type", "") or "").strip()
        if not mime_type:
            guessed_mime_type, _ = mimetypes.guess_type(file_path)
            mime_type = guessed_mime_type or "application/octet-stream"
        if not file_uri:
            raise ValueError(f"Agent worker could not upload file: {file_path}")
        parts.append(types.Part.from_uri(file_uri=file_uri, mime_type=mime_type))

    response = client.models.generate_content(
        model=model_name,
        contents=parts,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=temperature,
            thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget),
        ),
    )
    return {
        "text": _response_text(response),
        "response_text": _response_text_from_parts(response),
        "candidates": _dump_response_candidates(response),
        "response": {
            "model_version": _json_safe(getattr(response, "model_version", None)),
            "usage_metadata": _json_safe(getattr(response, "usage_metadata", None)),
        },
    }


def handle_request(request: Mapping[str, Any]) -> Any:
    method = request.get("method")
    payload = request.get("payload", {})
    if not isinstance(payload, Mapping):
        raise ValueError("Worker payload must be a JSON object.")
    if method == "generate_content":
        return generate_content(payload)
    raise ValueError(f"Unknown worker method: {method}")


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _float_value(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int_value(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _response_text(response: Any) -> str:
    text = _response_text_from_parts(response)
    if text:
        return text
    direct_text = getattr(response, "text", "")
    if direct_text:
        return str(direct_text).strip()
    return ""


def _response_text_from_parts(response: Any) -> str:
    candidates = getattr(response, "candidates", None) or []
    chunks: list[str] = []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", []) or []:
            part_text = getattr(part, "text", "")
            if part_text:
                chunks.append(str(part_text))
    return "\n".join(chunks).strip()


def _dump_response_candidates(response: Any) -> list[dict[str, Any]]:
    candidates = getattr(response, "candidates", None) or []
    dumped_candidates: list[dict[str, Any]] = []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        dumped_parts = [
            _dump_response_part(part) for part in getattr(content, "parts", []) or []
        ]
        dumped_candidates.append(
            {
                "finish_reason": _json_safe(getattr(candidate, "finish_reason", None)),
                "content_role": getattr(content, "role", None),
                "parts": dumped_parts,
            }
        )
    return dumped_candidates


def _dump_response_part(part: Any) -> dict[str, Any]:
    fields = (
        "text",
        "thought",
        "thought_signature",
        "inline_data",
        "file_data",
        "function_call",
        "function_response",
        "executable_code",
        "code_execution_result",
    )
    return {
        field: _json_safe(getattr(part, field))
        for field in fields
        if hasattr(part, field) and getattr(part, field) is not None
    }


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(nested) for key, nested in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return _json_safe(model_dump())
        except Exception:
            pass
    to_json_dict = getattr(value, "to_json_dict", None)
    if callable(to_json_dict):
        try:
            return _json_safe(to_json_dict())
        except Exception:
            pass
    return repr(value)


def _write_response(response: Mapping[str, Any]) -> None:
    sys.stdout.write(json.dumps(dict(response), ensure_ascii=True) + "\n")
    sys.stdout.flush()


def _configure_stdio() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def main() -> None:
    _configure_stdio()
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if not isinstance(request, Mapping):
                raise ValueError("Worker request must be a JSON object.")
            result = handle_request(request)
            _write_response({"ok": True, "result": result})
        except Exception as exc:
            _write_response({"ok": False, "error": str(exc)})


if __name__ == "__main__":
    main()
