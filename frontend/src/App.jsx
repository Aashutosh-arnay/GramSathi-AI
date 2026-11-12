import { useEffect, useRef, useState } from "react";
import { auth, chat, history } from "./api.js";

const T = {
  hi: {
    tag: "आपका डिजिटल ग्रामसाथी", sub: "खेती, सरकारी योजनाओं और ज़मीन-कानून की जानकारी — सरल भाषा में, भरोसेमंद स्रोतों के साथ।",
    login: "लॉग इन", register: "खाता बनाएँ", name: "आपका नाम", email: "ईमेल", pass: "पासवर्ड", haveNo: "खाता नहीं है? खाता बनाएँ", haveYes: "पहले से खाता है? लॉग इन करें",
    hello: "नमस्ते", pick: "आप किस बारे में पूछना चाहते हैं?", history: "पुरानी बातचीत", logout: "बाहर निकलें", home: "होम",
    farmT: "खेती के सवाल", farmD: "फसल, मिट्टी, सिंचाई, खाद और रोग-कीट की सामान्य जानकारी",
    nyT: "योजना और ज़मीन-कानून", nyD: "सरकारी योजनाएँ, ज़मीन के कागज़ और आम प्रशासनिक प्रक्रियाएँ",
    ask: "अपना सवाल लिखें…", send: "भेजें", think: "जानकारी खोज रहे हैं…", sources: "स्रोत", empty: "अभी कोई बातचीत नहीं है।", back: "वापस",
    ok: "सत्यापित स्रोतों पर आधारित", partial: "कुछ जानकारी और चाहिए", no: "पर्याप्त सत्यापित जानकारी नहीं मिली",
    farmN: "यह सामान्य जानकारी है, स्थानीय कृषि विशेषज्ञ की जाँच का विकल्प नहीं।", nyN: "यह जानकारी समझाने के लिए है — कानूनी सलाह या सरकारी पात्रता निर्णय नहीं।",
    err: "कुछ गड़बड़ हुई। कृपया दोबारा कोशिश करें।", new: "नई बातचीत",
    fq: ["मेरे गेहूं के पत्तों पर पीले धब्बे हैं", "धान की रोपाई का सही समय क्या है?"], nq: ["किसानों के लिए कौन सी योजनाएँ हैं?", "ज़मीन का दाखिल-खारिज कैसे होता है?"],
  },
  en: {
    tag: "Your digital GramSathi", sub: "Farming, government schemes and land-law information — in simple language, backed by trusted sources.",
    login: "Log in", register: "Create account", name: "Your name", email: "Email", pass: "Password", haveNo: "No account? Create one", haveYes: "Already have an account? Log in",
    hello: "Namaste", pick: "What would you like to ask about?", history: "Past chats", logout: "Log out", home: "Home",
    farmT: "Farming questions", farmD: "General info on crops, soil, irrigation, fertilizer, pests and diseases",
    nyT: "Schemes & land law", nyD: "Government schemes, land documents and common administrative procedures",
    ask: "Type your question…", send: "Send", think: "Searching verified documents…", sources: "Sources", empty: "No conversations yet.", back: "Back",
    ok: "Based on verified sources", partial: "More details needed", no: "Not enough verified information found",
    farmN: "General information only — not a substitute for local expert diagnosis.", nyN: "Explanatory only — not legal advice or an official eligibility decision.",
    err: "Something went wrong. Please try again.", new: "New chat",
    fq: ["Yellow spots on my wheat leaves", "When should I transplant paddy?"], nq: ["Which schemes are there for farmers?", "How does land mutation work?"],
  },
};
const A = { farm: { icon: "🌾", cls: "farm", t: "FarmSathi", d: "farmD", h: "farmT", n: "farmN", q: "fq" }, nyaya: { icon: "⚖️", cls: "nyaya", t: "NyayaSathi", d: "nyD", h: "nyT", n: "nyN", q: "nq" } };

export default function App() {
  const [lang, setLang] = useState(localStorage.getItem("gs_lang") || "hi");
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem("gs_user") || "null"));
  const [view, setView] = useState("home");
  const [asst, setAsst] = useState(null);
  const [msgs, setMsgs] = useState([]);
  const t = T[lang];
  useEffect(() => { localStorage.setItem("gs_lang", lang); document.documentElement.lang = lang; }, [lang]);

  const enter = ({ token, user }) => { localStorage.setItem("gs_token", token); localStorage.setItem("gs_user", JSON.stringify(user)); setUser(user); setView("home"); };
  const leave = () => { localStorage.removeItem("gs_token"); localStorage.removeItem("gs_user"); setUser(null); setMsgs([]); };
  const open = (a, m = []) => { setAsst(a); setMsgs(m); setView("chat"); };

  return (
    <div className="app">
      <header className="top">
        <button className="brand" onClick={() => user && setView("home")}>🌾 <b>GramSathi</b> AI</button>
        <div className="actions">
          <div className="seg" role="group" aria-label="Language">
            {["hi", "en"].map((l) => <button key={l} className={lang === l ? "on" : ""} onClick={() => setLang(l)}>{l === "hi" ? "हिंदी" : "EN"}</button>)}
          </div>
          {user && <><button className="ghost" onClick={() => setView("history")}>🕘 <span className="hide-sm">{t.history}</span></button><button className="ghost" onClick={leave}>⎋ <span className="hide-sm">{t.logout}</span></button></>}
        </div>
      </header>
      <main>
        {!user ? <Auth t={t} onDone={enter} />
          : view === "home" ? <Home t={t} user={user} onPick={(a) => open(a)} />
          : view === "history" ? <History t={t} onOpen={(c) => open(c.assistant, c.messages)} onBack={() => setView("home")} />
          : <Chat key={asst + msgs.length} t={t} lang={lang} asst={asst} initial={msgs} onBack={() => setView("home")} />}
      </main>
    </div>
  );
}

