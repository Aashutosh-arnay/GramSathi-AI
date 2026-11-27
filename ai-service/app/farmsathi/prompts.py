"""FarmSathi system and user prompt builders.

Design constraints (from §4 and §7 of the roadmap):
- Answer ONLY from retrieved context; never from parametric LLM knowledge.
- Answer in the language specified by the request (hi / en).
- When context is missing, ask a follow-up and return needs_clarification.
- Never prescribe pesticide/fertilizer dosages without supporting evidence.
- Recommend a KVK or expert when the diagnosis is uncertain.
"""
from __future__ import annotations

from app.services.retrieval_service import RetrievedChunk

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

FARMSATHI_SYSTEM_PROMPT = """\
You are FarmSathi AI, an agricultural assistant for Indian farmers, part of the
GramSathi AI platform.

STRICT RULES – follow every rule without exception:
1. Answer ONLY from the CONTEXT provided in the user message.
   Do NOT use any knowledge not present in CONTEXT.
2. Answer in the LANGUAGE indicated in the user message (hi = Hindi, en = English).
3. If CONTEXT is empty or "(none)", do NOT attempt to answer.
   Instead, politely state that you do not have enough information and ask a
   follow-up question to gather more details.
4. Never prescribe specific pesticide or fertilizer dosages unless CONTEXT
   explicitly states them with a reliable source.
5. When uncertain, always recommend that the farmer contact their nearest
   Krishi Vigyan Kendra (KVK) or a certified agricultural expert.
6. Keep answers practical and easy to understand for farmers with limited
   technical background.
7. Cite only sources that appear in the retrieved CONTEXT; never invent URLs
   or document titles.
"""

# ---------------------------------------------------------------------------
# User message builder
# ---------------------------------------------------------------------------


def build_user_message(
    question: str,
    language: str,
    chunks: list[RetrievedChunk],
    *,
    state: str | None = None,
    district: str | None = None,
    crop: str | None = None,
    crop_stage: str | None = None,
    history_summary: str = "",
) -> str:
    """Compose the user-turn message sent to the LLM.

    Parameters
    ----------
    question:
        The farmer's current question.
    language:
        ISO 639-1 code, e.g. ``"hi"`` or ``"en"``.
    chunks:
        Retrieved knowledge-base chunks (may be empty).
    state, district, crop, crop_stage:
        Request context fields forwarded from the Node.js backend.
    history_summary:
        A short textual summary of recent conversation turns (optional).
    """
    # Build context block
    if chunks:
        context_parts = [
            f"[Source: {c.source_title} | {c.publisher}]\n{c.text}"
            for c in chunks
        ]
        context_block = "\n---\n".join(context_parts)
    else:
        context_block = "(none)"

    # Build context metadata
    ctx_lines: list[str] = []
    if crop:
        ctx_lines.append(f"Crop: {crop}")
    if crop_stage:
        ctx_lines.append(f"Crop stage: {crop_stage}")
    if state:
        ctx_lines.append(f"State: {state}")
    if district:
        ctx_lines.append(f"District: {district}")
    farmer_context = "  |  ".join(ctx_lines) if ctx_lines else "(not provided)"

    history_block = history_summary if history_summary else "(none)"

    return (
        f"LANGUAGE: {language}\n\n"
        f"FARMER CONTEXT: {farmer_context}\n\n"
        f"RECENT HISTORY:\n{history_block}\n\n"
        f"CONTEXT:\n{context_block}\n\n"
        f"QUESTION: {question}"
    )


def summarise_history(history: list[dict]) -> str:
    """Convert recent history turns to a short readable summary."""
    if not history:
        return ""
    lines = []
    for turn in history[-6:]:   # limit to last 6 turns
        role = turn.get("role", "?")
        content = turn.get("content", "")
        lines.append(f"{role.capitalize()}: {content}")
    return "\n".join(lines)
