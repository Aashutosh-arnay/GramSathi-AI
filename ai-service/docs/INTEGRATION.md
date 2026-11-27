# GramSathi AI Service — Node.js Backend Integration Guide

This document describes how the **Node.js + Express** backend communicates with the **Python + FastAPI** AI service (`ai-service/`).

---

## 1. Base URL & Authentication

- **Local Development Base URL:** `http://localhost:8000`
- **Internal Service Auth Header:**
  ```http
  AI-Service-Api-Key: <AI_SERVICE_API_KEY>
  ```
- **Important:** `AI_SERVICE_API_KEY` is an internal service-to-service secret. **Never** reuse the user-facing JWT secret, and never expose this key to the React frontend.
- **Data Ownership Rule:** The AI service is **stateless** with respect to user accounts and MongoDB. Node.js verifies the user's JWT, validates conversation ownership, saves user messages and AI responses (`answer`, `answerStatus`, `sources`, `disclaimer`, `metadata`) to **MongoDB**, and returns the final response to React.

---

## 2. Recommended Node.js Timeout

Set the HTTP client timeout in Node.js (e.g. `axios` / `fetch`) to **at least `50000` ms (50 seconds)**:
- Gemini REST timeout per attempt: `20s`
- Automatic retry on `5xx` / timeout: `1` retry + `0.5s` backoff (up to ~`40.5s` worst-case LLM time)
- Local embedding + Chroma retrieval overhead: ~`1–3s`

---

## 3. Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/health` | None | Liveness probe |
| `GET` | `/api/v1/meta/states` | `AI-Service-Api-Key` | Canonical list of 36 Indian States & UTs |
| `POST` | `/api/v1/farmsathi/chat` | `AI-Service-Api-Key` | Agricultural Q&A (Hindi / English) |
| `POST` | `/api/v1/nyayasathi/chat` | `AI-Service-Api-Key` | Legal information Q&A (Hindi / English) |

---

## 4. State List & Normalization

Call `GET /api/v1/meta/states` to populate state dropdowns in React.  
`context.state` also accepts common abbreviations (`"UP"`, `"MP"`, `"DL"`) and Hindi names (`"बिहार"`, `"उत्तर प्रदेश"`), which are normalized to the canonical English name. Unrecognized non-empty states are treated as missing.

---

## 5. Request & Response Samples

### Request (`POST /api/v1/farmsathi/chat` or `/api/v1/nyayasathi/chat`)

```json
{
  "requestId": "req-12345",
  "conversationId": "6748a1b2c3d4e5f600000001",
  "message": "Who is eligible for PM-KISAN income support?",
  "language": "en",
  "history": [
    { "role": "user", "content": "I grow wheat in Bihar." },
    { "role": "assistant", "content": "How can I help with your wheat crop?" }
  ],
  "context": {
    "state": "Bihar",
    "crop": "Wheat"
  },
  "attachments": []
}
```

**Input limits enforced by Pydantic:**
- `message`: 1–2000 characters
- `language`: `"hi"` or `"en"` only
- `history`: truncated to the last 6 messages
- `attachments`: must be `[]` (non-empty arrays return HTTP `422`)

### Response (`200 OK`)

```json
{
  "requestId": "req-12345",
  "answer": "...",
  "language": "en",
  "answerStatus": "supported",
  "sources": [
    {
      "title": "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN) Operational Guidelines",
      "publisher": "Ministry of Agriculture & Farmers Welfare, Government of India",
      "url": "https://pmkisan.gov.in/Documents/OPERATIONAL%20GUIDELINES.pdf",
      "publishedAt": null,
      "retrievedAt": "2026-11-28"
    }
  ],
  "followUpQuestions": [],
  "disclaimer": null,
  "metadata": { "service": "farmsathi", "version": "1.0" }
}
```

*(For NyayaSathi, `disclaimer` is **always** populated in the requested language on every status.)*

---

## 6. Handling `answerStatus`

| `answerStatus` | Meaning | Node.js / React Action |
|---|---|---|
| `supported` | Grounded answer generated from verified sources | Save `answer`, `sources`, `disclaimer`; render citations |
| `needs_clarification` | Missing crop/state context | Render `answer` and `followUpQuestions` as quick-reply chips |
| `insufficient_information` | No verified source or out-of-scope / unverified claim | Render `answer` (and `disclaimer` for NyayaSathi); do not show fabricated sources |

---

## 7. Error Format & Handling

All errors follow §6.3:

```json
{
  "requestId": "req-12345",
  "error": {
    "code": "LLM_RATE_LIMITED",
    "message": "The language model rate limit or quota was exceeded. Please try again shortly.",
    "retryable": true
  }
}
```

| HTTP | `error.code` | `retryable` | Node.js Action |
|---|---|---|---|
| `401` | `UNAUTHORIZED` | `false` | Check `AI_SERVICE_API_KEY` config; do not retry |
| `422` | `VALIDATION_ERROR` | `false` | Fix request payload (`message` length, `language`, `attachments`); do not retry |
| `429` | `LLM_RATE_LIMITED` | `true` | Back off and retry or show "AI busy, please try again shortly" |
| `500` | `LLM_CONFIG_ERROR` | `false` | Alert ops (missing/invalid `LLM_API_KEY` or `LLM_MODEL`) |
| `503` | `LLM_UNAVAILABLE` | `true` | Retry once after short delay or return friendly service-unavailable message |
| `503` | `RETRIEVAL_UNAVAILABLE` | `true` | Vector store unavailable; retry or degrade gracefully |
