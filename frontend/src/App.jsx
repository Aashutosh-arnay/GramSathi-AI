import { useEffect, useRef, useState } from "react";
import { auth, chat, history } from "./api.js";

const T = {
  hi: {
    tag: "आपका डिजिटल ग्रामसाथी", sub: "खेती, सरकारी योजनाओं और ज़मीन-कानून की जानकारी — सरल भाषा में, भरोसेमंद स्रोतों के साथ।",
    login: "लॉग इन", register: "खाता बनाएँ", name: "आपका नाम", email: "ईमेल", pass: "पासवर्ड", haveNo: "खाता नहीं है? खाता बनाएँ", haveYes: "पहले से खाता है? लॉग इन करें",
    about: "हमारे बारे में", features: "सुविधाएँ", contact: "संपर्क", getStarted: "शुरू करें", learnMore: "और जानें", impact: "किसानों और नागरिकों के लिए भरोसेमंद AI सहायता", why: "ग्रामसाथी AI क्यों?", farmLabel: "स्मार्ट खेती, बेहतर कल", nyLabel: "अपने अधिकार जानें", farmer: "किसान", citizen: "नागरिक", welcome: "नमस्ते", dashboard: "डैशबोर्ड", quickLinks: "ज़रूरी लिंक", recent: "हाल की गतिविधि", viewAll: "सभी देखें", help: "मदद चाहिए?", voice: "वॉइस असिस्टेंट", notification: "सूचनाएँ", profile: "प्रोफ़ाइल", settings: "सेटिंग्स", schemes: "सरकारी योजनाएँ", helpline: "हेल्पलाइन", notices: "ज़रूरी सूचनाएँ", growth: "ग्रामीण भारत की प्रगति के लिए", motto: "AI का साथ, हर गाँव के साथ", accessible: "सरल और सुलभ",
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
    about: "About", features: "Features", contact: "Contact", getStarted: "Get started", learnMore: "Learn more", impact: "Trusted AI support for farmers and citizens", why: "Why GramSathi AI?", farmLabel: "Smarter farming, better tomorrow", nyLabel: "Know your rights", farmer: "Farmers", citizen: "Citizens", welcome: "Namaste", dashboard: "Dashboard", quickLinks: "Quick links", recent: "Recent activity", viewAll: "View all", help: "Need help?", voice: "Voice assistant", notification: "Notifications", profile: "Profile", settings: "Settings", schemes: "Govt. schemes", helpline: "Helpline", notices: "Important notices", growth: "for rural India's growth", motto: "AI ka saath, har gaon ke saath", accessible: "Simple and accessible",
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
  const [view, setView] = useState(() => localStorage.getItem("gs_user") ? "home" : "landing");
  const [authMode, setAuthMode] = useState("login");
  const [asst, setAsst] = useState(null);
  const [msgs, setMsgs] = useState([]);
  const t = T[lang];
  useEffect(() => { localStorage.setItem("gs_lang", lang); document.documentElement.lang = lang; }, [lang]);

  const enter = ({ token, user }) => { localStorage.setItem("gs_token", token); localStorage.setItem("gs_user", JSON.stringify(user)); setUser(user); setView("home"); };
  const leave = () => { localStorage.removeItem("gs_token"); localStorage.removeItem("gs_user"); setUser(null); setMsgs([]); };
  const open = (a, m = []) => { setAsst(a); setMsgs(m); setView("chat"); };
  const showAuth = (mode = "login") => { setAuthMode(mode); setView("auth"); };

  return (
    <div className="app">
      <header className="top">
        <button className="brand" onClick={() => setView(user ? "home" : "landing")} aria-label="GramSathi AI home">
          <span className="brand-mark" aria-hidden="true">🌱</span><span><b>GramSathi</b> AI<small>AI ka saath, har gaon ke saath</small></span>
        </button>
        {!user && view === "landing" && <nav className="main-nav" aria-label="Main navigation">
          <button className="nav-active" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>{t.home}</button>
          <a href="#about">{t.about}</a><a href="#features">{t.features}</a><a href="#contact">{t.contact}</a>
        </nav>}
        <div className="actions">
          <div className="seg" role="group" aria-label="Language">
            {["hi", "en"].map((l) => <button key={l} className={lang === l ? "on" : ""} onClick={() => setLang(l)}>{l === "hi" ? "हिंदी" : "EN"}</button>)}
          </div>
          {user ? <><button className="ghost" onClick={() => setView("history")}>🕘 <span className="hide-sm">{t.history}</span></button><button className="ghost" onClick={leave}>⎋ <span className="hide-sm">{t.logout}</span></button></>
            : <button className="primary top-login" onClick={() => showAuth("login")}>{t.login}</button>}
        </div>
      </header>
      <main>
        {!user ? view === "auth" ? <Auth key={authMode} t={t} initialMode={authMode} onMode={setAuthMode} onDone={enter} onBack={() => setView("landing")} />
          : <Landing t={t} onAuth={showAuth} />
          : view === "home" ? <Home t={t} user={user} onPick={(a) => open(a)} onHistory={() => setView("history")} />
          : view === "history" ? <History t={t} onOpen={(c) => open(c.assistant, c.messages)} onBack={() => setView("home")} />
          : <Chat key={asst + msgs.length} t={t} lang={lang} asst={asst} initial={msgs} onBack={() => setView("home")} />}
      </main>
    </div>
  );
}

function Landing({ t, onAuth }) {
  return (
    <div className="landing">
      <section className="landing-hero">
        <div className="hero-copy">
          <span className="eyebrow"><span className="status-dot" /> {t.impact}</span>
          <h1>{t.tag}<br /><span>{t.growth}</span></h1>
          <p>{t.sub}</p>
          <div className="hero-buttons">
            <button className="primary" onClick={() => onAuth("register")}>{t.getStarted}<span aria-hidden="true"> →</span></button>
            <a className="secondary-button" href="#features">{t.learnMore}<span aria-hidden="true"> ↓</span></a>
          </div>
          <div className="trust-line"><span className="trust-icon">✓</span> {t.ok} <span className="trust-divider">·</span> {t.accessible}</div>
        </div>
        <div className="hero-art" aria-label="Illustration of a farmer in a green field">
          <div className="art-sun" />
          <div className="art-cloud cloud-one" /><div className="art-cloud cloud-two" />
          <div className="art-hill hill-back" /><div className="art-hill hill-front" />
          <div className="art-ridge ridge-one" /><div className="art-ridge ridge-two" />
          <div className="art-tree tree-one">♣</div><div className="art-tree tree-two">♣</div>
          <div className="art-home"><span /><i /></div>
          <div className="farmer-illustration" aria-hidden="true">
            <span className="farmer-scarf" /><span className="farmer-head"><i /></span>
            <span className="farmer-body"><i /><b /></span><span className="farmer-arm" /><span className="farmer-phone">▯</span>
          </div>
          <span className="art-leaf leaf-one">✦</span><span className="art-leaf leaf-two">✦</span>
          <div className="art-caption"><span>🌾</span><div><b>{t.farmLabel}</b><small>{t.farmT}</small></div></div>
          <div className="art-corner">भारत का भविष्य, गाँवों के साथ</div>
        </div>
        <div className="hero-stats">
          <div><span className="stat-icon">🌾</span><b>{t.farmer}</b><small>{t.farmT}</small></div>
          <div><span className="stat-icon">⚖️</span><b>{t.citizen}</b><small>{t.nyT}</small></div>
          <div><span className="stat-icon">🛡️</span><b>{t.ok}</b><small>{t.sources}</small></div>
        </div>
      </section>
      <section className="benefits" id="about">
        <div className="section-heading"><span className="eyebrow">{t.why}</span><h2>{t.pick}</h2></div>
        <div className="benefit-grid">
          <article><span>🌱</span><h3>{t.farmT}</h3><p>{t.farmD}</p></article>
          <article><span>🤝</span><h3>{t.citizen}</h3><p>{t.nyD}</p></article>
          <article><span>✓</span><h3>{t.ok}</h3><p>{t.sub}</p></article>
        </div>
      </section>
      <section className="feature-section" id="features">
        <div><span className="eyebrow">{t.features}</span><h2>{t.pick}</h2><p>{t.sub}</p></div>
        <div className="feature-actions">
          <button className="feature-tile farm-tile" onClick={() => onAuth("register")}><span>🌾</span><div><b>FarmSathi AI</b><small>{t.farmLabel}</small></div><i>→</i></button>
          <button className="feature-tile nyaya-tile" onClick={() => onAuth("register")}><span>⚖️</span><div><b>NyayaSathi AI</b><small>{t.nyLabel}</small></div><i>→</i></button>
        </div>
      </section>
      <footer id="contact"><div className="footer-brand"><span>🌱</span><b>GramSathi AI</b></div><p>{t.sub}</p><button className="footer-cta" onClick={() => onAuth("register")}>{t.getStarted} →</button></footer>
    </div>
  );
}

function Auth({ t, initialMode, onMode, onDone, onBack }) {
  const reg = initialMode === "register";
  const [f, setF] = useState({ name: "", email: "", password: "" });
  const [err, setErr] = useState(""), [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setErr("");
    try { onDone(await (reg ? auth.register(f) : auth.login(f))); } catch (x) { setErr(x.message); } finally { setBusy(false); }
  };
  return (
    <section className="auth-page">
      <div className="auth-aside">
        <button className="back-link" onClick={onBack}>← {t.home}</button>
        <div className="auth-aside-copy"><span className="auth-emblem">🌾</span><h1>{t.tag}</h1><p>{t.sub}</p><div className="auth-checks"><span>✓ {t.ok}</span><span>✓ {t.farmLabel}</span><span>✓ {t.nyLabel}</span></div></div>
        <div className="auth-landscape"><span>🌳</span><span>🌾</span><span>🏡</span><span>🌾</span><span>🌳</span></div>
      </div>
      <form className="card auth" onSubmit={submit}>
        <div className="auth-heading"><span className="eyebrow">{reg ? t.register : t.welcome}</span><h2>{reg ? t.register : t.login}</h2><p>{reg ? t.sub : t.haveNo}</p></div>
        {reg && <label>{t.name}<input required name="name" placeholder={t.name} value={f.name} onChange={set("name")} autoComplete="name" /></label>}
        <label>{t.email}<input required name="email" type="email" placeholder={t.email} value={f.email} onChange={set("email")} autoComplete="email" /></label>
        <label>{t.pass}<input required name="password" type="password" minLength={6} placeholder={t.pass} value={f.password} onChange={set("password")} autoComplete={reg ? "new-password" : "current-password"} /></label>
        {err && <p className="err" role="alert">{err}</p>}
        <button className="primary auth-submit" disabled={busy}>{busy ? "…" : reg ? t.register : t.login}<span aria-hidden="true"> →</span></button>
        <p className="auth-switch">{reg ? t.haveYes : t.haveNo} <button type="button" className="link" onClick={() => onMode(reg ? "login" : "register")}>{reg ? t.login : t.register}</button></p>
      </form>
    </section>
  );
}

function Home({ t, user, onPick, onHistory }) {
  return (
    <section className="dashboard">
      <aside className="side-nav">
        <div className="side-brand"><span>🌱</span><b>GramSathi AI</b></div>
        <p className="side-label">{t.dashboard}</p><button className="side-item selected">⌂ <span>{t.dashboard}</span></button>
        <button className="side-item" onClick={() => onPick("farm")}>🌾 <span>FarmSathi AI</span></button>
        <button className="side-item" onClick={() => onPick("nyaya")}>⚖️ <span>NyayaSathi AI</span></button>
        <div className="side-separator" /><p className="side-label">{t.quickLinks}</p>
        <button className="side-item" onClick={onHistory}>🕘 <span>{t.history}</span></button>
        <button className="side-item">⚙️ <span>{t.settings}</span></button>
        <div className="side-bottom"><span>🇮🇳</span><div><b>{t.impact}</b><small>{t.ok}</small></div></div>
      </aside>
      <div className="dashboard-content">
        <div className="welcome-row"><div><span className="eyebrow">{t.dashboard}</span><h1>{t.welcome}, {user.name} 👋</h1><p>{t.pick}</p></div><div className="user-avatar" aria-label={user.name}>{user.name?.[0]?.toUpperCase() || "G"}</div></div>
        <div className="dashboard-banner"><div><span className="eyebrow">{t.impact}</span><h2>{t.tag}</h2><p>{t.sub}</p>        <span className="banner-motto">{t.motto}</span></div><div className="banner-scene" aria-hidden="true"><span>☀</span><b>🌳</b><i>🌾</i><strong>🚜</strong><em>🌾</em></div></div>
        <div className="dashboard-section-title"><div><span className="eyebrow">{t.features}</span><h2>{t.pick}</h2></div></div>
        <div className="cards">
          {Object.entries(A).map(([k, a]) => (
            <button key={k} className={`card pick ${a.cls}`} onClick={() => onPick(k)}>
              <span className="ico">{a.icon}</span><span className="card-arrow">↗</span><h2>{a.t} AI</h2><b>{t[k === "farm" ? "farmLabel" : "nyLabel"]}</b><p>{t[a.d]}</p><span className="card-link">{t.getStarted} →</span>
            </button>
          ))}
        </div>
        <div className="dashboard-bottom">
          <section className="activity-card"><div className="panel-heading"><h3>{t.recent}</h3><button className="text-button" onClick={onHistory}>{t.viewAll} →</button></div><button className="activity-row" onClick={() => onPick("farm")}><span>🌾</span><div><b>{t.farmT}</b><small>{t.farmD}</small></div><i>→</i></button><button className="activity-row" onClick={() => onPick("nyaya")}><span>⚖️</span><div><b>{t.nyT}</b><small>{t.nyD}</small></div><i>→</i></button></section>
          <section className="quick-card"><h3>{t.quickLinks}</h3><div className="quick-grid"><button onClick={() => onPick("nyaya")}><span>🏛️</span>{t.schemes}</button><button onClick={() => onPick("farm")}><span>☎️</span>{t.helpline}</button><button onClick={() => onPick("nyaya")}><span>📣</span>{t.notices}</button></div></section>
        </div>
        <div className="help-strip"><span>🟢</span><b>{t.help}</b><span>{t.helpline}: 1800-123-456</span><button onClick={() => onPick("farm")}>🎙️ {t.voice}</button></div>
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
