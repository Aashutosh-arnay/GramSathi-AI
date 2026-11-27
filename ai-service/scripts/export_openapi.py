"""Export the FastAPI OpenAPI schema to ai-service/docs/openapi.json.

Usage (from ai-service/):
    .venv/Scripts/python.exe scripts/export_openapi.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_AI_SERVICE_ROOT = Path(__file__).resolve().parent.parent
if str(_AI_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_AI_SERVICE_ROOT))

from app.main import app


def main() -> None:
    out_path = _AI_SERVICE_ROOT / "docs" / "openapi.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    schema = app.openapi()
    out_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"Exported OpenAPI schema to {out_path}")


if __name__ == "__main__":
    main()
