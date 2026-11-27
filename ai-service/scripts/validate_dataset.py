"""Dataset validator for FarmSathi and NyayaSathi PDFs + sidecar JSONs.

Checks every PDF in FARMSATHI_DATA_PATH and NYAYASATHI_DATA_PATH (ignoring files
whose names start with ``_``):
  1. Sibling ``<stem>.json`` sidecar exists and is valid JSON.
  2. Required fields (§4.3 for FarmSathi, §5.3 for NyayaSathi) are present and non-empty.
  3. ``url`` starts with ``https://``.
  4. Date fields are valid ISO-8601 dates (``YYYY-MM-DD``).
  5. Extracted PDF text is at least 50 chars and not garbled (<= 5% replacement
     or non-printable control characters).

Usage (from ai-service/):
    .venv/Scripts/python.exe scripts/validate_dataset.py
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

_AI_SERVICE_ROOT = Path(__file__).resolve().parent.parent
if str(_AI_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_AI_SERVICE_ROOT))

from app.core.config import get_settings
from app.services.ingestion_utils import extract_text_from_pdf

MIN_TEXT_LENGTH = 50
MAX_GARBLED_RATIO = 0.05

FARMSATHI_REQUIRED = (
    "source_title",
    "publisher",
    "url",
    "topic",
    "language",
    "retrieval_date",
)
FARMSATHI_DATES = ("published_date", "retrieval_date")

NYAYASATHI_REQUIRED = (
    "document_title",
    "issuing_authority",
    "url",
    "jurisdiction",
    "act_name",
    "retrieval_date",
)
NYAYASATHI_DATES = ("publication_date", "effective_date", "last_updated_date", "retrieval_date")


def _is_valid_iso_date(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        date.fromisoformat(value.strip())
        return True
    except ValueError:
        return False


def _garbled_ratio(text: str) -> float:
    if not text:
        return 1.0
    bad = sum(
        1
        for ch in text
        if ch == "\ufffd" or (ord(ch) < 32 and ch not in ("\n", "\r", "\t"))
    )
    return bad / len(text)


def validate_pdf(pdf_path: Path, module: str) -> list[str]:
    """Return a list of validation error strings for *pdf_path* (empty = PASS)."""
    errors: list[str] = []
    sidecar = pdf_path.with_suffix(".json")

    if not sidecar.exists():
        errors.append(f"Missing sidecar JSON: {sidecar.name}")
        return errors

    try:
        meta = json.loads(sidecar.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"Invalid JSON in {sidecar.name}: {exc}")
        return errors

    required = FARMSATHI_REQUIRED if module == "farmsathi" else NYAYASATHI_REQUIRED
    date_fields = FARMSATHI_DATES if module == "farmsathi" else NYAYASATHI_DATES

    for field in required:
        val = meta.get(field)
        if not isinstance(val, str) or not val.strip():
            errors.append(f"Missing or empty required field '{field}'")

    if module == "nyayasathi":
        jur = str(meta.get("jurisdiction", "")).strip().lower()
        if jur not in ("central", "state"):
            errors.append("Field 'jurisdiction' must be 'central' or 'state'")
        if jur == "state" and not str(meta.get("applicable_state", "")).strip():
            errors.append("Field 'applicable_state' is required when jurisdiction='state'")

    url = str(meta.get("url", "")).strip()
    if url and not url.startswith("https://"):
        errors.append(f"Field 'url' must start with 'https://' (got '{url}')")

    for df in date_fields:
        if df in meta and meta[df] not in (None, ""):
            if not _is_valid_iso_date(meta[df]):
                errors.append(f"Field '{df}' is not a valid ISO date (YYYY-MM-DD): '{meta[df]}'")

    try:
        text = extract_text_from_pdf(pdf_path).strip()
    except Exception as exc:
        errors.append(f"PDF text extraction failed: {exc}")
        return errors

    if len(text) < MIN_TEXT_LENGTH:
        errors.append(f"Extracted text too short ({len(text)} chars < {MIN_TEXT_LENGTH})")
    else:
        ratio = _garbled_ratio(text)
        if ratio > MAX_GARBLED_RATIO:
            errors.append(f"Extracted text appears garbled ({ratio:.1%} invalid/replacement chars)")

    return errors


def validate_folder(folder: Path, module: str) -> tuple[int, int]:
    """Validate all non-underscore PDFs in *folder*. Returns (passed, failed)."""
    print(f"\n=== Validating {module} ({folder}) ===")
    if not folder.exists():
        print("  [INFO] Folder does not exist — 0 files checked.")
        return 0, 0

    pdfs = [p for p in sorted(folder.glob("*.pdf")) if not p.name.startswith("_")]
    if not pdfs:
        print("  [INFO] No PDFs found — 0 files checked.")
        return 0, 0

    passed = 0
    failed = 0
    for pdf in pdfs:
        errs = validate_pdf(pdf, module)
        if errs:
            failed += 1
            print(f"  [FAIL] {pdf.name}")
            for e in errs:
                print(f"         - {e}")
        else:
            passed += 1
            print(f"  [PASS] {pdf.name}")

    return passed, failed


def main() -> int:
    settings = get_settings()
    base = _AI_SERVICE_ROOT
    farm_dir = (base / settings.farmsathi_data_path).resolve()
    nyaya_dir = (base / settings.nyayasathi_data_path).resolve()

    p1, f1 = validate_folder(farm_dir, "farmsathi")
    p2, f2 = validate_folder(nyaya_dir, "nyayasathi")

    total_passed = p1 + p2
    total_failed = f1 + f2
    print(f"\nSummary: {total_passed} passed, {total_failed} failed.")
    return 1 if total_failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
