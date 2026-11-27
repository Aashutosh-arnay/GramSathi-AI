"""Phase E evaluation harness for FarmSathi AI and NyayaSathi AI.

Runs eval/questions_farmsathi.json and eval/questions_nyayasathi.json in-process
(no HTTP server needed), writes Markdown and JSON reports under eval/results/,
and optionally runs retrieval threshold tuning.

Usage (from ai-service/):
    .venv/Scripts/python.exe scripts/run_eval.py --provider mock
    .venv/Scripts/python.exe scripts/run_eval.py --provider mock --threshold-tuning
    .venv/Scripts/python.exe scripts/run_eval.py --provider gemini --module farmsathi
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_AI_SERVICE_ROOT = Path(__file__).resolve().parent.parent
if str(_AI_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_AI_SERVICE_ROOT))


def _configure_provider(provider: str, threshold: float | None = None) -> None:
    """Force the selected LLM provider without printing .env or secrets."""
    os.environ["LLM_PROVIDER"] = provider
    if threshold is not None:
        os.environ["RETRIEVAL_THRESHOLD"] = str(threshold)
    from app.core.config import get_settings
    from app.services.llm_service import get_llm_service

    get_settings.cache_clear()
    get_llm_service.cache_clear()


def _probe_raw_scores(
    module: str,
    question: str,
    state: str | None,
) -> list[dict[str, Any]]:
    """Query Chroma with threshold=0.0 to inspect raw top-k similarity scores."""
    from app.core.config import get_settings
    from app.farmsathi.knowledge_base import get_farmsathi_collection
    from app.nyayasathi.knowledge_base import get_nyayasathi_collection
    from app.nyayasathi.service import _build_jurisdiction_filter
    from app.services.embedding_service import get_embedding_service
    from app.services.retrieval_service import RetrievalService

    settings = get_settings()
    emb = get_embedding_service()
    if module == "farmsathi":
        col = get_farmsathi_collection(settings.chroma_persist_dir, id(emb))
        where = None
    else:
        col = get_nyayasathi_collection(settings.chroma_persist_dir, id(emb))
        where = _build_jurisdiction_filter(state)

    svc = RetrievalService(collection=col, threshold=0.0, top_k=settings.retrieval_top_k)
    chunks = svc.search(question, where=where)
    return [
        {
            "score": round(c.score, 4),
            "source_file": (c.metadata or {}).get("source_file", ""),
            "title": c.source_title,
        }
        for c in chunks
    ]


def _evaluate_items(
    module: str,
    items: list[dict[str, Any]],
    provider: str,
) -> list[dict[str, Any]]:
    from app.core.exceptions import AIServiceError
    from app.farmsathi.service import process_farmsathi_chat
    from app.nyayasathi.service import process_nyayasathi_chat
    from app.schemas.chat_schema import (
        FarmSathiChatRequest,
        FarmSathiContext,
        NyayaSathiChatRequest,
        NyayaSathiContext,
    )

    results: list[dict[str, Any]] = []

    for idx, item in enumerate(items):
        qid = item["id"]
        lang = item.get("language", "en")
        question = item["question"]
        ctx = item.get("context") or {}
        category = item["category"]
        expected_status = item["expected_status"]
        expected_files = item.get("expected_source_files") or []

        raw_scores = _probe_raw_scores(module, question, ctx.get("state"))

        from app.core.exceptions import AIServiceError

        error_info: str | None = None
        if module == "farmsathi":
            req = FarmSathiChatRequest(
                requestId=f"eval-{qid}",
                conversationId="eval-conv",
                message=question,
                language=lang,
                history=[],
                context=FarmSathiContext(**ctx),
                attachments=[],
            )
            try:
                resp = process_farmsathi_chat(req)
            except AIServiceError as exc:
                error_info = f"{exc.code}: {exc.message}"
                resp = None
            disclaimer_present = None
        else:
            req = NyayaSathiChatRequest(
                requestId=f"eval-{qid}",
                conversationId="eval-conv",
                message=question,
                language=lang,
                history=[],
                context=NyayaSathiContext(**ctx),
                attachments=[],
            )
            try:
                resp = process_nyayasathi_chat(req)
            except AIServiceError as exc:
                error_info = f"{exc.code}: {exc.message}"
                resp = None
            disclaimer_present = bool(resp and resp.disclaimer and resp.disclaimer.strip())

        if provider == "gemini" and idx < len(items) - 1:
            time.sleep(1.5)

        if resp is None:
            results.append(
                {
                    "id": qid,
                    "module": module,
                    "category": category,
                    "language": lang,
                    "question": question,
                    "expected_status": expected_status,
                    "answerStatus": f"error:{error_info.split(':', 1)[0]}" if error_info else "error",
                    "status_pass": False,
                    "expected_source_files": expected_files,
                    "sources_match": False,
                    "retrieved_sources": [],
                    "top_retrieval_scores": raw_scores[:3],
                    "disclaimer_present": disclaimer_present,
                    "answer": error_info or "LLM error",
                }
            )
            continue

        actual_status = resp.answerStatus.value
        status_pass = actual_status == expected_status

        retrieved_urls = [s.url for s in resp.sources]
        retrieved_titles = [s.title for s in resp.sources]

        # Check expected_source_files against raw retrieved chunks when supported
        if not expected_files:
            sources_match = True
        else:
            returned_set = {
                r["source_file"]
                for r in raw_scores
                if any(s.url and r["title"] in s.title for s in resp.sources)
            }
            # Fallback: also match if any retrieved source file is in expected_files
            top_files = {r["source_file"] for r in raw_scores}
            sources_match = any(ef in returned_set or ef in top_files for ef in expected_files) and bool(resp.sources)

        results.append(
            {
                "id": qid,
                "module": module,
                "category": category,
                "language": lang,
                "question": question,
                "expected_status": expected_status,
                "answerStatus": actual_status,
                "status_pass": status_pass,
                "expected_source_files": expected_files,
                "sources_match": sources_match,
                "retrieved_sources": [
                    {"title": t, "url": u} for t, u in zip(retrieved_titles, retrieved_urls)
                ],
                "top_retrieval_scores": raw_scores[:3],
                "disclaimer_present": disclaimer_present,
                "answer": resp.answer,
            }
        )

    return results


def _print_threshold_tuning(results: list[dict[str, Any]]) -> None:
    print("\n================ THRESHOLD TUNING REPORT ================")
    for module in sorted({r["module"] for r in results}):
        mod_rows = [r for r in results if r["module"] == module]
        in_scope = [
            r["top_retrieval_scores"][0]["score"]
            for r in mod_rows
            if r["expected_status"] == "supported" and r["top_retrieval_scores"]
        ]
        out_scope = [
            r["top_retrieval_scores"][0]["score"]
            for r in mod_rows
            if r["expected_status"] == "insufficient_information" and r["top_retrieval_scores"]
        ]
        print(f"\nModule: {module}")
        if in_scope:
            print(
                f"  In-scope (supported, n={len(in_scope)}): "
                f"min={min(in_scope):.4f}  median={statistics.median(in_scope):.4f}  max={max(in_scope):.4f}"
            )
        if out_scope:
            print(
                f"  No-source / OOS / Trap (n={len(out_scope)}): "
                f"min={min(out_scope):.4f}  median={statistics.median(out_scope):.4f}  max={max(out_scope):.4f}"
            )
        if in_scope and out_scope:
            low_in = min(in_scope)
            high_out = max(out_scope)
            if low_in > high_out:
                rec = round((low_in + high_out) / 2, 2)
                print(f"  -> Clean separation! Recommended RETRIEVAL_THRESHOLD: {rec:.2f} (gap: {high_out:.4f} .. {low_in:.4f})")
            else:
                # Suggest midpoint between 25th percentile of in_scope and 75th percentile of out_scope
                rec = round((statistics.median(in_scope) + statistics.median(out_scope)) / 2, 2)
                print(
                    f"  -> Distributions overlap ({high_out:.4f} >= {low_in:.4f}). "
                    f"Suggested midpoint RETRIEVAL_THRESHOLD: {rec:.2f} (not applied automatically)."
                )


def _write_reports(
    results: list[dict[str, Any]],
    provider: str,
    out_dir: Path,
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"{ts}.json"
    md_path = out_dir / f"{ts}.md"

    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# GramSathi AI Evaluation Report ({ts} UTC)",
        "",
        f"- **Provider:** `{provider}`",
        f"- **Total questions:** {len(results)}",
        f"- **Status passed:** {sum(1 for r in results if r['status_pass'])}/{len(results)}",
        "",
        "## Hallucination-Trap Failures",
        "",
    ]
    trap_fails = [
        r for r in results if r["category"] == "hallucination_trap" and not r["status_pass"]
    ]
    if not trap_fails:
        lines.append("None (all hallucination traps passed).")
    else:
        for r in trap_fails:
            lines.append(
                f"- **{r['id']}** ({r['module']}): expected `{r['expected_status']}`, got `{r['answerStatus']}` — {r['question']}"
            )

    lines.extend(["", "## Pass Rate by Module & Category", "", "| Module | Category | Passed | Total | Rate |", "|---|---|---|---|---|"])
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in results:
        grouped[(r["module"], r["category"])].append(r)
    for (mod, cat), rows in sorted(grouped.items()):
        p = sum(1 for x in rows if x["status_pass"])
        t = len(rows)
        lines.append(f"| {mod} | {cat} | {p} | {t} | {p/t:.0%} |")

    lines.extend(["", "## Detailed Results", ""])
    for r in results:
        badge = "PASS" if r["status_pass"] else "FAIL"
        top_score = r["top_retrieval_scores"][0]["score"] if r["top_retrieval_scores"] else 0.0
        lines.extend([
            f"### {r['id']} [{badge}] ({r['module']} / {r['category']} / `{r['language']}`)",
            f"- **Question:** {r['question']}",
            f"- **Expected:** `{r['expected_status']}` | **Actual:** `{r['answerStatus']}` | **Top score:** `{top_score:.4f}` | **Sources match:** `{r['sources_match']}`",
        ])
        if r["module"] == "nyayasathi":
            lines.append(f"- **Disclaimer present:** `{r['disclaimer_present']}`")
        if r["retrieved_sources"]:
            src_str = "; ".join(f"{s['title']} ({s['url']})" for s in r["retrieved_sources"])
            lines.append(f"- **Retrieved sources:** {src_str}")
        else:
            lines.append("- **Retrieved sources:** (none)")
        lines.extend(["", "**Answer:**", "", r["answer"], ""])

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase E evaluation harness.")
    parser.add_argument("--provider", choices=["mock", "gemini"], default="mock")
    parser.add_argument("--module", choices=["farmsathi", "nyayasathi", "all"], default="all")
    parser.add_argument("--set", dest="eval_set", choices=["main", "holdout", "guards"], default="main")
    parser.add_argument("--threshold", type=float, default=None, help="Override RETRIEVAL_THRESHOLD for this run.")
    parser.add_argument("--threshold-tuning", action="store_true")
    args = parser.parse_args()

    _configure_provider(args.provider, threshold=args.threshold)

    eval_dir = _AI_SERVICE_ROOT / "eval"
    results: list[dict[str, Any]] = []
    if args.eval_set == "guards":
        guard_items = json.loads((eval_dir / "guards_regression.json").read_text(encoding="utf-8"))
        for mod in ("farmsathi", "nyayasathi"):
            if args.module in (mod, "all"):
                mod_items = [it for it in guard_items if it["module"] == mod]
                if mod_items:
                    results.extend(_evaluate_items(mod, mod_items, args.provider))
    else:
        prefix = "questions" if args.eval_set == "main" else "holdout"
        if args.module in ("farmsathi", "all"):
            items = json.loads((eval_dir / f"{prefix}_farmsathi.json").read_text(encoding="utf-8"))
            results.extend(_evaluate_items("farmsathi", items, args.provider))
        if args.module in ("nyayasathi", "all"):
            items = json.loads((eval_dir / f"{prefix}_nyayasathi.json").read_text(encoding="utf-8"))
            results.extend(_evaluate_items("nyayasathi", items, args.provider))

    json_path, md_path = _write_reports(results, f"{args.provider} ({args.eval_set})", eval_dir / "results")

    # ── Console Summary (hallucination traps FIRST) ─────────────────────────
    trap_fails = [
        r for r in results if r["category"] == "hallucination_trap" and not r["status_pass"]
    ]
    print("\n================ HALLUCINATION-TRAP FAILURES ================")
    if not trap_fails:
        print("  None (all hallucination traps passed).")
    else:
        for r in trap_fails:
            top_s = r["top_retrieval_scores"][0]["score"] if r["top_retrieval_scores"] else 0.0
            print(
                f"  [FAIL] {r['id']} ({r['module']}): expected={r['expected_status']} "
                f"got={r['answerStatus']} top_score={top_s:.4f} | {r['question']}"
            )

    print("\n================ PASS RATE BY CATEGORY ================")
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in results:
        grouped[(r["module"], r["category"])].append(r)
    for (mod, cat), rows in sorted(grouped.items()):
        p = sum(1 for x in rows if x["status_pass"])
        t = len(rows)
        print(f"  {mod:10s} | {cat:18s} | {p:2d}/{t:2d} ({p/t:4.0%})")

    total_pass = sum(1 for r in results if r["status_pass"])
    print(f"\nOverall status pass: {total_pass}/{len(results)} ({total_pass/len(results):.0%})")
    print(f"Reports written:\n  JSON: {json_path}\n  MD:   {md_path}")

    if args.threshold_tuning:
        _print_threshold_tuning(results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
