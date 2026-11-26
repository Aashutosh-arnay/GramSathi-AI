// API layer – follows the contract in the PRD (section 13/15).
// Falls back to demo data when a route is missing and VITE_USE_MOCK !== "false".
const BASE = import.meta.env.VITE_API_URL || "/api";
const MOCK = import.meta.env.VITE_USE_MOCK !== "false";
const store = (k, v) => (v === undefined ? JSON.parse(localStorage.getItem(k) || "null") : localStorage.setItem(k, JSON.stringify(v)));

async function req(path, opts = {}) {
  const token = localStorage.getItem("gs_token");
  const r = await fetch(BASE + path, {
    ...opts,
    headers: { "Content-Type": "application/json", ...(token && { Authorization: `Bearer ${token}` }) },
  });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(d.message || "Request failed"), { status: r.status });
  return d;
}
const call = async (path, opts, mock) => {
  try { return await req(path, opts); }
  catch (e) { if (MOCK && (!e.status || e.status === 404)) return mock(); throw e; }
};
const post = (body) => ({ method: "POST", body: JSON.stringify(body) });

export const auth = {
  login: (b) => call("/auth/login", post(b), () => ({ token: "demo", user: { name: b.email.split("@")[0], email: b.email } })),
  register: (b) => call("/auth/register", post(b), () => ({ token: "demo", user: { name: b.name, email: b.email } })),
};

// body: { assistant: "farm"|"nyaya", message, language: "hi"|"en" }
// returns: { answer, sources:[{title,url}], evidence_status, needs_followup }
export const chat = (body) =>
  call("/chat", post(body), () => {
    const m = body.message.toLowerCase();
    const hit = /gehun|wheat|गेहूं|patt|पत्त|yojana|योजना|scheme|land|जमीन/.test(m);
    const hi = body.language === "hi";
    const res = !hit
      ? { answer: hi ? "माफ़ कीजिए, मेरे पास इस सवाल के लिए पर्याप्त सत्यापित जानकारी नहीं है। कृपया स्थानीय कृषि कार्यालय या आधिकारिक पोर्टल से संपर्क करें।" : "Sorry, I don't have enough verified information to answer this. Please contact your local office or the official portal.", sources: [], evidence_status: "insufficient", needs_followup: false }
      : m.length < 25
      ? { answer: hi ? "सही जवाब के लिए बताइए: फसल कौन सी अवस्था में है और आपका ज़िला कौन सा है?" : "To help properly, please tell me: what stage is the crop at, and which district are you in?", sources: [], evidence_status: "partial", needs_followup: true }
      : { answer: hi ? "यह एक डेमो उत्तर है। असली उत्तर RAG सेवा से आएगा, जिसमें सत्यापित दस्तावेज़ों के स्रोत दिखेंगे।" : "This is a demo answer. The real answer will come from the RAG service, with sources from verified documents.", sources: [{ title: "Demo source (replace with retrieved document)", url: "https://www.myscheme.gov.in/" }], evidence_status: "sufficient", needs_followup: false };
    return new Promise((r) => setTimeout(() => r(res), 900));
  });

export const history = {
  list: () => call("/chat/history", {}, () => store("gs_hist") || []),
  // Used only in demo mode so history works before the backend saves it
  saveLocal: (assistant, messages) => {
    if (!MOCK) return;
    const h = store("gs_hist") || [];
    const title = messages.find((m) => m.role === "user")?.content.slice(0, 48) || "…";
    store("gs_hist", [{ _id: Date.now(), assistant, title, messages, updatedAt: new Date().toISOString() }, ...h].slice(0, 30));
  },
};
