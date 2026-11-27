# GramSathi AI — Known Limitations (Phase E)

Updated after threshold tuning, guard false-positive auditing, holdout evaluation, and Gemini evaluation.

---

## 1. Retrieval Threshold (`RETRIEVAL_THRESHOLD=0.45`)

Comparison on the 50-question **main** set (`--provider mock`):

| Threshold | Main Overall | FarmSathi In-Scope (`basic`/`complex`/`bilingual`) | FarmSathi `out_of_scope` | NyayaSathi `no_source` |
|---|---|---|---|---|
| `0.30` | 47 / 50 (94%) | 12 / 12 (100%) | 1 / 3 (33%) | 3 / 4 (75%) |
| `0.45` *(new default)* | **49 / 50 (98%)** | **12 / 12 (100%)** | **3 / 3 (100%)** | 3 / 4 (75%) |
| `0.55` | 49 / 50 (98%) | 11 / 12 (92% — 1 bilingual Hindi query dropped) | 3 / 3 (100%) | 4 / 4 (100%) |

- **`0.45`** is set as the tentative default because it is safely below the lowest in-scope score (`0.4878`) while eliminating low-score out-of-scope false positives (`0.34–0.38`).
- On the 30-question **holdout** set at `0.45` (`--provider mock`), overall pass rate was **29 / 30 (97%)** (`15/15` NyayaSathi, `14/15` FarmSathi, `0` hallucination-trap failures).

## 2. Remaining Failure Modes

- **Semantic overlap with adjacent acts (`ns-17`):** *"What is the procedure for mutual consent divorce under the Hindu Marriage Act?"* retrieves `nalsa_widows_access_to_justice.pdf` (`0.5467`), which mentions marriage/widowhood background. Because the Hindu Marriage Act, 1955 is not in `dataset/nyayasathi/`, this is a **dataset coverage gap** rather than a retrieval-logic bug.
- **Subtle out-of-scope phrasing (`holdout` 1/2 FarmSathi OOS):** Occasionally an out-of-scope query without explicit anchor terms scores just above `0.45` against general scheme/guideline text.

## 3. Heuristic Guard Trade-offs

- **Pre-LLM / post-retrieval guards** (`_is_live_or_uncovered`, `_has_unverified_named_entity`, `_TOPIC_TERMS`, `_extract_asked_sections`) were audited against 20 real in-scope questions (`0/20` false positives after tightening regexes to require live/time qualifiers and whole-word boundaries).
- Novel phrasing in Hindi or regional dialects for uncovered domains can still bypass keyword guards and rely on `RETRIEVAL_THRESHOLD=0.45` plus the LLM system prompt.

## 4. Dataset Coverage & OCR

- **FarmSathi:** No PMFBY guidelines (`pmfby.gov.in` is a client-rendered SPA), no live weather (IMD) or mandi price APIs, and only PM-KISAN, NMSA-SHM, ICAR wheat/rice, and PPQS wheat/rice IPM are ingested.
- **NyayaSathi:** Central acts/regulations only (CP Act 2019, RTI Act 2005, Citizen's Charter, NALSA regulations/SOPs). No criminal codes (BNS/BNSS), family law, labour codes, or state-specific acts are ingested yet.
- **Scanned PDFs:** Image-only official PDFs with 0 extractable text characters are excluded (no OCR pipeline yet).

## 5. Gemini Rate Limits / Quota

- Bulk evaluation (`--provider gemini` on 50 questions) hit **Gemini API quota exhaustion (`HTTP 429` / `503`)** on the configured free-tier key, preventing a full 8-answers-per-module live Gemini prose audit in a single run. Use `--provider mock` for CI/regression checks and `--provider gemini` with a billed/higher-quota key for prose audits.
