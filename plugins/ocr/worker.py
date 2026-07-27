"""Out-of-process OCR worker.

Protocol: read one JSON object per line from stdin and write one JSON object per
line to stdout. Heavy OCR dependencies are imported here, not by JunEdu.exe.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping, Optional


def extract_task_text(payload: Mapping[str, Any]) -> str:
    parts = payload.get("parts", [])
    if not isinstance(parts, list):
        raise ValueError("OCR payload field 'parts' must be a list.")

    tmp_dir_value = payload.get("tmp_dir", "")
    tmp_dir = Path(str(tmp_dir_value)) if tmp_dir_value else Path.cwd()
    sections: list[str] = []
    for raw_part in parts:
        if not isinstance(raw_part, Mapping):
            continue
        part_number = _part_number(raw_part)
        part_text = _extract_ocr_text_for_part(raw_part, tmp_dir)
        if part_text.strip():
            sections.append(
                f"TOEIC Part {part_number} PaddleOCR text:\n{part_text.strip()}"
            )
    if not sections:
        raise ValueError("PaddleOCR did not extract text from this request.")
    return "\n\n".join(sections)


def handle_request(request: Mapping[str, Any]) -> Any:
    method = request.get("method")
    payload = request.get("payload", {})
    if not isinstance(payload, Mapping):
        raise ValueError("Worker payload must be a JSON object.")
    if method == "extract_task_text":
        return extract_task_text(payload)
    raise ValueError(f"Unknown worker method: {method}")


def _extract_ocr_text_for_part(payload: Mapping[str, Any], tmp_dir: Path) -> str:
    part = _part_number(payload)
    question_pdf_path = str(payload.get("question_pdf_path") or "")
    question_pages = _page_indices(payload.get("question_pages"))
    transcript_pdf_path = str(payload.get("transcript_pdf_path") or "")
    transcript_pages = _page_indices(payload.get("transcript_pages"))

    lane_texts: list[str] = []
    if part != 2 and question_pdf_path and question_pages:
        question_text = _extract_ocr_text_from_pdf_pages(
            question_pdf_path,
            question_pages,
            tmp_dir / f"ocr_part_{part}_questions",
        )
        if question_text.strip():
            lane_texts.append(f"Question pages:\n{question_text.strip()}")
    if transcript_pdf_path and transcript_pages:
        transcript_text = _extract_ocr_text_from_pdf_pages(
            transcript_pdf_path,
            transcript_pages,
            tmp_dir / f"ocr_part_{part}_transcripts",
        )
        if transcript_text.strip():
            lane_texts.append(f"Transcript pages:\n{transcript_text.strip()}")
    return "\n\n".join(lane_texts)


def _extract_ocr_text_from_pdf_pages(
    pdf_path: str, page_indices: list[int], output_dir: Path
) -> str:
    try:
        import fitz
    except ImportError as exc:
        raise ImportError("PyMuPDF is required to render PDF pages for PaddleOCR.") from exc

    os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "0")
    try:
        from paddleocr import PaddleOCR
    except ImportError as exc:
        raise ImportError(
            "PaddleOCR is required in the OCR worker environment."
        ) from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    ocr = _create_paddle_ocr(PaddleOCR)
    page_texts: list[str] = []
    with fitz.open(str(pdf_path)) as document:
        for page_index in sorted(set(page_indices)):
            if page_index < 0 or page_index >= len(document):
                raise ValueError(
                    f"Page {page_index + 1} is outside {Path(pdf_path).name}."
                )
            page = document[page_index]
            image_path = output_dir / f"page_{page_index + 1}.png"
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            pixmap.save(str(image_path))
            lines = _ocr_image_text(ocr, image_path)
            if lines:
                page_texts.append(f"Page {page_index + 1}:\n" + "\n".join(lines))
    return "\n\n".join(page_texts)


def _ocr_image_text(ocr: Any, image_path: Path) -> list[str]:
    try:
        result = ocr.predict(str(image_path))
    except AttributeError:
        try:
            result = ocr.ocr(str(image_path), cls=True)
        except TypeError:
            result = ocr.ocr(str(image_path))
    lines: list[str] = []
    _collect_ocr_lines(result, lines)
    return lines


def _create_paddle_ocr(paddle_ocr_class: Any) -> Any:
    os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "0")
    last_error: Optional[Exception] = None
    for kwargs in (
        {
            "lang": "en",
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
        },
        {"lang": "en", "use_textline_orientation": True},
        {"lang": "en"},
        {"use_angle_cls": True, "lang": "en"},
        {},
    ):
        try:
            return paddle_ocr_class(**kwargs)
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError(
        "Could not initialize PaddleOCR. Check that paddleocr and paddlepaddle "
        "are installed correctly in the OCR worker environment."
    ) from last_error


def _collect_ocr_lines(value: Any, lines: list[str]) -> None:
    if value is None:
        return
    if isinstance(value, dict):
        for key in ("text", "rec_text", "transcription"):
            text = value.get(key)
            if isinstance(text, str) and text.strip():
                lines.append(text.strip())
        rec_texts = value.get("rec_texts")
        if isinstance(rec_texts, list):
            lines.extend(
                text.strip()
                for text in rec_texts
                if isinstance(text, str) and text.strip()
            )
        for key, nested in value.items():
            if key == "rec_texts":
                continue
            _collect_ocr_lines(nested, lines)
        return
    if isinstance(value, (list, tuple)):
        if value and all(isinstance(item, str) for item in value):
            lines.extend(item.strip() for item in value if item.strip())
            return
        if len(value) >= 2 and isinstance(value[1], (list, tuple)):
            text_candidate = value[1][0] if value[1] else ""
            if isinstance(text_candidate, str) and text_candidate.strip():
                lines.append(text_candidate.strip())
                return
        for nested in value:
            _collect_ocr_lines(nested, lines)


def _part_number(payload: Mapping[str, Any]) -> int:
    try:
        return int(payload.get("part") or 0)
    except (TypeError, ValueError):
        return 0


def _page_indices(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    indices: list[int] = []
    for item in value:
        try:
            indices.append(int(item))
        except (TypeError, ValueError):
            continue
    return indices


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
