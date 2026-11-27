"""NyayaSathi system and user prompt builders + localized legal disclaimers.

Design constraints (from §5 and §7 of the roadmap):
- Answer ONLY from retrieved CONTEXT in simple, easy-to-understand language.
- Answer in the request's language (hi / en).
- NEVER state section numbers, case names, or deadlines (limitation periods,
  notice periods) unless they explicitly appear in the retrieved CONTEXT.
- Explain practical next steps and when to approach a qualified advocate or
  free legal aid (NALSA / State Legal Services Authority).
- State the effective date of a cited provision when available.
"""
from __future__ import annotations

from app.services.retrieval_service import RetrievedChunk

LEGAL_DISCLAIMER_EN = (
    "⚖️ Disclaimer: GramSathi AI provides general legal information for "
    "educational purposes only. It is not a substitute for professional legal "
    "advice or representation by a qualified advocate. For specific legal "
    "matters, please consult a licensed legal professional or contact your "
    "nearest Legal Services Authority (NALSA / SLSA)."
)

LEGAL_DISCLAIMER_HI = (
    "⚖️ अस्वीकरण: GramSathi AI केवल सामान्य और शैक्षिक उद्देश्यों के लिए कानूनी "
    "जानकारी प्रदान करता है। यह किसी योग्य वकील की पेशेवर कानूनी सलाह या "
    "प्रतिनिधित्व का विकल्प नहीं है। किसी भी विशिष्ट कानूनी मामले के लिए कृपया "
    "किसी पंजीकृत वकील या अपने नज़दीकी विधिक सेवा प्राधिकरण (NALSA / SLSA) से संपर्क करें।"
)


def get_legal_disclaimer(language: str) -> str:
    """Return the mandatory legal disclaimer in the requested language."""
    if (language or "en").lower().startswith("hi"):
        return LEGAL_DISCLAIMER_HI
    return LEGAL_DISCLAIMER_EN


NYAYASATHI_SYSTEM_PROMPT = """\
You are NyayaSathi AI, an accessible legal-information assistant for ordinary
Indian citizens, part of the GramSathi AI platform.

STRICT RULES – follow every rule without exception:
1. Answer ONLY from the CONTEXT provided in the user message.
   Do NOT use outside knowledge or invent legal provisions.
2. Answer in the LANGUAGE indicated in the user message (hi = Hindi, en = English),
   using simple, plain words that non-lawyers can understand.
3. NEVER state section numbers, act names, case names, judicial decisions, or
   deadlines (such as limitation periods or notice periods) unless they
   explicitly appear in the retrieved CONTEXT.
4. If the user asks about a specific section number that does NOT appear in the
   CONTEXT, clearly state that you cannot verify or confirm that section from
   available official sources.
5. Whenever an effective date is provided in a retrieved provision's metadata,
   mention that effective date in your explanation.
6. Always explain practical next steps and when the user should approach a
   qualified advocate or free legal aid (NALSA / State Legal Services Authority).
7. Cite only official sources present in CONTEXT; never invent URLs or citations.
"""


def build_nyayasathi_user_message(
    question: str,
    language: str,
    chunks: list[RetrievedChunk],
    *,
    country: str | None = "India",
    state: str | None = None,
    category: str | None = None,
    history_summary: str = "",
) -> str:
    """Compose the user-turn message sent to the LLM for NyayaSathi."""
    if chunks:
        context_parts: list[str] = []
        for c in chunks:
            meta = c.metadata or {}
            header_bits = [f"Document: {c.source_title}"]
            if c.publisher:
                header_bits.append(f"Authority: {c.publisher}")
            if meta.get("jurisdiction"):
                jur = meta["jurisdiction"]
                if meta.get("applicable_state"):
                    jur = f"{jur} ({meta['applicable_state']})"
                header_bits.append(f"Jurisdiction: {jur}")
            if meta.get("act_name"):
                header_bits.append(f"Act: {meta['act_name']}")
            if meta.get("section_number"):
                header_bits.append(f"Section: {meta['section_number']}")
            if meta.get("effective_date"):
                header_bits.append(f"Effective Date: {meta['effective_date']}")
            header = " | ".join(header_bits)
            context_parts.append(f"[{header}]\n{c.text}")
        context_block = "\n---\n".join(context_parts)
    else:
        context_block = "(none)"

    ctx_lines: list[str] = []
    if country:
        ctx_lines.append(f"Country: {country}")
    if state:
        ctx_lines.append(f"State: {state}")
    if category:
        ctx_lines.append(f"Category: {category}")
    legal_context = "  |  ".join(ctx_lines) if ctx_lines else "(not provided)"

    history_block = history_summary if history_summary else "(none)"

    return (
        f"LANGUAGE: {language}\n\n"
        f"LEGAL CONTEXT: {legal_context}\n\n"
        f"RECENT HISTORY:\n{history_block}\n\n"
        f"CONTEXT:\n{context_block}\n\n"
        f"QUESTION: {question}"
    )
