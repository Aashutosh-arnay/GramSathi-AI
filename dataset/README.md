# GramSathi AI Knowledge Base Dataset

This directory holds the verified source PDFs and metadata sidecars ingested by `ai-service/`.

## Rules

1. **Official sources only**: Only add documents from verified government, ICAR/KVK, India Code, e-Gazette, NALSA/SLSA, or court portals.
2. **One sidecar per PDF**: Every `<name>.pdf` must have a sibling `<name>.json` sidecar. Start from `_template.json` in `farmsathi/` or `nyayasathi/`. Files starting with `_` (like `_template.json`) are ignored during validation and ingestion.
3. **Never commit invented content**: Do not place synthetic, unverified, or test-fixture PDFs here (test fixtures belong in `ai-service/tests/fixtures/`).

## Validate Before Ingesting

From `ai-service/`:

```powershell
.venv\Scripts\python.exe scripts\validate_dataset.py
```

The validator checks that every PDF has a sidecar, all required §4.3 / §5.3 fields are non-empty, URLs start with `https://`, dates are valid ISO-8601 (`YYYY-MM-DD`), and extracted PDF text is readable.

## Ingest / Rebuild Vector Store

From `ai-service/`:

```powershell
# FarmSathi
.venv\Scripts\python.exe -m app.farmsathi.ingest --rebuild

# NyayaSathi
.venv\Scripts\python.exe -m app.nyayasathi.ingest --rebuild
```

Use `--rebuild` whenever documents are updated or removed so stale chunks are dropped before re-ingesting.