function Auth({ t, onDone }) {
  const [reg, setReg] = useState(false);
  const [f, setF] = useState({ name: "", email: "", password: "" });
  const [err, setErr] = useState(""), [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setErr("");
    try { onDone(await (reg ? auth.register(f) : auth.login(f))); } catch (x) { setErr(x.message); } finally { setBusy(false); }
  };
  return (
    <section className="hero">
      <div className="hero-copy"><h1>{t.tag}</h1><p>{t.sub}</p>
        <ul className="pills"><li>🌾 FarmSathi</li><li>⚖️ NyayaSathi</li><li>📄 {t.sources}</li></ul></div>
      <form className="card auth" onSubmit={submit}>
        <h2>{reg ? t.register : t.login}</h2>
        {reg && <input required placeholder={t.name} value={f.name} onChange={set("name")} autoComplete="name" />}
        <input required type="email" placeholder={t.email} value={f.email} onChange={set("email")} autoComplete="email" />
        <input required type="password" minLength={6} placeholder={t.pass} value={f.password} onChange={set("password")} autoComplete={reg ? "new-password" : "current-password"} />
        {err && <p className="err" role="alert">{err}</p>}
        <button className="primary" disabled={busy}>{busy ? "…" : reg ? t.register : t.login}</button>
        <button type="button" className="link" onClick={() => setReg(!reg)}>{reg ? t.haveYes : t.haveNo}</button>
      </form>
    </section>
  );
}

function Home({ t, user, onPick }) {
  return (
    <section className="home">
      <h1>{t.hello}, {user.name} 🙏</h1><p className="muted">{t.pick}</p>
      <div className="cards">
        {Object.entries(A).map(([k, a]) => (
          <button key={k} className={`card pick ${a.cls}`} onClick={() => onPick(k)}>
            <span className="ico">{a.icon}</span><h2>{a.t}</h2><b>{t[a.h]}</b><p>{t[a.d]}</p>
          </button>
        ))}
      </div>
    </section>
  );
}

function Chat({ t, lang, asst, initial, onBack }) {
  const a = A[asst];
  const [msgs, setMsgs] = useState(initial);
  const [text, setText] = useState(""), [busy, setBusy] = useState(false), [err, setErr] = useState("");
  const end = useRef();
  useEffect(() => end.current?.scrollIntoView({ behavior: "smooth" }), [msgs, busy]);

  const send = async (q) => {
    const message = (q ?? text).trim();
    if (!message || busy) return;
    const next = [...msgs, { role: "user", content: message }];
    setMsgs(next); setText(""); setBusy(true); setErr("");
    try {
      const r = await chat({ assistant: asst, message, language: lang });
      const done = [...next, { role: "assistant", content: r.answer, sources: r.sources || [], status: r.evidence_status, followup: r.needs_followup }];
      setMsgs(done); history.saveLocal(asst, done);
    } catch { setErr(t.err); } finally { setBusy(false); }
  };

  return (
    <section className={`chat ${a.cls}`}>
      <div className="chat-head"><button className="ghost" onClick={onBack}>← <span className="hide-sm">{t.back}</span></button><span className="ico sm">{a.icon}</span><div><b>{a.t}</b><small>{t[a.h]}</small></div></div>
      <div className="thread" aria-live="polite">
        {!msgs.length && <div className="starter"><span className="ico">{a.icon}</span><p>{t[a.d]}</p>{t[a.q].map((s) => <button key={s} className="chip" onClick={() => send(s)}>{s}</button>)}</div>}
        {msgs.map((m, i) => m.role === "user" ? <div key={i} className="bub me">{m.content}</div> : (
          <div key={i} className="bub bot">
            <span className={`badge ${m.status}`}>{m.status === "sufficient" ? "✔ " + t.ok : m.status === "partial" || m.followup ? "？ " + t.partial : "ⓘ " + t.no}</span>
            <p>{m.content}</p>
            {!!m.sources?.length && <div className="src"><small>{t.sources}</small>{m.sources.map((s) => <a key={s.url} href={s.url} target="_blank" rel="noreferrer">🔗 {s.title}</a>)}</div>}
          </div>))}
        {busy && <div className="bub bot typing"><i /><i /><i /><span className="sr">{t.think}</span></div>}
        {err && <p className="err" role="alert">{err}</p>}
        <div ref={end} />
      </div>
      <form className="composer" onSubmit={(e) => { e.preventDefault(); send(); }}>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder={t.ask} aria-label={t.ask} />
        <button className="primary" disabled={busy || !text.trim()}>{t.send} ➤</button>
      </form>
      <p className="note">ⓘ {t[a.n]}</p>
    </section>
  );
}

function History({ t, onOpen, onBack }) {
  const [list, setList] = useState(null);
  useEffect(() => { history.list().then(setList).catch(() => setList([])); }, []);
  return (
    <section className="home">
      <button className="ghost" onClick={onBack}>← {t.back}</button><h1>{t.history}</h1>
      {list && !list.length && <p className="muted">{t.empty}</p>}
      <ul className="hist">{(list || []).map((c) => (
        <li key={c._id}><button className="card" onClick={() => onOpen(c)}><span className="ico sm">{A[c.assistant]?.icon}</span><div><b>{c.title}</b><small>{A[c.assistant]?.t} · {new Date(c.updatedAt).toLocaleDateString()}</small></div></button></li>))}
      </ul>
    </section>
  );
}
