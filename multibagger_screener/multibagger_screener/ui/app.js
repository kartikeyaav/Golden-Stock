/* Golden Stock — v7 interface (2026-09-25).

   ONE QUESTION PER SCREEN.
     Today      what do I do today?          (buy signals, positions, pivots)
     Setups     what is about to break out?  (the evidence-backed pipeline)
     Screener   what is the whole universe doing?
     Portfolio  how are my positions and the paper book?
     Research   why? (AI memos, committee, themes, news, policy)
     Track record  is any of this working?   (gate, forward record, backtest)
     Penny lab  the separate, unvalidated nano-cap research surface
     System     is the machine healthy?

   The ordering of every list follows the evidence, not the available data:
   a fired trigger outranks a base, a base outranks an uptrend, and the
   research score is a tie-breaker and an exclusion tool, never the headline.
   Nothing on this page places an order, gates a signal or sizes a trade.
*/
"use strict";

/* ====================================================================== data */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
const D = JSON.parse($("#d-core").textContent || "{}");
const X = D.v7 || {};
const _lazy = {};
function lazy(name) {
  if (!(name in _lazy)) {
    const el = document.getElementById("d-" + name);
    try { _lazy[name] = el ? JSON.parse(el.textContent || "null") : null; } catch (e) { _lazy[name] = null; }
  }
  return _lazy[name];
}
const detailOf = s => (lazy("details") || {})[s] || null;
const ohlcOf = s => (lazy("ohlc") || {})[s] || null;
const fundOf = s => (lazy("fund") || {})[s] || null;
const archiveNewsOf = s => (lazy("news") || {})[s] || [];

const ROWS = D.rows || [];
const rowBy = Object.fromEntries(ROWS.map(r => [r.sym, r]));
const SETUPS = (X.setups && X.setups.rows) || [];
const setupBy = Object.fromEntries(SETUPS.map(r => [r.sym, r]));
const verdictBy = {};
(D.verdict_items || []).forEach(v => { if (!verdictBy[v.sym]) verdictBy[v.sym] = v; });
const pickBy = Object.fromEntries(((D.ai_picks || {}).picks || []).map(p => [p.symbol, p]));
const actBy = {};
(D.actionable || []).forEach(a => { if (!actBy[a.sym]) actBy[a.sym] = a; });
const survBy = D.surv || {};
const newsMem = (D.news_mem && D.news_mem.syms) || {};
/* Paper books only. Personal holdings are never shipped to this page
   (user decision 2026-09-25) — the builder does not read them at all. */
const POS = X.positions_v7 || { paper: [] };
const MC = X.momentum || {};                       // momentum-core paper sleeve
const RD = X.radar || {};                          // whole-market multibagger radar
const posBy = {};
(POS.paper || []).forEach(p => { (posBy[p.sym] = posBy[p.sym] || []).push(p); });
const MC_LAST = (MC.rebalances || []).slice(-1)[0] || null;
const DEALS = X.deals || {};
function dealChip(sym) {
  const d = (DEALS.net90 || {})[sym];
  if (!d || !isNum(d.net) || Math.abs(d.net) < 1e7) return "";
  const buy = d.net > 0;
  return `<span class="chip sm ${buy ? "info" : "risk"}" data-tip="${esc((buy ? "Named net buying" : "Named net selling") + " in bulk/block deals over 90 days: " + inrShort(Math.abs(d.net)) + (d.buyers && d.buyers.length ? ". Buyers: " + d.buyers.join(", ") : "") + ". Same-session buy+sell churn excluded.")}">${buy ? "bulk buy" : "bulk sell"}</span>`;
}
const coreHeld = new Set(Object.keys((MC_LAST && MC_LAST.holdings_after) || {}));
const corePreview = new Set(((MC.preview || {}).targets || []).map(t => t.sym));
const themeBy = {};
((D.themes || {}).themes || []).forEach(t => (t.leaders || []).forEach(l => { (themeBy[l.sym] = themeBy[l.sym] || []).push(t.name); }));
const VOC = D.vocab || { tags: {}, tagtips: {} };
const CAPITAL = D.capital || 1000000;

/* ===================================================================== utils */
const esc = v => String(v == null ? "" : v).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const isNum = v => typeof v === "number" && isFinite(v);
const nf0 = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
const nf2 = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
function px(v) { return isNum(v) ? "₹" + (Math.abs(v) >= 1000 ? nf0.format(v) : nf2.format(v)) : "—"; }
function inr(v) { return isNum(v) ? (v < 0 ? "−₹" : "₹") + nf0.format(Math.abs(v)) : "—"; }
function inrShort(v) {
  if (!isNum(v)) return "—";
  const a = Math.abs(v), s = v < 0 ? "−" : "";
  if (a >= 1e7) return s + "₹" + (a / 1e7).toFixed(2) + " Cr";
  if (a >= 1e5) return s + "₹" + (a / 1e5).toFixed(2) + " L";
  if (a >= 1e3) return s + "₹" + (a / 1e3).toFixed(1) + "k";
  return s + "₹" + a.toFixed(0);
}
function pct(v, dp = 1, sign = true) { return isNum(v) ? (sign && v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(dp) + "%" : "—"; }
function rr(v, dp = 2) { return isNum(v) ? (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(dp) + "R" : "—"; }
function num(v, dp = 0) { return isNum(v) ? (dp ? v.toFixed(dp) : nf0.format(v)) : "—"; }
function volFmt(v) { if (!isNum(v)) return "—"; if (v >= 1e7) return (v / 1e7).toFixed(1) + " Cr"; if (v >= 1e5) return (v / 1e5).toFixed(1) + " L"; if (v >= 1e3) return (v / 1e3).toFixed(0) + "k"; return String(v); }
const cls = v => isNum(v) ? (v > 0 ? "pos" : v < 0 ? "neg" : "") : "";
function dateLabel(s) {
  if (!s) return "—";
  const d = new Date(String(s).slice(0, 10) + "T00:00:00");
  if (isNaN(d)) return esc(s);
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}
function dayName(s) {
  const d = new Date(String(s).slice(0, 10) + "T00:00:00");
  return isNaN(d) ? "" : d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
}
function daysSince(s) {
  const d = new Date(String(s).slice(0, 10) + "T00:00:00");
  return isNaN(d) ? null : Math.round((Date.now() - d.getTime()) / 864e5);
}
function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
function stageWord(t) { return VOC.tags && VOC.tags[t] || t || "—"; }
function stageChip(t) { return t ? `<span class="tag-stage stage-${esc(t)}" data-tip="${esc(VOC.tagtips && VOC.tagtips[t] || "")}">${esc(stageWord(t))}</span>` : `<span class="faint">—</span>`; }
const SETUP_WORD = { "VALIDATED": "Breakout fired", "VALIDATED (EXTENDED)": "Fired · extended", "AWAITING TRIGGER": "Base ready", "NO VCP BASE": "No base", "EP EVENT": "Gap-up (EP)" };
function setupChip(st) {
  const c = st === "VALIDATED" ? "buy" : st === "EP EVENT" ? "ep" : st === "AWAITING TRIGGER" ? "watch" : st === "VALIDATED (EXTENDED)" ? "watch" : "ghost";
  return st ? `<span class="chip sm ${c}">${esc(SETUP_WORD[st] || st)}</span>` : `<span class="faint">—</span>`;
}
function verdictChip(v, withDate) {
  if (!v) return "";
  const c = v.verdict === "BUY" ? "buy" : v.verdict === "SKIP" ? "risk" : v.verdict === "WAIT" ? "watch" : "ghost";
  return `<span class="chip sm ${c}" data-tip="${esc("AI analyst: " + (v.why || ""))}">AI ${esc(v.verdict)}${v.conv ? " · " + esc(v.conv) : ""}${withDate && v.stamp ? " · " + dateLabel(v.stamp) : ""}</span>`;
}
function survChips(sym) {
  const s = survBy[sym];
  if (!s || !s.flags) return "";
  return s.flags.map(f => `<span class="chip sm risk" data-tip="${esc(f.detail + " — " + f.why)}">${esc(f.code)}</span>`).join("");
}
function info(tip) { return `<span class="info-i" data-tip="${esc(tip)}">?</span>`; }
function spark(vals, w = 96, h = 28, forceColor) {
  const v = (vals || []).filter(isNum);
  if (v.length < 3) return `<svg class="spark" width="${w}" height="${h}"></svg>`;
  const mn = Math.min(...v), mx = Math.max(...v), rg = (mx - mn) || 1;
  const pts = v.map((x, i) => `${(i / (v.length - 1) * (w - 2) + 1).toFixed(1)},${(h - 2 - (x - mn) / rg * (h - 4)).toFixed(1)}`).join(" ");
  const col = forceColor || (v[v.length - 1] >= v[0] ? css("--buy") : css("--risk"));
  return `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true"><polyline fill="none" stroke="${col}" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" points="${pts}"/></svg>`;
}
function areaSpark(pairs, w = 260, h = 56, color) {
  const v = (pairs || []).map(p => p[1]).filter(isNum);
  if (v.length < 3) return "";
  const mn = Math.min(...v), mx = Math.max(...v), rg = (mx - mn) || 1;
  const xy = v.map((x, i) => [i / (v.length - 1) * w, h - 3 - (x - mn) / rg * (h - 8)]);
  const line = xy.map(p => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ");
  const col = color || css("--info");
  return `<svg width="100%" height="${h}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true">
    <polygon points="0,${h} ${line} ${w},${h}" fill="${col}" opacity=".10"/><polyline points="${line}" fill="none" stroke="${col}" stroke-width="1.6" vector-effect="non-scaling-stroke"/></svg>`;
}
function meter(frac, kind = "") { const p = Math.max(0, Math.min(1, frac || 0)) * 100; return `<div class="meter ${kind}"><i style="width:${p.toFixed(1)}%"></i></div>`; }
function toast(msg) { const t = $("#toast"); t.textContent = msg; t.classList.add("on"); clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove("on"), 2200); }
async function copyText(text, label) {
  try { await navigator.clipboard.writeText(text); toast(label || "Copied"); }
  catch (e) {
    const ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); toast(label || "Copied"); } catch (e2) { toast("Copy failed — select and copy manually"); }
    ta.remove();
  }
}
function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } return null; }
function closesOf(sym) { return (D.closes || {})[sym] || []; }
function riskShare(plan) { return plan && isNum(plan.risk) ? plan.risk / CAPITAL * 100 : null; }

/* ===================================================================== icons */
const I = {
  today: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/></svg>',
  setups: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 17l5-5 4 3 8-9"/><path d="M15 6h5v5"/></svg>',
  screener: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M4 6h16M7 12h10M10 18h4"/></svg>',
  portfolio: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>',
  research: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M18.5 15.5l.7 1.8 1.8.7-1.8.7-.7 1.8-.7-1.8-1.8-.7 1.8-.7z"/></svg>',
  record: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 12l2 2 4-4"/><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/></svg>',
  penny: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="8"/><path d="M12 8v8M9.5 10h4a1.8 1.8 0 010 3.6h-4"/></svg>',
  system: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.8-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 01-4 0v-.1a1.7 1.7 0 00-1.1-1.5 1.7 1.7 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.8 1.7 1.7 0 00-1.5-1H3a2 2 0 010-4h.1a1.7 1.7 0 001.5-1.1 1.7 1.7 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.8.3H9a1.7 1.7 0 001-1.5V3a2 2 0 014 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.8V9a1.7 1.7 0 001.5 1H21a2 2 0 010 4h-.1a1.7 1.7 0 00-1.5 1z"/></svg>',
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>',
  sun: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
  moon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z"/></svg>',
  close: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>',
  left: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>',
  right: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6"/></svg>',
  copy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 012-2h10"/></svg>',
  more: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/></svg>',
};

/* ==================================================================== routes */
const PAGES = [
  { id: "today", label: "Today", group: "Act" },
  { id: "setups", label: "Setups", group: "Act" },
  { id: "portfolio", label: "Paper portfolio", group: "Act" },
  { id: "screener", label: "Screener", group: "Explore" },
  { id: "research", label: "Research", group: "Explore" },
  { id: "record", label: "Track record", group: "Verify" },
  { id: "penny", label: "Penny lab", group: "Explore", hidden: () => !D.penny },
  { id: "system", label: "System", group: "Verify" },
];
const S = {
  page: "today", sub: null,
  stock: null, sheetTab: "chart", ctx: [],
  screener: { q: "", view: "all", ind: "", tier: "", sort: "setup", dir: -1, limit: 150, map: false, hideVeto: false },
  setups: { view: "ready", sel: 0 },
  research: "analyst",
  record: "gate",
  penny: { q: "", arm: "", showVeto: false, sort: "score", dir: -1 },
  chartRange: "6M",
};

function parseHash() {
  const h = (location.hash || "").replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  return h;
}
function go(page, sub) { location.hash = "#/" + page + (sub ? "/" + encodeURIComponent(sub) : ""); }
function onRoute() {
  const h = parseHash();
  if (h[0] === "stock" && h[1]) {
    openStock(h[1], null, true);
    if (!$("#main").dataset.rendered) renderPage();
    return;
  }
  closeSheet(true);
  const id = PAGES.some(p => p.id === h[0]) ? h[0] : "today";
  S.page = id; S.sub = h[1] || null;
  if (id === "research" && S.sub) S.research = S.sub;
  if (id === "record" && S.sub) S.record = S.sub;
  renderShell();
  renderPage();
  window.scrollTo(0, 0);
}

/* ===================================================================== shell */
function healthSummary() {
  const h = D.health || [];
  const bad = h.filter(x => x.state === "fail"), warn = h.filter(x => x.state === "warn");
  return { state: bad.length ? "fail" : warn.length ? "warn" : "ok", bad, warn };
}
function priceSession() {
  const p = (D.health || []).find(x => x.k === "prices");
  return (p && p.session) || D.price_date || "";
}
function regime() {
  const b = D.breadth_pct;
  const def = !!D.defensive;
  return { breadth: b, defensive: def, word: def ? "Defensive" : "Normal", size: def ? "Half size" : "Full size" };
}
function renderShell() {
  const rail = $("#rail");
  const groups = {};
  PAGES.filter(p => !(p.hidden && p.hidden())).forEach(p => (groups[p.group] = groups[p.group] || []).push(p));
  const counts = {
    today: buySignals().length + attention().length,
    setups: readySetups().length,
  };
  rail.innerHTML = `
    <div class="brand"><div class="brand-mark">G</div><div><div class="brand-name">Golden Stock</div><div class="brand-sub">NSE small &amp; mid-cap desk</div></div></div>
    <button class="search-btn" id="railsearch">${I.search}<span>Search stocks</span><kbd>Ctrl K</kbd></button>
    ${Object.entries(groups).map(([g, ps]) => `<div class="nav-group">${g}</div>` + ps.map(p => `
      <button class="nav-item ${S.page === p.id ? "on" : ""}" data-go="${p.id}">${I[p.id] || ""}<span>${p.label}</span>
      ${counts[p.id] ? `<span class="badge-count chip sm ${p.id === "today" ? "buy" : "watch"}">${counts[p.id]}</span>` : ""}</button>`).join("")).join("")}
    <div class="rail-foot">
      <div class="row"><span class="dot ${healthSummary().state}"></span><span>Data: prices to ${dateLabel(priceSession())}</span></div>
      <div class="row faint">Built ${esc(D.generated || "")}</div>
    </div>`;
  const rg = regime(), gate = D.gate || {}, coh = gate.cohort || {}, hs = healthSummary();
  const title = (PAGES.find(p => p.id === S.page) || {}).label || "";
  $("#topbar").innerHTML = `
    <h1>${esc(title)}</h1>
    <span class="spacer"></span>
    <span class="pill hide-xs" data-tip="Market regime — the breadth rule that sizes every trade: half risk when fewer than half of the watched stocks close above their own 200-day average."><span class="dot ${rg.defensive ? "warn" : "ok"}"></span>${esc(rg.word)} · ${isNum(rg.breadth) ? rg.breadth.toFixed(0) + "% above 200-DMA" : "breadth n/a"}</span>
    <button class="pill hide-sm" data-go="record" data-tip="Capital gate: the pre-registered test that decides whether real money is ever deployed. Needs 40 qualifying signals.">Gate ${num(coh.n_qualifying)}/${num((gate.required || {}).min_signals || 40)}</button>
    <button class="pill" data-go="system" data-tip="Freshness of every subsystem against its own cadence."><span class="dot ${hs.state}"></span>${hs.state === "ok" ? "All systems fresh" : (hs.bad.length ? hs.bad.length + " failing" : hs.warn.length + " stale")}</button>
    <button class="icon-btn" id="themebtn" aria-label="Toggle light or dark theme">${document.documentElement.dataset.theme === "light" ? I.moon : I.sun}</button>`;
  const bn = [["today", "Today"], ["setups", "Setups"], ["portfolio", "Paper"], ["screener", "Screener"], ["more", "More"]];
  $("#bottomnav").innerHTML = bn.map(([id, l]) => `<button data-go="${id}" class="${S.page === id || (id === "more" && ["research", "record", "penny", "system"].includes(S.page)) ? "on" : ""}">${I[id] || I.more}<span>${l}</span></button>`).join("");
}

/* ======================================================= derived collections */
let _buy = null;
/* A buy signal is only a buy while its own stop is intact. The journal's
   "ACTIONABLE" status retires a gap-up only when the chart turns BROKEN, so a
   pivot that fired, filled and hit its stop the next morning (OPTIEMUS,
   2026-09-24) still read as a live buy. Lowest low since the signal vs the
   plan's stop decides it here. */
function stoppedSince(a) {
  const plan = planOf(a.sym), data = ohlcOf(a.sym);
  if (!plan || plan.skip || !isNum(plan.stop) || !data) return false;
  const since = (D.scorecard || []).find(r => r.sym === a.sym && (r.kind === a.kind));
  const from = since ? String(since.d).slice(0, 10) : null;
  if (!from) return false;
  const after = data.filter(r => r[0] > from);
  return after.length > 0 && Math.min(...after.map(r => r[3])) <= plan.stop;
}
function buySignals() {
  if (_buy) return _buy;
  _buy = (D.actionable || []).filter(a => (a.dokind === "act" || a.dokind === "ep") && a.status === "ACTIONABLE" && !stoppedSince(a));
  return _buy;
}
function attention() {
  return (POS.paper || []).filter(p => p.urgent && p.urgent.length);
}
function readySetups() { return SETUPS.filter(s => s.status === "AWAITING TRIGGER" && s.tag === "CONFIRMED" && !s.veto); }
function formingSetups() { return SETUPS.filter(s => s.status === "AWAITING TRIGGER" && s.tag !== "CONFIRMED"); }
function recentTriggers() {
  return (D.actionable || []).filter(a => ["act", "ep", "warn"].includes(a.dokind) || a.trigger === "VALIDATED" || a.trigger === "EP EVENT");
}
function heldSyms() { return new Set([...(POS.paper || []).map(p => p.sym), ...coreHeld]); }
function nextRebalanceLabel() {
  const d = new Date(String((MC.preview || {}).asof || priceSession() || "").slice(0, 10) + "T00:00:00");
  if (isNaN(d)) return "the first session of next month";
  const n = new Date(d.getFullYear(), d.getMonth() + 1, 1);
  return "the first session of " + n.toLocaleDateString("en-IN", { month: "long" });
}

/* ===================================================================== pages */
function renderPage() {
  const m = $("#main");
  m.dataset.rendered = "1";
  _prevCharts.forEach(c => { try { c.remove(); } catch (e) { } });
  _prevCharts = [];
  if (_pageCharts) { _pageCharts.forEach(c => { try { c.remove(); } catch (e) { } }); }
  _pageCharts = [];
  const fn = { today: pageToday, setups: pageSetups, screener: pageScreener, portfolio: pagePortfolio, research: pageResearch, record: pageRecord, penny: pagePenny, system: pageSystem }[S.page] || pageToday;
  m.innerHTML = `<div class="fade-in">${fn()}</div>` + footer();
  afterRender();
}
function footer() {
  return `<div class="foot"><span>Decision support only — not investment advice. Execution is always yours.</span>
    <span>Prices: Yahoo daily + NSE bhavcopy · Fundamentals: screener.in · Filings: NSE</span>
    <a href="dashboard_classic.html">Classic dashboard</a></div>`;
}
const AFTER = [];
function afterRender() { while (AFTER.length) { try { AFTER.shift()(); } catch (e) { console.error(e); } } }

/* ------------------------------------------------------------------- TODAY */
function pageToday() {
  const rg = regime(), gate = D.gate || {}, coh = gate.cohort || {}, req = gate.required || {};
  const buys = buySignals(), att = attention(), ready = readySetups();
  const breadthHist = ((X.market || {}).breadth || []).slice(-130);
  const session = priceSession();
  const pv = MC.preview || {}, mcNav = MC.nav || [], cmp = MC.compare || {};
  return `
  <div class="page-head"><div>
    <h2>What to do today</h2>
    <div class="sub">Prices as of the ${esc(dayName(session))} close · last scan ${esc(D.scan_date || "—")}</div>
  </div></div>

  <div class="kpis" style="margin-bottom:18px">
    <div class="kpi" data-tip="The breadth rule sizes every trade: risk halves when fewer than 50% of the watched stocks close above their 200-day average. Tested and adopted 2026-07-19.">
      <div class="label"><span class="dot ${rg.defensive ? "warn" : "ok"}"></span>Market</div>
      <div class="value text">${esc(rg.word)} · ${esc(rg.size)}</div>
      <div class="note">${isNum(rg.breadth) ? rg.breadth.toFixed(0) + "% of stocks above their 200-DMA" : "breadth unavailable"}</div>
      <div style="margin-top:8px">${areaSpark(breadthHist, 260, 34, rg.defensive ? css("--watch") : css("--buy"))}</div>
    </div>
    <div class="kpi" data-tip="Breakout triggers and gap-up episodic pivots from the last 7 days that are still valid. This is what the system is built to act on.">
      <div class="label">Buy signals</div>
      <div class="value ${buys.length ? "pos" : ""}">${buys.length}</div>
      <div class="note">${buys.length ? "valid now — plans below" : "none valid right now (normal)"}</div>
    </div>
    <div class="kpi" data-tip="The momentum core: the top 20 stocks by volatility-adjusted 6- and 12-month momentum, rebalanced monthly at the next open. Pre-registered 2026-09-25 as the core of one book with the breakout trades; tracked forward on paper.">
      <div class="label">Momentum core</div>
      ${mcNav.length ? `<div class="value ${cls(cmp.sleeve)}">${pct(cmp.sleeve)}</div>
        <div class="note">since ${esc(dateLabel(mcNav[0][0]))} · universe ${pct(cmp.universe_ew)}</div>`
      : `<div class="value text">Starts ${esc(nextRebalanceLabel().replace("the first session of ", "1 "))}</div>
        <div class="note">${(pv.targets || []).length} names at ${Math.round((pv.exposure || 1) * 100)}% invested, if it rebalanced tonight</div>`}
    </div>
    <div class="kpi" data-tip="The pre-registered capital gate: 40 qualifying signals at ≥50% of the backtest's age-matched expectancy, beating the momentum-quality ETF, by 2026-12-31. Real money waits for it.">
      <div class="label">Capital gate</div>
      <div class="value">${num(coh.n_qualifying)}<span class="muted" style="font-size:15px">/${num(req.min_signals || 40)}</span></div>
      <div class="note">${isNum(coh.expectancy_r) ? rr(coh.expectancy_r) + " vs " + rr(coh.required_expectancy_r) + " needed" : "accruing"}</div>
      <div style="margin-top:8px">${meter((coh.n_qualifying || 0) / (req.min_signals || 40), "info")}</div>
    </div>
  </div>

  <div class="grid grid-main">
    <div>
      <div class="section-title">Buy signals<span class="line"></span></div>
      ${buys.length ? `<div class="action-list">${buys.map(buyCard).join("")}</div>` : emptyBuys()}
    </div>
    <div>
      <div class="section-title">Paper portfolio<span class="line"></span></div>
      ${paperPortfolioCard()}
    </div>
  </div>

  <div class="section-title" style="margin-top:28px">Ready to break out <span class="chip sm watch">${ready.length}</span>${info("Uptrend names with a live volatility-contraction base. The validated entry is a CLOSE above the pivot on at least 1.5× average volume. Set a price alert at the pivot, and if it trips, check the volume near 3:15 PM — buying on the breakout day's close is what the backtest measured; waiting for the next morning cost about 10 points of CAGR in the 2026-09-25 re-run.")}<span class="line"></span>
    <button class="btn sm" data-copy-alerts="today">${I.copy}Copy alert list</button></div>
  ${readyTable(ready.slice(0, 10), false)}
  ${ready.length > 10 ? `<div style="margin-top:8px"><button class="btn link" data-go="setups">All ${ready.length} ready setups →</button></div>` : ""}

  ${radarSection()}

  <div class="grid grid-2" style="margin-top:28px">
    <div>
      <div class="section-title">Market pulse<span class="line"></span></div>
      ${marketPulseCard()}
    </div>
    <div>${headsUpCard() || `<div class="section-title">Heads-up<span class="line"></span></div><div class="empty">No negative filing or exchange-surveillance flag on anything in the paper portfolio or about to be bought.</div>`}</div>
  </div>`;
}
/* The whole-market multibagger radar (scripts/multibagger_radar.py): the three
   signals that raised the odds of a stock tripling within a year in BOTH halves
   of 2005-2026 on the survivorship-free NSE panel. A research watchlist under
   forward test — never presented as a buy list. */
const RADAR_WORD = { H7: "Power play", H9: "RS leader", H14: "Discovery" };
const RADAR_TIP = {
  H7: "Up 90%+ within 40 sessions with no pullback deeper than 25%, closing at a new high — often the surge itself, sometimes the break of a short flag after it.",
  H9: "6-month AND 12-month return both in the top 10% of the liquid market — the day it first got there.",
  H14: "Daily traded value rose from the market's bottom half to its top quarter within 60 sessions — new money arriving.",
};
function radarSection() {
  const rows = RD.rows || [];
  if (!RD.asof) return "";
  const R = RD.research || {};
  const odds = Object.entries(RADAR_WORD).filter(([k]) => R[k] && isNum(R[k].tripled_within_1y_pct))
    .map(([k, w]) => `${w}: <b>${num(R[k].tripled_within_1y_pct, 1)}%</b> tripled within a year (all liquid stocks ${num(R[k].universe_pct, 1)}%)`).join(" · ");
  const body = rows.length ? `<div class="card flush"><div class="table-wrap"><table class="t"><thead><tr><th>Stock</th><th>Signal</th><th class="r">6 months</th><th class="r">12 months</th><th class="r hide-sm" data-tip="6-month return percentile in the liquid market (100 = strongest).">RS</th><th class="r hide-sm">From 52-wk high</th><th class="r hide-sm" data-tip="Median daily traded value, last 20 sessions.">Traded / day</th></tr></thead>
    <tbody>${rows.slice(0, 15).map(r => `<tr ${rowBy[r.sym] ? `data-sym="${esc(r.sym)}"` : ""}><td><div class="cell-sym"><span class="sym">${esc(r.sym)}</span><span class="co">${esc((rowBy[r.sym] || {}).company || "outside the scanned universe")}</span></div></td>
      <td>${Object.entries(r.signals || {}).map(([k, d]) => `<span class="chip sm ${k === "H7" ? "buy" : k === "H14" ? "ai" : "watch"}" data-tip="${esc(RADAR_TIP[k] + " Fired " + d + ".")}">${esc(RADAR_WORD[k] || k)}</span>`).join(" ")}</td>
      <td class="r num ${cls(r.ret_6m_pct)}">${pct(r.ret_6m_pct, 0)}</td><td class="r num ${cls(r.ret_12m_pct)}">${pct(r.ret_12m_pct, 0)}</td>
      <td class="r num hide-sm">${num(r.rs_pct, 0)}</td><td class="r num hide-sm">${pct(r.off_52w_high_pct, 1)}</td><td class="r num hide-sm">₹${num(r.traded_value_cr, 1)} Cr</td></tr>`).join("")}</tbody></table></div></div>`
    : `<div class="empty">No power play, new RS leader or discovery signal in the last ${num(RD.window_sessions)} sessions.</div>`;
  return `<div class="section-title" style="margin-top:28px">Multibagger radar <span class="chip sm">${rows.length}</span>${info("The whole NSE market (" + num(RD.universe_size) + " liquid stocks, not just the scanned universe), rebuilt nightly from the exchange's own files. These three signals raised the chance of a stock tripling within a year in BOTH 2005–2015 and 2016–2026 on a survivorship-free panel; the system's own VCP breakout barely did. Even the best was followed by a triple only about 1 time in 10 — a list to research, not to buy blindly.")}<span class="line"></span><span class="hint">as of ${esc(RD.asof)}</span></div>
    ${body}
    ${odds ? `<div class="hint" style="margin-top:8px">Measured 2016–2026: ${odds}.</div>` : ""}`;
}
function emptyBuys() {
  const recent = recentTriggers().filter(a => !(a.dokind === "act" || a.dokind === "ep") || a.status !== "ACTIONABLE");
  return `<div class="empty"><b>No valid buy signal right now.</b> That is normal: the backtest averaged about 2–3 entries a month, with gaps of several weeks. The closest setups are listed under <b>Ready to break out</b>.
    ${recent.length ? `<div style="margin-top:8px">${recent.length} recent trigger${recent.length > 1 ? "s have" : " has"} run away or faded — <a href="#/setups/triggered">see them</a>.</div>` : ""}</div>`;
}
function planOf(sym) {
  const d = detailOf(sym);
  const p = d && d.plan;
  if (!p || p.skip) return p || null;
  const risk = isNum(p.capital_at_risk) ? p.capital_at_risk : (isNum(p.shares_total) && isNum(p.risk_per_share) ? p.shares_total * p.risk_per_share : null);
  return { entry: p.entry_price, stop: p.stop_loss_price, shares: p.shares_total, t: p.shares_trading_lot, c: p.shares_core_lot, risk,
           stop_pct: isNum(p.entry_price) && isNum(p.stop_loss_price) ? (1 - p.stop_loss_price / p.entry_price) * 100 : null };
}
function buyCard(a) {
  const r = rowBy[a.sym] || {}, v = verdictBy[a.sym], plan = planOf(a.sym), st = setupBy[a.sym];
  const isEP = a.dokind === "ep";
  let zone = "";
  if (isEP && isNum(a.alert_px) && isNum(a.now_px)) {
    const ext = (a.now_px / a.alert_px - 1) * 100;
    zone = ext > 5 ? `<span class="chip sm watch">${pct(ext)} past the gap-day close — don't chase</span>`
      : ext < -3 ? `<span class="chip sm watch">${pct(ext)} below the gap-day close — the gap is being given back</span>`
      : `<span class="chip sm buy">Near the gap-day close ${px(a.alert_px)}</span>`;
  } else if (st && isNum(st.pivot) && isNum(a.now_px)) {
    const ext = (a.now_px / st.pivot - 1) * 100;
    zone = ext <= 5 ? `<span class="chip sm buy">In the buy zone (≤5% above pivot ${px(st.pivot)})</span>` : `<span class="chip sm watch">${pct(ext)} above the pivot — past the buy zone</span>`;
  }
  const ch = closesOf(a.sym).slice(-60);
  return `<div class="acard ${isEP ? "ep" : "buy"}" data-sym="${esc(a.sym)}">
    <div>
      <div class="top"><span class="title">${esc(a.sym)}</span>
        <span class="chip sm ${isEP ? "ep" : "buy"}">${isEP ? "Gap-up (EP)" : "Breakout"}</span>
        ${verdictChip(v)} ${survChips(a.sym)} ${a.n > 1 ? `<span class="chip sm ghost">alerted ${a.n}×</span>` : ""}</div>
      <div class="desc">${esc(r.company || "")}${r.ind ? " · " + esc(r.ind) : ""} · signalled ${esc(a.d)} at ${px(a.alert_px)} · now ${px(a.now_px)} <span class="${cls(a.chg)}">${pct(a.chg)}</span></div>
      ${zone ? `<div style="margin-top:8px">${zone}</div>` : ""}
      ${plan && !plan.skip ? `<div class="plan">
        <div><div class="k">Entry ≈</div><div class="v">${px(plan.entry)}</div></div>
        <div><div class="k">Stop</div><div class="v neg">${px(plan.stop)} <span class="muted" style="font-size:11px">(${pct(-plan.stop_pct)})</span></div></div>
        <div><div class="k">Quantity</div><div class="v">${num(plan.shares)}</div></div>
        <div><div class="k">Risk</div><div class="v">${inr(plan.risk)} <span class="muted" style="font-size:11px">${isNum(riskShare(plan)) ? riskShare(plan).toFixed(2) + "%" : ""}</span></div></div>
      </div>` : plan && plan.skip ? `<div class="why warn">No sized plan: ${esc(plan.skip_reason || "stop wider than the 12% cap")}</div>` : ""}
      ${v && v.why ? `<div class="why"><span class="muted">AI:</span> ${esc(v.why).slice(0, 220)}${v.why.length > 220 ? "…" : ""}</div>` : ""}
    </div>
    <div class="side">${spark(ch, 120, 40)}<button class="btn sm" data-sym="${esc(a.sym)}">Open</button></div>
  </div>`;
}
function readyTable(list, compact) {
  if (!list.length) return `<div class="empty">No uptrend name has a live base right now. Bases take weeks to form; this list refills as they do.</div>`;
  return `<div class="card flush"><div class="table-wrap"><table class="t">
    <thead><tr><th>Stock</th><th class="r">Price</th><th class="r">Pivot</th><th class="r" data-tip="How far price must rise to close above the pivot. Negative = already above it, waiting for volume.">To pivot</th>
    <th class="r hide-sm" data-tip="Shares that must trade on the breakout day (1.5× the 50-day average) — and today's volume as a multiple of that average.">Volume needed</th>
    <th class="r hide-sm">Stop</th><th class="r hide-sm">Qty</th><th class="r">RS</th>${compact ? "" : `<th class="hide-sm">Stage</th><th class="r hide-sm">Score</th>`}</tr></thead>
    <tbody>${list.map(s => `<tr data-sym="${esc(s.sym)}" data-ctx="ready">
      <td><div class="cell-sym"><span class="sym">${esc(s.sym)} ${verdictBy[s.sym] ? verdictChip(verdictBy[s.sym]) : ""} ${pickBy[s.sym] ? '<span class="chip sm ai">Committee pick</span>' : ""} ${corePreview.has(s.sym) ? '<span class="chip sm ghost" data-tip="Also in the momentum top 20.">momentum</span>' : ""} ${dealChip(s.sym)}</span><span class="co">${esc(s.company || "")}</span></div></td>
      <td class="r num">${px(s.px)}</td><td class="r num">${px(s.pivot)}</td>
      <td class="r num ${isNum(s.dist) && s.dist <= 2 ? "pos" : ""}">${pct(s.dist)}</td>
      <td class="r num hide-sm">${volFmt(s.vneed)} <span class="muted">· today ${isNum(s.vr) ? s.vr.toFixed(1) + "×" : "—"}</span></td>
      <td class="r num hide-sm">${s.plan && !s.plan.skip ? px(s.plan.stop) + ` <span class="muted">${pct(-s.plan.stop_pct)}</span>` : `<span class="warn" data-tip="${esc((s.plan || {}).why || "")}">too wide</span>`}</td>
      <td class="r num hide-sm">${s.plan && !s.plan.skip ? num(s.plan.shares) : "—"}</td>
      <td class="r num">${isNum(s.rs) ? s.rs.toFixed(0) : "—"}</td>
      ${compact ? "" : `<td class="hide-sm">${stageChip(s.tag)}</td><td class="r num hide-sm">${isNum(s.score) ? s.score.toFixed(0) : "—"}</td>`}
    </tr>`).join("")}</tbody></table></div></div>`;
}
function alertText(list) {
  const day = dayName(priceSession());
  const lines = list.filter(s => s.plan && !s.plan.skip).map(s =>
    `${s.sym}: alert above ${px(s.pivot)} · buy only on a close above it with volume ≥ ${volFmt(s.vneed)} · stop ${px(s.plan.stop)} · qty ${s.plan.shares} (risk ${inr(s.plan.risk)})`);
  return `Golden Stock — pivot alerts (prices to ${day})\n` + lines.join("\n") + `\n\nThe validated entry is a CLOSE above the pivot on ≥1.5× average volume. A price alert is a prompt to check, not an order.`;
}
function paperPortfolioCard() {
  const paper = POS.paper || [], att = attention(), paperSum = D.paper || {};
  const pv = MC.preview || {}, nav = MC.nav || [], cmp = MC.compare || {};
  let html = `<div class="card">`;
  // 1. the momentum core: what it holds, or what it will buy at the next rebalance
  html += `<div class="lrow" data-go="portfolio"><div><div><span class="sym">Momentum core</span> <span class="chip sm ai">monthly</span></div>`;
  if (nav.length) {
    html += `<div class="meta">${coreHeld.size} names · ${pct(cmp.sleeve)} since ${esc(dateLabel(nav[0][0]))} (universe ${pct(cmp.universe_ew)}, MIDSMALL ${pct(cmp.midsmall)})</div>
      <div class="act">Next rebalance: ${esc(nextRebalanceLabel())}${(pv.adds || []).length ? ` · tonight's ranking would add ${pv.adds.length}, drop ${(pv.drops || []).length}` : ""}</div>`;
  } else {
    html += `<div class="meta">First rebalance at ${esc(nextRebalanceLabel())}'s open — ${(pv.targets || []).length} names at ${Math.round((pv.exposure || 1) * 100)}% invested if the month ended tonight</div>
      <div class="act muted">Top of tonight's ranking: ${(pv.targets || []).slice(0, 5).map(t => esc(t.sym)).join(", ")}…</div>`;
  }
  html += `</div><div class="muted" style="font-size:12px">view →</div></div>`;
  // 2. the breakout paper book: anything a rule is about to act on
  html += `<div class="lrow" data-go="portfolio" style="border-bottom:0"><div><div><span class="sym">Breakout book</span> <span class="chip sm ghost">analyst BUYs</span></div>
      <div class="meta">${paper.length} open · <span class="${cls(paperSum.net)}">${inrShort(paperSum.net)}</span> net (${pct(paperSum.net_pct)})</div></div>
      <div class="muted" style="font-size:12px">view →</div></div>`;
  if (att.length) {
    html += att.slice(0, 5).map(p => `<div class="lrow" data-sym="${esc(p.sym)}">
      <div><div><span class="sym">${esc(p.sym)}</span> <span class="chip sm ghost">paper</span></div>
      <div class="act warn">${esc(p.urgent[0])}</div>
      <div class="meta">stop ${px(p.stop)} · last ${px(p.last)}</div></div>
      <div class="r num ${cls(p.r_now)}" style="text-align:right">${rr(p.r_now)}<div class="meta">${pct(p.pnl_pct)}</div></div></div>`).join("");
  }
  return html + `</div>`;
}
function marketPulseCard() {
  const m = X.market || {};
  const ew = (m.ew || []);
  const nf = (D.nifty || []).map(r => [r[0], r[1]]);
  function chg(series, n) { if (series.length <= n) return null; const a = series[series.length - 1 - n][1], b = series[series.length - 1][1]; return (b / a - 1) * 100; }
  const t = D.tags || {}, tot = Object.values(t).reduce((a, b) => a + b, 0) || 1;
  const segs = [["CONFIRMED", "--buy"], ["EXTENDED", "--watch"], ["ANTICIPATION", "--info"], ["WATCH", "--faint"], ["BROKEN", "--risk"]];
  const themes = ((D.themes || {}).themes || []).filter(x => !x.thin).slice().sort((a, b) => (b.heat || 0) - (a.heat || 0)).slice(0, 4);
  return `<div class="card">
    <div class="pulse" style="grid-template-columns:repeat(2,minmax(0,1fr))">
      <div><div class="k">Small &amp; mid caps ${info("An equal-weight index of every stock this system watches — the market it actually trades, rather than the NIFTY 50.")}</div>
        <div class="v ${cls(chg(ew, 21))}">${pct(chg(ew, 21))}</div><div class="s">1 month · ${pct(chg(ew, 63))} 3 months</div></div>
      <div><div class="k">NIFTY 50</div><div class="v ${cls(chg(nf, 21))}">${pct(chg(nf, 21))}</div><div class="s">1 month · ${pct(chg(nf, 63))} 3 months</div></div>
    </div>
    <div style="margin-top:14px">${areaSpark(ew.slice(-130), 300, 54, css("--info"))}</div>
    <div class="stagebar" style="margin-top:12px">${segs.map(([k, c]) => `<i style="width:${((t[k] || 0) / tot * 100).toFixed(1)}%;background:var(${c})" data-tip="${esc(stageWord(k))}: ${t[k] || 0}"></i>`).join("")}</div>
    <div class="legend">${segs.map(([k, c]) => `<span><i style="background:var(${c})"></i>${esc(stageWord(k))} ${t[k] || 0}</span>`).join("")}</div>
    ${themes.length ? `<div style="margin-top:14px;font-size:12px" class="muted">Hottest themes ${info("Relative heat across 18 cross-industry themes (3-month move, chart breadth, news). A research ranking — tested as an entry filter and rejected, so it changes no trade.")}</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px">${themes.map(x => `<button class="chip" data-go="research" data-sub="themes">${esc(x.name)} <span class="muted">${num(x.heat)}</span></button>`).join("")}</div>` : ""}
  </div>`;
}
function headsUpCard() {
  const held = heldSyms(), buy = new Set(buySignals().map(a => a.sym));
  const items = [];
  Object.entries(newsMem).forEach(([sym, m]) => {
    if (!(held.has(sym) || buy.has(sym)) || !m.n_neg) return;
    const negs = (m.events || []).filter(e => e[1] === "neg");
    const last = negs.length ? negs[negs.length - 1] : null;
    const age = last ? daysSince(last[2]) : null;
    if (age != null && age <= 30) items.push({ sym, text: `${last[0]} filing ${age === 0 ? "today" : age + "d ago"}`, kind: "risk" });
  });
  [...held, ...buy].forEach(sym => { const s = survBy[sym]; if (s && s.flags && s.flags.length) items.push({ sym, text: s.flags.map(f => f.code + " (" + f.detail + ")").join(", "), kind: "watch" }); });
  if (!items.length) return "";
  return `<div><div class="section-title">Heads-up<span class="line"></span></div>
    <div class="card accent-risk">${items.slice(0, 8).map(i => `<div class="lrow" data-sym="${esc(i.sym)}"><div><span class="sym">${esc(i.sym)}</span>
      <div class="act ${i.kind === "risk" ? "neg" : "warn"}">${esc(i.text)}</div></div><div class="muted" style="font-size:12px">${held.has(i.sym) ? "paper portfolio" : "buy signal"}</div></div>`).join("")}
    <div class="meta muted" style="font-size:12px;margin-top:8px">Negative filings and exchange surveillance on names in the paper portfolio or about to be bought. Read the filing before acting.</div></div></div>`;
}

/* ------------------------------------------------------------------ SETUPS */
function setupsList() {
  const v = S.setups.view;
  if (v === "triggered") return recentTriggers().map(a => ({ ...a, _kind: "trig" }));
  if (v === "forming") return formingSetups();
  return readySetups();
}
function pageSetups() {
  if (S.sub && ["ready", "forming", "triggered"].includes(S.sub)) S.setups.view = S.sub;
  const es = (X.event_study || {}).by_status || [];
  const base = es.find(r => r.key === "AWAITING TRIGGER"), noBase = es.find(r => r.key === "NO VCP BASE");
  const list = setupsList();
  S.ctx = list.map(r => r.sym);
  if (S.setups.sel >= list.length) S.setups.sel = 0;
  const counts = { ready: readySetups().length, forming: formingSetups().length, triggered: recentTriggers().length };
  AFTER.push(() => drawSetupPreview());
  return `
  <div class="page-head"><div><h2>Setups</h2>
    <div class="sub">The breakout pipeline: only names with a live base or a fired trigger. Use ↑ ↓ to flip through charts, Enter to open.</div></div></div>
  ${base && noBase ? `<div class="callout info" style="margin-bottom:14px">Why this list: in the forward record, alerts on names <b>with a live base</b> beat the universe by <b>${pct(base.x40)}</b> over 40 sessions (${num(base.b40)}% of them did), against ${pct(noBase.x40)} for uptrend-only alerts. The base is where the edge is.</div>` : ""}
  <div class="toolbar"><div class="seg">
    ${[["ready", "Ready to break out"], ["triggered", "Triggered (7 days)"], ["forming", "Base, trend not confirmed"]].map(([k, l]) => `<button data-setview="${k}" class="${S.setups.view === k ? "on" : ""}">${l}<span class="count">${counts[k]}</span></button>`).join("")}
  </div>${S.setups.view !== "triggered" ? `<button class="btn sm" data-copy-alerts="setups">${I.copy}Copy alert list</button>` : ""}<span class="right">${list.length} names</span></div>
  <div class="split">
    <div class="card flush">${S.setups.view === "triggered" ? triggeredTable(list) : setupsTable(list)}</div>
    <div class="pane-right" id="preview"></div>
  </div>`;
}
function setupsTable(list) {
  if (!list.length) return `<div class="empty" style="margin:14px">Nothing here right now.</div>`;
  return `<div class="table-wrap max"><table class="t" id="setuptbl"><thead><tr><th>Stock</th><th class="r">Price</th><th class="r">Pivot</th><th class="r">To pivot</th><th class="r hide-sm">Vol today</th><th class="r">RS</th><th class="hide-sm">Stage</th><th class="r hide-sm">Score</th></tr></thead>
  <tbody>${list.map((s, i) => `<tr data-idx="${i}" class="${i === S.setups.sel ? "sel" : ""}">
    <td><div class="cell-sym"><span class="sym">${esc(s.sym)}</span><span class="co">${esc(s.company || "")}</span></div></td>
    <td class="r num">${px(s.px)}</td><td class="r num">${px(s.pivot)}</td>
    <td class="r num ${isNum(s.dist) && s.dist <= 2 ? "pos" : ""}">${pct(s.dist)}</td>
    <td class="r num hide-sm">${isNum(s.vr) ? s.vr.toFixed(1) + "×" : "—"}</td>
    <td class="r num">${isNum(s.rs) ? s.rs.toFixed(0) : "—"}</td><td class="hide-sm">${stageChip(s.tag)}</td>
    <td class="r num hide-sm">${isNum(s.score) ? s.score.toFixed(0) : "—"}</td></tr>`).join("")}</tbody></table></div>`;
}
function triggeredTable(list) {
  if (!list.length) return `<div class="empty" style="margin:14px">No trigger in the last 7 days.</div>`;
  return `<div class="table-wrap max"><table class="t" id="setuptbl"><thead><tr><th>Stock</th><th>Type</th><th class="r">Signalled</th><th class="r">Then</th><th class="r">Now</th><th class="r">Move</th><th>Status</th></tr></thead>
  <tbody>${list.map((a, i) => `<tr data-idx="${i}" class="${i === S.setups.sel ? "sel" : ""}">
    <td><div class="cell-sym"><span class="sym">${esc(a.sym)}</span><span class="co">${esc((rowBy[a.sym] || {}).company || "")}</span></div></td>
    <td>${a.dokind === "ep" || a.trigger === "EP EVENT" ? '<span class="chip sm ep">Gap-up</span>' : '<span class="chip sm buy">Breakout</span>'}</td>
    <td class="r">${esc(a.d)}</td><td class="r num">${px(a.alert_px)}</td><td class="r num">${px(a.now_px)}</td>
    <td class="r num ${cls(a.chg)}">${pct(a.chg)}</td>
    <td>${a.status === "ACTIONABLE" ? '<span class="chip sm buy">Valid</span>' : a.status === "RAN AWAY" ? '<span class="chip sm watch">Ran away</span>' : a.status === "VETOED" ? '<span class="chip sm risk">Vetoed</span>' : '<span class="chip sm ghost">Faded</span>'}</td></tr>`).join("")}</tbody></table></div>`;
}
let _prevCharts = [];
function drawSetupPreview() {
  const box = $("#preview");
  _prevCharts.forEach(c => { try { c.remove(); } catch (e) { } });
  _prevCharts = [];
  if (!box) return;
  const list = setupsList();
  const s = list[S.setups.sel];
  if (!s) { box.innerHTML = ""; return; }
  const sym = s.sym, r = rowBy[sym] || {}, st = setupBy[sym], v = verdictBy[sym];
  const plan = st && st.plan && !st.plan.skip ? st.plan : null;
  box.innerHTML = `<div class="card">
    <div class="card-head"><div><h3 style="font-size:18px">${esc(sym)}</h3><div class="co" style="max-width:none">${esc(r.company || "")} · ${esc(r.ind || "")}</div></div>
      <div class="right">${verdictChip(v, true)}<button class="btn sm" data-sym="${esc(sym)}">Open ↗</button></div></div>
    <div class="chart-box" style="height:280px" id="prevchart"></div>
    ${plan ? `<div class="plan-grid" style="margin-top:12px">
      <div class="plan-cell"><div class="k">Buy above</div><div class="v">${px(st.pivot)}</div><div class="s">on ≥ ${volFmt(st.vneed)} shares</div></div>
      <div class="plan-cell"><div class="k">Stop</div><div class="v neg">${px(plan.stop)}</div><div class="s">${pct(-plan.stop_pct)} from entry</div></div>
      <div class="plan-cell"><div class="k">Quantity</div><div class="v">${num(plan.shares)}</div><div class="s">${inrShort(plan.value)} position</div></div>
      <div class="plan-cell"><div class="k">Risk</div><div class="v">${inr(plan.risk)}</div><div class="s">${(plan.risk / CAPITAL * 100).toFixed(2)}% of capital</div></div>
    </div>` : st && st.plan && st.plan.skip ? `<div class="callout watch" style="margin-top:12px">No sized plan: ${esc(st.plan.why)}</div>` : ""}
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:12px">${stageChip(r.tag)} ${setupChip(r.trig)} ${survChips(sym)} ${(themeBy[sym] || []).slice(0, 2).map(t => `<span class="chip sm ghost">${esc(t)}</span>`).join("")}</div>
    ${v ? `<div class="why" style="margin-top:10px;font-size:13px;color:var(--text-2)"><span class="muted">AI analyst:</span> ${esc(v.why)}</div>` : ""}
  </div>`;
  drawCandles($("#prevchart"), sym, { range: "6M", compact: true, bucket: _prevCharts, pivot: st ? st.pivot : null, stop: plan ? plan.stop : null });
}

/* ---------------------------------------------------------------- SCREENER */
const VIEWS = [
  ["all", "All"], ["setup", "With a setup"], ["CONFIRMED", "Uptrend"], ["EXTENDED", "Extended"],
  ["ANTICIPATION", "Basing"], ["WATCH", "Neutral"], ["BROKEN", "Downtrend"],
];
function setupRank(r) { return r.trig === "VALIDATED" ? 0 : r.trig === "AWAITING TRIGGER" ? 1 : r.trig === "VALIDATED (EXTENDED)" ? 2 : 3; }
function screenerRows() {
  const f = S.screener, q = f.q.trim().toLowerCase();
  let rows = ROWS.filter(r => {
    if (q && !(r.sym.toLowerCase().includes(q) || (r.company || "").toLowerCase().includes(q))) return false;
    if (f.view === "setup" && !["VALIDATED", "AWAITING TRIGGER", "VALIDATED (EXTENDED)"].includes(r.trig)) return false;
    if (["CONFIRMED", "EXTENDED", "ANTICIPATION", "WATCH", "BROKEN"].includes(f.view) && r.tag !== f.view) return false;
    if (f.ind && r.ind !== f.ind) return false;
    if (f.tier && r.tier !== f.tier) return false;
    if (f.hideVeto && r.veto) return false;
    return true;
  });
  const k = f.sort, d = f.dir;
  const val = r => k === "setup" ? setupRank(r) * 1000 - (r.rs || 0) : k === "sym" ? r.sym : k === "dist" ? (setupBy[r.sym] ? setupBy[r.sym].dist : null) : r[k];
  rows.sort((a, b) => {
    let x = val(a), y = val(b);
    if (k === "setup") return x - y;
    if (x == null && y == null) return 0; if (x == null) return 1; if (y == null) return -1;
    if (typeof x === "string") return d * x.localeCompare(y);
    return d * (x - y);
  });
  return rows;
}
function pageScreener() {
  const f = S.screener;
  const rows = screenerRows();
  S.ctx = rows.map(r => r.sym);
  const inds = [...new Set(ROWS.map(r => r.ind).filter(Boolean))].sort();
  const cnt = {};
  VIEWS.forEach(([k]) => { cnt[k] = k === "all" ? ROWS.length : k === "setup" ? ROWS.filter(r => ["VALIDATED", "AWAITING TRIGGER", "VALIDATED (EXTENDED)"].includes(r.trig)).length : ROWS.filter(r => r.tag === k).length; });
  const shown = rows.slice(0, f.limit);
  const th = (k, l, extra = "", tip = "") => `<th class="sortable ${extra}" data-sort="${k}" ${tip ? `data-tip="${esc(tip)}"` : ""}>${l}${f.sort === k ? `<span class="arrow">${f.dir > 0 ? "▲" : "▼"}</span>` : ""}</th>`;
  if (f.map) AFTER.push(() => bindMap());
  return `
  <div class="page-head"><div><h2>Screener</h2><div class="sub">Every stock the nightly scan watches. Default order: fired triggers, then live bases, then relative strength.</div></div></div>
  <div class="toolbar">
    <input class="field" id="sq" placeholder="Symbol or company…" value="${esc(f.q)}" style="width:210px">
    <select class="field" id="sind"><option value="">All industries</option>${inds.map(i => `<option ${f.ind === i ? "selected" : ""}>${esc(i)}</option>`).join("")}</select>
    <select class="field" id="stier"><option value="">All sizes</option>${["Micro", "Small", "Mid", "Large"].map(t => `<option value="${t}" ${f.tier === t ? "selected" : ""}>${t} cap</option>`).join("")}</select>
    <label class="muted" style="font-size:12.5px;display:flex;gap:6px;align-items:center"><input type="checkbox" id="sveto" ${f.hideVeto ? "checked" : ""}>Hide vetoed</label>
    <div class="seg" style="margin-left:auto"><button data-map="0" class="${!f.map ? "on" : ""}">Table</button><button data-map="1" class="${f.map ? "on" : ""}">Map</button></div>
  </div>
  <div class="toolbar"><div class="seg" style="flex-wrap:wrap">${VIEWS.map(([k, l]) => `<button data-sview="${k}" class="${f.view === k ? "on" : ""}">${l}<span class="count">${cnt[k]}</span></button>`).join("")}</div>
    <span class="right">${rows.length} match</span></div>
  ${f.map ? universeMap(rows) : `<div class="card flush"><div class="table-wrap max"><table class="t" id="stbl">
    <thead><tr>${th("sym", "Stock")}${th("tag", "Stage")}${th("setup", "Setup", "", "Fired breakout > live base > none. The base is where the forward record shows the edge.")}${th("dist", "To pivot", "r hide-sm", "How far below its pivot a base-ready name sits.")}
      ${th("rs", "RS", "r", "Relative strength percentile: 6- and 12-month return ranked against the whole universe.")}${th("close", "Price", "r")}<th class="hide-sm">120 days</th>
      ${th("tier", "Size", "hide-sm")}${th("ind", "Industry", "hide-sm")}${th("score", "Score", "r hide-sm", "Research score (0–100) from the eight weighted questions. Useful to rule out the worst (vetoed and under-50 names lag the universe); it does not rank the rest — see Track record.")}
      ${th("roce", "ROCE", "r hide-sm")}${th("pe", "P/E", "r hide-sm")}${th("pgttm", "Profit TTM", "r hide-sm")}</tr></thead>
    <tbody>${shown.map(r => { const s = setupBy[r.sym]; return `<tr data-sym="${esc(r.sym)}" data-ctx="screener" class="${r.veto ? "dim" : ""}">
      <td><div class="cell-sym"><span class="sym">${esc(r.sym)}${r.veto ? ' <span class="chip sm risk" data-tip="Vetoed: governance or leverage red flag. Research score capped at 25.">veto</span>' : ""}</span><span class="co">${esc(r.company || "")}</span></div></td>
      <td>${stageChip(r.tag)}</td><td>${setupChip(r.trig)}</td>
      <td class="r num hide-sm">${s && isNum(s.dist) ? pct(s.dist) : ""}</td>
      <td class="r num">${isNum(r.rs) ? r.rs.toFixed(0) : "—"}</td><td class="r num">${px(r.close)}</td>
      <td class="hide-sm">${spark(closesOf(r.sym), 90, 24)}</td>
      <td class="hide-sm muted">${esc(r.tier || "")}</td><td class="hide-sm muted" style="max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(r.ind || "")}</td>
      <td class="r num hide-sm">${isNum(r.score) ? r.score.toFixed(0) : "—"}</td>
      <td class="r num hide-sm">${isNum(r.roce) ? r.roce.toFixed(0) + "%" : "—"}</td><td class="r num hide-sm">${isNum(r.pe) ? r.pe.toFixed(0) : "—"}</td>
      <td class="r num hide-sm ${cls(r.pgttm)}">${isNum(r.pgttm) ? pct(r.pgttm, 0) : "—"}</td></tr>`; }).join("")}</tbody></table></div>
    ${rows.length > shown.length ? `<div style="padding:12px 16px"><button class="btn" id="smore">Show ${Math.min(200, rows.length - shown.length)} more of ${rows.length - shown.length}</button></div>` : ""}</div>`}`;
}
function universeMap(rows) {
  const alerted = new Set((D.actionable || []).map(a => a.sym));
  const col = { CONFIRMED: "--buy", EXTENDED: "--watch", ANTICIPATION: "--info", WATCH: "--surface-3", BROKEN: "--risk" };
  const sorted = rows.slice().sort((a, b) => (b.rs || 0) - (a.rs || 0));
  return `<div class="card"><div class="card-head"><h3>Universe map</h3><span class="hint">Each square is a stock, strongest relative strength first; colour is the chart stage; a ring marks a buy alert in the last 7 days.</span></div>
    <div class="umap" id="umap">${sorted.map(r => `<i data-sym="${esc(r.sym)}" class="${alerted.has(r.sym) ? "alerted" : ""}" style="background:var(${col[r.tag] || "--surface-3"})" data-tip="${esc(r.sym + " · " + stageWord(r.tag) + " · RS " + (isNum(r.rs) ? r.rs.toFixed(0) : "—") + (r.company ? " · " + r.company : ""))}"></i>`).join("")}</div>
    <div class="legend" style="margin-top:12px">${Object.entries(col).map(([k, c]) => `<span><i style="background:var(${c})"></i>${esc(stageWord(k))}</span>`).join("")}</div></div>`;
}
function bindMap() { }

/* --------------------------------------------------------------- PORTFOLIO */
function momentumSection() {
  const pv = MC.preview || {}, nav = MC.nav || [], cmp = MC.compare || {}, book = MC.book || {};
  const targets = pv.targets || [];
  if (nav.length) AFTER.push(() => drawCoreNav());
  const kpis = nav.length ? `
    <div class="kpi"><div class="label">Since ${esc(dateLabel(nav[0][0]))}</div><div class="value ${cls(cmp.sleeve)}">${pct(cmp.sleeve)}</div><div class="note">NAV ${inrShort(nav[nav.length - 1][1])} on a ₹10L paper book</div></div>
    <div class="kpi"><div class="label">Own the universe</div><div class="value sm ${cls(cmp.universe_ew)}">${pct(cmp.universe_ew)}</div><div class="note">equal weight, same dates</div></div>
    <div class="kpi"><div class="label">MIDSMALL ETF</div><div class="value sm ${cls(cmp.midsmall)}">${pct(cmp.midsmall)}</div><div class="note">the investable alternative</div></div>
    <div class="kpi"><div class="label">Invested</div><div class="value sm">${Math.round(((MC_LAST || {}).exposure || 1) * 100)}%</div><div class="note">${coreHeld.size} names · breadth ${num((MC_LAST || {}).breadth)}% at the signal</div></div>`
    : `
    <div class="kpi"><div class="label">First rebalance</div><div class="value text">${esc(nextRebalanceLabel().replace("the first session of ", "1 "))}</div><div class="note">at the open, from the 30 Sep month-end ranking</div></div>
    <div class="kpi"><div class="label">If it rebalanced tonight</div><div class="value sm">${targets.length} names</div><div class="note">${Math.round((pv.exposure || 1) * 100)}% invested · breadth ${num(pv.breadth)}%</div></div>
    <div class="kpi"><div class="label">Eligible</div><div class="value sm">${num(pv.eligible)}</div><div class="note">index names with ≥₹2 Cr daily turnover</div></div>
    <div class="kpi"><div class="label">Backtest, 2020 → 2026</div><div class="value sm pos">+43.6%/yr</div><div class="note">−23.4% worst drawdown, at 0.25% costs</div></div>`;
  const tbl = `<div class="card flush"><div class="card-head"><h3>${nav.length ? "Next rebalance, if the month ended tonight" : "The list the rules would buy tonight"}</h3>
      <span class="hint">as of ${esc(pv.asof || "")}${nav.length ? ` · adds ${(pv.adds || []).length}, drops ${(pv.drops || []).length}` : ""}</span></div>
    <div class="table-wrap"><table class="t"><thead><tr><th class="r">Rank</th><th>Stock</th><th class="r">6 months</th><th class="r">12 months</th><th class="r hide-sm" data-tip="Annualised volatility of daily returns — the score divides by it, so steady strength outranks wild swings.">Volatility</th><th class="r">Price</th><th>Status</th></tr></thead>
    <tbody>${targets.map(t => `<tr data-sym="${esc(t.sym)}" data-ctx="core"><td class="r num">${num(t.rank)}</td>
      <td><div class="cell-sym"><span class="sym">${esc(t.sym)}</span><span class="co">${esc((rowBy[t.sym] || {}).company || "")}</span></div></td>
      <td class="r num ${cls(t.r6)}">${pct(t.r6, 0)}</td><td class="r num ${cls(t.r12)}">${pct(t.r12, 0)}</td><td class="r num hide-sm">${num(t.vol)}%</td>
      <td class="r num">${px(t.close)}</td><td>${t.held ? '<span class="chip sm ghost">held</span>' : nav.length ? '<span class="chip sm buy">add</span>' : '<span class="chip sm ghost">new</span>'}</td></tr>`).join("")}
      ${(pv.drops || []).map(s => `<tr data-sym="${esc(s)}"><td class="r faint">—</td><td class="sym">${esc(s)}</td><td colspan="4" class="muted">fell below rank 40</td><td><span class="chip sm risk">drop</span></td></tr>`).join("")}</tbody></table></div></div>`;
  const held = nav.length && (book.rows || []).length ? `<div class="card flush" style="margin-top:16px"><div class="card-head"><h3>Holdings</h3><span class="hint">cash ${inrShort(book.cash)}</span></div><div class="table-wrap"><table class="t"><thead><tr><th>Stock</th><th class="r">Weight</th><th class="r">Since</th><th class="r">Return</th><th class="r">Price</th></tr></thead>
    <tbody>${book.rows.map(r => `<tr data-sym="${esc(r.sym)}" data-ctx="coreheld"><td class="sym">${esc(r.sym)}</td><td class="r num">${num(r.weight, 1)}%</td><td class="r">${esc(dateLabel(r.since))}</td><td class="r num ${cls(r.ret)}">${pct(r.ret)}</td><td class="r num">${px(r.close)}</td></tr>`).join("")}</tbody></table></div></div>` : "";
  return `<div class="section-title">Momentum core ${info("The top 20 stocks by volatility-adjusted 6- and 12-month momentum (NSE's momentum-index method), liquid names only, rebalanced on the first session of each month at the open; a holding stays while it ranks in the top 40; half invested when market breadth is under 50%. Pre-registered 2026-09-25 (PREREG_2026-09-25_momentum_core.md) and judged forward against the MIDSMALL ETF and the universe.")}<span class="chip sm ai">pre-registered · paper</span><span class="line"></span></div>
    <div class="kpis" style="margin-bottom:14px">${kpis}</div>
    ${nav.length ? `<div class="card" style="margin-bottom:16px"><div class="card-head"><h3>Growth of the paper book</h3></div><div class="chart-box" id="corenav" style="height:220px"></div></div>` : `<div class="callout info" style="margin-bottom:14px">Why this exists: over 2020–2026 this rotation made about as much as the breakout system with ideal fills, and it catches the fast V-shaped recoveries a base-breakout system cannot enter. Run as <b>one book</b> with the breakout trades — 50/50 had the best risk-adjusted result of everything tested. It starts forward on ${esc(nextRebalanceLabel())}; the pass bar was fixed before any forward data.</div>`}
    ${tbl}${held}`;
}
function drawCoreNav() {
  const box = $("#corenav"), nav = MC.nav || [];
  if (!box || !nav.length || !window.LightweightCharts) return;
  const ch = makeChart(box, { bucket: _pageCharts });
  const s = ch.addAreaSeries({ lineColor: css("--ai"), topColor: css("--ai") + "33", bottomColor: css("--ai") + "05", lineWidth: 2, priceLineVisible: false });
  s.setData(nav.map(p => ({ time: p[0], value: p[1] })));
  ch.timeScale().fitContent();
}
function pagePortfolio() {
  const paper = POS.paper || [], P = D.paper || {};
  const led = P.ledger || [];
  return `
  <div class="page-head"><div><h2>Paper portfolio</h2><div class="sub">One book in two parts, both run on paper by rules alone: the momentum core (monthly) and the breakout book (every analyst BUY, managed by the two-lot plan).</div></div></div>
  ${momentumSection()}
  <div class="section-title" style="margin-top:28px">Breakout book ${info("Every AI-analyst BUY verdict auto-entered at the next session's open, sized by the mechanical plan and exited by the same two-lot rules. It is the running test of whether the analyst layer adds money. Notional ₹10L book.")}<span class="line"></span></div>
  <div class="kpis" style="margin-bottom:14px">
    <div class="kpi"><div class="label">Net result</div><div class="value ${cls(P.net)}">${inrShort(P.net)}</div><div class="note">${pct(P.net_pct, 1)} of the ₹10L notional book</div></div>
    <div class="kpi"><div class="label">Realised</div><div class="value sm ${cls(P.realized)}">${inrShort(P.realized)}</div><div class="note">${num(P.n_closed)} positions closed</div></div>
    <div class="kpi"><div class="label">Open, marked to market</div><div class="value sm ${cls(P.unrealized)}">${inrShort(P.unrealized)}</div><div class="note">${paper.length} positions open</div></div>
    <div class="kpi"><div class="label">Waiting to fill</div><div class="value sm">${(P.pending || []).length}</div><div class="note">${(P.pending || []).map(p => esc(p.sym)).join(", ") || "none"}</div></div>
  </div>
  ${paper.length ? positionsTable(paper) : `<div class="empty">The paper book has no open positions.</div>`}
  ${led.length ? `<details class="more" style="margin-top:14px"><summary>Recent paper fills (${led.length})</summary><div class="card flush" style="margin-top:8px"><div class="table-wrap"><table class="t"><thead><tr><th>Date</th><th>Stock</th><th>Action</th><th class="r">Shares</th><th class="r">Price</th><th class="r">P&amp;L</th><th class="hide-sm">Reason</th></tr></thead>
    <tbody>${led.map(l => `<tr data-sym="${esc(l.sym)}"><td class="num">${esc(l.d)}</td><td class="sym">${esc(l.sym)}</td><td>${l.action === "BUY" ? '<span class="chip sm buy">Buy</span>' : l.action === "SELL" ? '<span class="chip sm">Sell ' + esc(l.lot) + "</span>" : '<span class="chip sm ghost">' + esc(l.action) + "</span>"}</td>
      <td class="r num">${esc(l.shares)}</td><td class="r num">${isNum(+l.price) && l.price !== "" ? px(+l.price) : "—"}</td><td class="r num ${cls(+l.pnl)}">${l.pnl !== "" && isNum(+l.pnl) ? inr(+l.pnl) : ""}</td><td class="hide-sm muted" style="max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(l.reason)}</td></tr>`).join("")}</tbody></table></div></div></details>` : ""}`;
}
function positionsTable(list) {
  return `<div class="card flush"><div class="table-wrap"><table class="t"><thead><tr><th>Stock</th><th class="r">Entry</th><th class="r">Last</th><th class="r">Result</th><th class="r hide-sm">Shares</th><th>Next rules</th></tr></thead>
    <tbody>${list.map(p => `<tr data-sym="${esc(p.sym)}" data-ctx="positions">
      <td><div class="cell-sym"><span class="sym">${esc(p.sym)}</span><span class="co">since ${esc(dateLabel(p.entered))}${p.verdict ? " · " + esc(p.verdict) : ""}</span></div></td>
      <td class="r num">${px(p.entry)}</td><td class="r num">${px(p.last)}</td>
      <td class="r num ${cls(p.r_now)}">${rr(p.r_now)}<div class="muted" style="font-size:11.5px">${pct(p.pnl_pct)} · ${inrShort(p.pnl)}</div></td>
      <td class="r num hide-sm">${num(p.shares)}</td>
      <td style="min-width:260px">${p.urgent && p.urgent.length ? `<div class="warn" style="font-size:12.5px;font-weight:600">⚠ ${esc(p.urgent.join(" · "))}</div>` : ""}
        ${(p.rules || []).map(r => `<div style="font-size:12px;display:flex;gap:8px;justify-content:space-between"><span class="muted">${esc(r.label)}</span><span class="num">${px(r.px)} <span class="faint">${isNum(r.gap) ? pct(r.gap) : ""}</span></span></div>`).join("")}</td></tr>`).join("")}</tbody></table></div></div>`;
}

/* ---------------------------------------------------------------- RESEARCH */
function pageResearch() {
  const tabs = [["analyst", "AI analyst"], ["committee", "Committee picks"], ["themes", "Themes & sectors"], ["news", "News & filings"], ["deals", "Bulk & block deals"], ["policy", "Policy radar"]];
  if (S.sub && tabs.some(t => t[0] === S.sub)) S.research = S.sub;
  const body = { analyst: researchAnalyst, committee: researchCommittee, themes: researchThemes, news: researchNews, deals: researchDeals, policy: researchPolicy }[S.research] || researchAnalyst;
  return `<div class="page-head"><div><h2>Research</h2><div class="sub">The context behind the signals. Nothing here changes an entry, a stop or a size — it explains, flags risk, and is journaled so it can be measured.</div></div></div>
    <div class="toolbar"><div class="seg">${tabs.map(([k, l]) => `<button data-research="${k}" class="${S.research === k ? "on" : ""}">${l}</button>`).join("")}</div></div>
    ${body()}`;
}
function researchAnalyst() {
  const items = D.verdict_items || [];
  if (!items.length) return `<div class="empty">No analyst verdicts in the last 10 days.</div>`;
  const es = X.event_study || {};
  return `<div class="callout" style="margin-bottom:14px">The nightly analyst web-researches the top buy alerts and returns <b>take, halve or skip</b> — it can only be more cautious than the machine, never less. Its forward record so far: BUY calls ran slightly ahead of WAIT calls, and SKIPs did not underperform, so treat a verdict as research, not as a filter.</div>
    <div class="grid grid-2">${items.map(v => `<div class="vcard" data-sym="${esc(v.sym)}" style="cursor:pointer">
      <div class="top"><span class="sym" style="font-size:15px">${esc(v.sym)}</span>${verdictChip(v)}${v.size ? `<span class="chip sm ghost">${esc(v.size)}</span>` : ""}<span class="muted" style="margin-left:auto;font-size:12px">${esc(dateLabel(v.stamp))}</span></div>
      <div class="why">${esc(v.why)}</div>
      ${(v.whys && v.whys.length) || (v.risks && v.risks.length) ? `<details><summary>Evidence and risks</summary><div class="memo">
        ${v.whys && v.whys.length ? `<h4>Why</h4><ul>${v.whys.map(w => `<li>${esc(w)}</li>`).join("")}</ul>` : ""}
        ${v.risks && v.risks.length ? `<h4>Risks</h4><ul>${v.risks.map(w => `<li>${esc(w)}</li>`).join("")}</ul>` : ""}
        ${v.flip ? `<h4>What would change the view</h4><p>${esc(v.flip)}</p>` : ""}</div></details>` : ""}
    </div>`).join("")}</div>`;
}
function researchCommittee() {
  const P = D.ai_picks || {};
  const picks = P.picks || [];
  if (!picks.length) return `<div class="empty">No committee picks yet.</div>`;
  const age = P.age_days;
  return `${age != null && age > 8 ? `<div class="callout watch" style="margin-bottom:12px"><b>Not this week's read:</b> the committee last ran ${age} days ago.</div>` : ""}
    <div class="card" style="margin-bottom:14px"><div class="card-head"><h3>Portfolio view</h3><span class="hint">Weekly · ${esc(P.generated || "")}</span></div><div class="memo">${esc(P.portfolio_view || "")}</div></div>
    <div class="grid grid-2">${picks.map(p => { const m = p.meta || {}, pl = m.plan || {}; return `<div class="vcard">
      <div class="top"><button class="btn link sym" data-sym="${esc(p.symbol)}" style="font-size:16px;color:var(--text)">${esc(p.symbol)}</button>
        <span class="chip sm ${p.conviction === "HIGH" ? "buy" : "info"}">${esc(p.conviction || "")}</span><span class="chip sm ghost">${esc(m.sector || "")}</span>
        ${stageChip((rowBy[p.symbol] || {}).tag)} ${setupChip((rowBy[p.symbol] || {}).trig)}</div>
      <div class="muted" style="font-size:12.5px;margin-top:4px">${esc(m.company || "")}</div>
      <div class="why"><b>Thesis.</b> ${esc(p.thesis || "")}</div>
      <details><summary>Catalyst, risks, what to watch</summary><div class="memo">
        ${p.catalyst ? `<h4>Catalyst</h4><p>${esc(p.catalyst)}</p>` : ""}${p.risks ? `<h4>Risks</h4><p>${esc(Array.isArray(p.risks) ? p.risks.join(" ") : p.risks)}</p>` : ""}
        ${p.watch_for ? `<h4>Watch for</h4><p>${esc(p.watch_for)}</p>` : ""}${p.selected_because ? `<h4>Why selected</h4><p>${esc(p.selected_because)}</p>` : ""}
        ${isNum(pl.entry_price) ? `<h4>Mechanical plan</h4><p class="num">entry ${px(pl.entry_price)} · stop ${px(pl.stop_loss_price)} · ${num(pl.shares_total)} shares · risk ${inr(pl.capital_at_risk)}</p>` : ""}</div></details>
    </div>`; }).join("")}</div>`;
}
function researchThemes() {
  const T = D.themes || {}, th = (T.themes || []).slice().sort((a, b) => (b.heat || 0) - (a.heat || 0));
  const intel = T.intel || {};
  return `<div class="callout" style="margin-bottom:14px">Themes group stocks the way markets trade them (grid capex, defence, EMS…), across NSE's accounting categories. <b>Heat</b> ranks themes against each other from 3-month move, chart breadth and news. Sector heat was tested as an entry filter and <b>rejected</b> (it cut expectancy from +1.27R to +0.22R), so it is context only.</div>
    <div class="card flush"><div class="table-wrap"><table class="t"><thead><tr><th>Theme</th><th class="r">Heat</th><th class="r">3 months</th><th class="r hide-sm">In uptrend</th><th class="r hide-sm">Names</th><th>Leaders</th></tr></thead>
    <tbody>${th.map(t => `<tr style="cursor:default"><td><div class="cell-sym"><span class="sym">${esc(t.name)}</span><span class="co" style="max-width:300px">${esc(t.blurb || "")}</span></div></td>
      <td class="r num"><span class="bar-inline" style="width:${Math.max(4, (t.heat || 0) * .6)}px;background:var(--watch);opacity:.7"></span> ${num(t.heat)}</td>
      <td class="r num ${cls(t.ret3m)}">${pct(t.ret3m)}</td><td class="r num hide-sm">${num(t.breadth)}%</td><td class="r num hide-sm">${num(t.n)}${t.thin ? ' <span class="faint">thin</span>' : ""}</td>
      <td>${(t.leaders || []).filter(l => l.tag === "CONFIRMED" || l.tag === "EXTENDED").slice(0, 5).map(l => `<button class="chip sm" data-sym="${esc(l.sym)}">${esc(l.sym)}</button>`).join(" ")}</td></tr>`).join("")}</tbody></table></div></div>
    ${intel.summary ? `<div class="card accent-ai" style="margin-top:16px"><div class="card-head"><h3>This week's thematic research</h3><span class="chip sm ai">AI · weekly</span><span class="hint">${esc(intel.generated || "")}</span></div><div class="memo">${esc(intel.summary)}</div>
      ${(intel.themes || []).slice(0, 8).map(x => `<details class="more"><summary><b>${esc(x.name || x.key)}</b> — ${esc(x.direction || "")}${x.strength ? " · strength " + esc(x.strength) : ""}</summary><div class="memo">${esc(x.thesis || x.summary || "")}
        ${(x.calls || x.beneficiaries || []).length ? `<ul>${(x.calls || x.beneficiaries || []).slice(0, 8).map(c => `<li><b>${esc(c.symbol || c.sym || "")}</b> ${esc(c.effect || "")} — ${esc(c.mechanism || c.why || "")}</li>`).join("")}</ul>` : ""}</div></details>`).join("")}</div>` : ""}
    ${T.read ? `<details class="more" style="margin-top:12px"><summary>The committee's theme read</summary><div class="card"><div class="memo">${esc(T.read)}</div></div></details>` : ""}`;
}
function researchNews() {
  const held = heldSyms(), buy = new Set(buySignals().map(a => a.sym));
  const risk = [], building = [];
  Object.entries(newsMem).forEach(([sym, m]) => {
    const tag = (rowBy[sym] || {}).tag;
    if (m.n_neg && (held.has(sym) || buy.has(sym) || actBy[sym])) risk.push({ sym, m, tag });
    if (m.primed && !["CONFIRMED", "EXTENDED"].includes(tag)) building.push({ sym, m, tag });
  });
  building.sort((a, b) => (b.m.p || 0) - (a.m.p || 0));
  const hits = (D.radar || {}).hits || [];
  return `<div class="callout" style="margin-bottom:14px">Measured on this system's own archive, positive news did <b>not</b> lead the technical trigger (names with a positive filing alerted 7.3% of the time vs a 16.6% base rate). So news here is a <b>risk watch and a dossier</b>, not a buy list.</div>
    <div class="grid grid-2">
      <div class="card accent-risk"><div class="card-head"><h3>Risk on paper-portfolio and alerted names</h3></div>
        ${risk.length ? risk.slice(0, 20).map(x => `<div class="lrow" data-sym="${esc(x.sym)}"><div><span class="sym">${esc(x.sym)}</span> ${stageChip(x.tag)}<div class="meta">${esc(x.m.summary || "")}</div></div><span class="chip sm risk">${x.m.n_neg} negative</span></div>`).join("") : `<div class="muted">No negative filings on paper-portfolio or alerted names.</div>`}</div>
      <div class="card"><div class="card-head"><h3>Stories building, chart not there yet</h3></div>
        ${building.length ? building.slice(0, 15).map(x => `<div class="lrow" data-sym="${esc(x.sym)}"><div><span class="sym">${esc(x.sym)}</span> ${stageChip(x.tag)}<div class="meta">${esc(x.m.summary || "")}</div></div><span class="muted num" style="font-size:12px">${(x.m.p || 0).toFixed(2)}</span></div>`).join("") : `<div class="muted">Nothing building.</div>`}</div>
    </div>
    <div class="card flush" style="margin-top:16px"><div class="card-head"><h3>Filings since the last scan</h3><span class="hint">${hits.length} classified</span></div><div class="table-wrap"><table class="t"><thead><tr><th></th><th>Stock</th><th>Chart</th><th class="r">RS</th><th>Event</th><th class="hide-sm">Filing</th></tr></thead>
      <tbody>${hits.map(h => `<tr data-sym="${esc(h.sym)}"><td>${h.cls === "neg" ? '<span class="neg">▼</span>' : h.cls === "pos" ? '<span class="pos">▲</span>' : "·"}</td><td class="sym">${esc(h.sym)}</td><td>${stageChip(h.tag)}</td><td class="r num">${isNum(h.rs) ? h.rs.toFixed(0) : "—"}</td>
        <td>${esc(h.event || "")}${h.confluence ? ' <span class="chip sm buy" data-tip="Positive filing on a stock already in an uptrend.">confluence</span>' : ""}</td><td class="hide-sm muted" style="max-width:420px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(h.subject || "")}</td></tr>`).join("")}</tbody></table></div></div>`;
}
function researchDeals() {
  const rec = DEALS.recent || [];
  const intro = `<div class="callout" style="margin-bottom:14px">Bulk and block deals on the names this system watches, as NSE publishes them each evening. Most bulk-deal rows in small caps are trading desks <b>buying and selling the same stock in the same session</b>${isNum(DEALS.churn_pct) ? ` (${DEALS.churn_pct}% of rows so far)` : ""} — those net to nothing and are left out here. What remains is someone ending the day holding more or less. Archived from ${esc(dateLabel(DEALS.since))}, so the history grows nightly; context only, never an entry filter.</div>`;
  if (!rec.length) return intro + `<div class="empty">No named deal of ₹1 crore or more on a watched name in the last 30 days.</div>`;
  return intro + `<div class="card flush"><div class="card-head"><h3>Named deals, last 30 days</h3><span class="hint">₹1 crore and above</span></div><div class="table-wrap max"><table class="t"><thead><tr><th>Date</th><th>Stock</th><th>Side</th><th>Client</th><th class="r">Shares</th><th class="r">Price</th><th class="r">Value</th><th class="hide-sm">Type</th></tr></thead>
    <tbody>${rec.map(r => `<tr data-sym="${esc(r.sym)}"><td class="num">${esc(dateLabel(r.d))}</td><td class="sym">${esc(r.sym)} ${stageChip((rowBy[r.sym] || {}).tag)}</td>
      <td>${r.side === "BUY" ? '<span class="chip sm buy">Buy</span>' : '<span class="chip sm risk">Sell</span>'}</td><td class="muted" style="max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(r.client)}</td>
      <td class="r num">${num(r.qty)}</td><td class="r num">${px(r.price)}</td><td class="r num">${inrShort(r.value)}</td><td class="hide-sm muted">${esc(r.kind)}</td></tr>`).join("")}</tbody></table></div></div>`;
}
function researchPolicy() {
  const M = X.macro || {};
  const themeMeta = Object.fromEntries(((D.themes || {}).themes || []).map(t => [t.key, t]));
  const list = Object.entries(M.themes || {}).map(([k, v]) => ({ key: k, ...v }))
    .sort((a, b) => Math.abs(b.pressure || 0) - Math.abs(a.pressure || 0));
  if (!list.length) return `<div class="empty">No policy event in the last ${num(M.window_days)} days.</div>`;
  return `<div class="callout" style="margin-bottom:14px">Government and regulator decisions that move a whole theme, read from <b>${num(M.headlines_read)}</b> headlines that name no company (${num(M.policy_hits)} qualified in the last ${num(M.window_days)} days). Bounded on purpose: it can move a stock's catalyst dimension by at most 0.12 and moves nothing else.</div>
    <div class="grid grid-2">${list.map(t => { const meta = themeMeta[t.key] || {}; const names = (meta.leaders || []).filter(l => ["CONFIRMED", "EXTENDED"].includes(l.tag)).slice(0, 8);
      return `<div class="vcard"><div class="top"><span class="sym" style="font-size:15px">${esc(meta.name || t.key)}</span>
      <span class="chip sm ${(t.pressure || 0) >= 0 ? "buy" : "risk"}" data-tip="Decayed policy pressure on this theme (half-life ${num(M.half_life_days)} days).">${(t.pressure || 0) >= 0 ? "+" : ""}${(t.pressure || 0).toFixed(2)}</span></div>
      <div style="margin-top:6px">${(t.top || []).slice(0, 3).map(e => `<div class="news-item" style="grid-template-columns:62px minmax(0,1fr)"><div class="d">${esc(dateLabel(e.date))}</div><div><div class="h"><span class="${e.polarity === "neg" ? "neg" : "pos"}">${e.polarity === "neg" ? "▼" : "▲"}</span> ${e.link && /^https?:/.test(e.link) ? `<a href="${esc(e.link)}" target="_blank" rel="noopener">${esc(e.title)}</a>` : esc(e.title)}</div><div class="src">${esc(e.source || "")}${e.event ? " · " + esc(e.event) : ""}${isNum(e.amount_cr) ? " · ₹" + nf0.format(e.amount_cr) + " Cr" : ""}</div></div></div>`).join("")}</div>
      ${names.length ? `<div class="muted" style="font-size:11.5px;margin-top:8px">In an uptrend in this theme</div><div style="display:flex;gap:4px;flex-wrap:wrap;margin-top:4px">${names.map(l => `<button class="chip sm" data-sym="${esc(l.sym)}">${esc(l.sym)}</button>`).join("")}</div>` : ""}</div>`; }).join("")}</div>`;
}

/* ------------------------------------------------------------ TRACK RECORD */
function pageRecord() {
  const tabs = [["gate", "Capital gate"], ["signals", "Which signals work"], ["backtest", "Backtest, honestly"], ["log", "Signal log"]];
  if (S.sub && tabs.some(t => t[0] === S.sub)) S.record = S.sub;
  const body = { gate: recordGate, signals: recordSignals, backtest: recordBacktest, log: recordLog }[S.record] || recordGate;
  return `<div class="page-head"><div><h2>Track record</h2><div class="sub">Is any of this working? The forward record is the judge; the backtest is only the hypothesis it is tested against.</div></div></div>
    <div class="toolbar"><div class="seg">${tabs.map(([k, l]) => `<button data-record="${k}" class="${S.record === k ? "on" : ""}">${l}</button>`).join("")}</div></div>${body()}`;
}
function recordGate() {
  const g = D.gate || {}, c = g.cohort || {}, req = g.required || {}, cond = g.conditions || {}, obs = g.observation || {};
  const bm = g.benchmark || {}, bm2 = g.benchmark2 || {};
  const names = { sample: "Sample size", expectancy: "Expectancy", beats_benchmark: "Beats the ETF", hit_stop: "Stop-out rate", concentration: "Not one lucky trade" };
  return `<div class="grid grid-main">
    <div class="card"><div class="card-head"><h3>Capital gate</h3><span class="chip sm ${g.verdict === "PASS" ? "buy" : g.verdict === "FAIL" ? "risk" : "info"}">${esc(g.verdict || "—")}</span><span class="hint">registered ${esc(g.registered || "")} · deadline ${esc(g.deadline || "")} (${num(g.days_to_deadline)} days)</span></div>
      <div class="kpis" style="grid-template-columns:repeat(3,minmax(0,1fr));margin-bottom:14px">
        <div class="kpi"><div class="label">Qualifying signals</div><div class="value">${num(c.n_qualifying)}<span class="muted" style="font-size:15px">/${num(req.min_signals || 40)}</span></div>${meter((c.n_qualifying || 0) / (req.min_signals || 40), "info")}</div>
        <div class="kpi"><div class="label">Expectancy</div><div class="value sm ${cls(c.expectancy_r)}">${rr(c.expectancy_r)}</div><div class="note">needs ${rr(c.required_expectancy_r)} at a median age of ${num(c.median_age_days)} days</div></div>
        <div class="kpi"><div class="label">Win rate · stopped</div><div class="value sm">${num(c.win_rate_pct)}% · ${num(c.hit_stop_pct)}%</div><div class="note">best ${rr(c.best_r)} · worst ${rr(c.worst_r)}</div></div>
      </div>
      <div class="checklist">${Object.entries(cond).map(([k, v]) => `<div class="check"><div class="ico ${v.ok ? "ok" : "na"}">${v.ok ? "✓" : "…"}</div><div><div class="t">${esc(names[k] || k)}</div><div class="n">${esc(v.detail)}</div></div><div class="w">${v.ok ? "passing" : "not yet"}</div></div>`).join("")}</div>
      <div class="muted" style="font-size:12.5px;margin-top:12px">Only the validated entries count: breakout triggers and gap-up pivots from 2026-07-25 on. Scans observed ${num(obs.sessions_scanned)} of ${num(obs.eligible_weekdays)} weekdays.</div>
    </div>
    <div class="stack">
      <div class="card"><div class="card-head"><h3>Against the alternatives</h3></div>
        <div class="lrow" style="cursor:default"><div><b>This system</b> (signal basis)<div class="meta">sum of plan-followed R × 1.25% risk</div></div><div class="num ${cls(c.signal_basis_return_pct)}">${pct(c.signal_basis_return_pct)}</div></div>
        <div class="lrow" style="cursor:default"><div>${esc(bm.label || "Momentum-quality ETF")}<div class="meta">${esc(bm.sym || "")} · ${esc(bm.from || "")} → ${esc(bm.to || "")}</div></div><div class="num ${cls(bm.ret_pct)}">${pct(bm.ret_pct)}</div></div>
        <div class="lrow" style="cursor:default"><div>${esc(bm2.label || "NIFTY 50")}</div><div class="num ${cls(bm2.ret_pct)}">${pct(bm2.ret_pct)}</div></div>
        <div class="callout watch" style="margin-top:10px;font-size:12px">The system figure adds up independent signal results; it is not a cash-constrained portfolio, so it overstates what one book would have earned. Treat the comparison as directional.</div>
      </div>
    </div></div>`;
}
function esRow(r) {
  const cell = h => r["n" + h] ? `<td class="r num ${cls(r["x" + h])}">${pct(r["x" + h])}<div class="faint" style="font-size:11px">${num(r["b" + h])}% beat · n ${r["n" + h]}</div></td>` : `<td class="r faint">—</td>`;
  return `<tr style="cursor:default"><td><b>${esc(r.cohort)}</b></td><td class="r num">${num(r.n)}</td>${cell(10)}${cell(20)}${cell(40)}</tr>`;
}
function recordSignals() {
  const es = X.event_study || {};
  if (!es.by_status) return `<div class="empty">The forward record has not been measured on this build.</div>`;
  return `<div class="callout info" style="margin-bottom:14px">Each buy alert is measured from the <b>next session's open</b> against an <b>equal-weight basket of the whole universe</b> over the same days, at fixed horizons. So a rising market cannot flatter a label and old and young alerts are not mixed. Measured to ${esc(es.as_of || "")}.</div>
    <div class="card flush"><div class="card-head"><h3>By setup</h3><span class="hint">excess return over the universe</span></div><div class="table-wrap"><table class="t"><thead><tr><th>Alert type</th><th class="r">Alerts</th><th class="r">10 sessions</th><th class="r">20 sessions</th><th class="r">40 sessions</th></tr></thead>
      <tbody>${es.by_status.map(esRow).join("")}</tbody></table></div></div>
    <div class="card flush" style="margin-top:16px"><div class="card-head"><h3>By research score at the alert</h3><span class="hint">does the 0–100 score sort outcomes?</span></div><div class="table-wrap"><table class="t"><thead><tr><th>Score band</th><th class="r">Alerts</th><th class="r">10 sessions</th><th class="r">20 sessions</th><th class="r">40 sessions</th></tr></thead>
      <tbody>${(es.by_conv || []).map(esRow).join("")}</tbody></table></div></div>
    <div class="callout" style="margin-top:14px"><b>Reading it.</b> The setup matters most: live-base and trigger alerts beat the universe, uptrend-only alerts barely do. The research score separates the <b>bottom</b> (under 50, including vetoes, lags the universe) but does not rank the rest — which is why this interface sorts by setup first and uses the score only as a tie-breaker.</div>
    ${(D.forensics || {}).sections ? `<details class="more" style="margin-top:14px"><summary>Plan-followed forensics (older ruler, by cohort)</summary>${D.forensics.sections.map(sec => `<div class="card flush" style="margin-top:10px"><div class="card-head"><h3>${esc(sec.title)}</h3></div><div class="table-wrap"><table class="t"><thead><tr><th>Cohort</th><th class="r">n</th><th class="r">Open</th><th class="r">Plan R</th><th class="r">Median R</th><th class="r">Stopped</th><th class="r">Avg best R</th></tr></thead>
      <tbody>${sec.rows.map(r => `<tr style="cursor:default"><td>${esc(r.cohort)}</td><td class="r num">${num(r.n)}</td><td class="r num">${num(r.open)}</td><td class="r num ${cls(r.plan_r)}">${rr(r.plan_r)}</td><td class="r num ${cls(r.med_r)}">${rr(r.med_r)}</td><td class="r num">${num(r.hit_stop_pct)}%</td><td class="r num">${rr(r.avg_mfe)}</td></tr>`).join("")}</tbody></table></div></div>`).join("")}</details>` : ""}`;
}
const HR_LABEL = {
  F1_live_full_net: "System (VCP + gap-up), ideal fills", F2_live_full_stress: "System, realistic execution",
  F3_vcp_only_full_net: "VCP breakouts only", F4_ep_only_full_net: "Gap-up pivots only",
  EQW_full: "Own the whole universe (equal weight)", MOM_full: "Monthly momentum rotation, top 20",
  MOMR_full: "Momentum rotation + breadth rule", NIFTY50_full: "NIFTY 50", MOMENTUM100_full: "Nifty Midcap 100 ETF",
  L1_live_2023_breadth_net: "System, ideal fills (2023–26)", L2_live_2023_stress: "System, realistic (2023–26)",
  EQW_2023: "Own the universe (2023–26)", MOMR_2023: "Momentum + breadth (2023–26)", NIFTY50_2023: "NIFTY 50 (2023–26)",
  L0_repro_2023_nifty_gross: "Published headline, reproduced (2023–26, gross)",
};
function recordBacktest() {
  const H = X.honest;
  if (!H) return `<div class="empty">The 2026-09-25 re-run is not on this build.</div>`;
  const rows = H.rows || [];
  const full = ["F1_live_full_net", "F2_live_full_stress", "F3_vcp_only_full_net", "F4_ep_only_full_net", "EQW_full", "MOM_full", "MOMR_full", "NIFTY50_full", "MOMENTUM100_full"];
  const recent = ["L0_repro_2023_nifty_gross", "L1_live_2023_breadth_net", "L2_live_2023_stress", "EQW_2023", "MOMR_2023", "NIFTY50_2023"];
  const tbl = keys => `<table class="t"><thead><tr><th>Strategy</th><th class="r">CAGR</th><th class="r">Max drawdown</th><th class="r" data-tip="CAGR divided by the worst drawdown — return per unit of pain.">MAR</th><th class="r hide-sm">Sharpe</th><th class="r hide-sm">₹1 became</th></tr></thead>
    <tbody>${keys.map(k => rows.find(r => r.config === k)).filter(Boolean).map(r => `<tr style="cursor:default" class="${/^F[12]|^L[12]/.test(r.config) ? "" : "dim"}"><td>${esc(HR_LABEL[r.config] || r.config)}</td>
      <td class="r num ${cls(r.cagr_pct)}">${pct(r.cagr_pct)}</td><td class="r num neg">${pct(r.max_dd_pct)}</td><td class="r num">${isNum(r.mar) ? r.mar.toFixed(2) : "—"}</td><td class="r num hide-sm">${isNum(r.sharpe) ? r.sharpe.toFixed(2) : "—"}</td><td class="r num hide-sm">${isNum(r.total_x) ? "₹" + r.total_x.toFixed(2) : "—"}</td></tr>`).join("")}</tbody></table>`;
  AFTER.push(() => drawCurves());
  return `<div class="callout watch" style="margin-bottom:14px"><b>Read this first.</b> Every figure here uses today's index members, so it carries survivorship bias: simply owning the whole universe returned 33% a year since 2020, while the real, investable Midcap-100 ETF returned 21%. Compare rows with each other, never with a bank deposit.</div>
    <div class="card"><div class="card-head"><h3>Growth of ₹100 since 2020</h3><span class="hint">weekly, log scale</span></div><div class="chart-box" id="curvebox" style="height:340px"></div></div>
    <div class="grid grid-2" style="margin-top:16px">
      <div class="card flush"><div class="card-head"><h3>Full history, 2020 → today</h3></div><div class="table-wrap">${tbl(full)}</div></div>
      <div class="card flush"><div class="card-head"><h3>The headline window, 2023-08 → today</h3></div><div class="table-wrap">${tbl(recent)}</div></div>
    </div>
    <div class="card" style="margin-top:16px"><h3 style="font-size:15px;margin-bottom:8px">What this says</h3><div class="memo"><ul>
      <li>The published 54.5% a year came from the strongest three-year window, with costs left out of the equity curve. Measured honestly, the live rules earned <b>45% a year with ideal fills and 30% with realistic execution</b> since 2020, with drawdowns of 21–25%.</li>
      <li>Execution is the biggest lever: filling on the morning after the signal instead of at the breakout-day close cost about <b>10 points a year</b> by itself.</li>
      <li>Gap-up pivots carry more of the edge than VCP breakouts (40% vs 25% a year, with a far smaller drawdown).</li>
      <li>A plain monthly momentum rotation with the same breadth rule made 44% a year at a similar drawdown, and it catches the fast V-shaped recoveries this breakout system structurally misses. It is the natural candidate for a second, pre-registered sleeve.</li></ul></div></div>`;
}
function drawCurves() {
  const box = $("#curvebox"), H = X.honest;
  if (!box || !H || !H.curves || !window.LightweightCharts) return;
  const ch = makeChart(box, { log: true, bucket: _pageCharts });
  const colors = { F1: css("--buy"), F2: css("--info"), EQW_full: css("--faint"), MOMR_full: css("--ai"), NIFTY50: css("--risk"), MOMENTUM100: css("--watch") };
  const leg = [];
  H.curves.series.forEach(s => {
    const line = ch.addLineSeries({ color: colors[s.key] || css("--muted"), lineWidth: s.key.startsWith("F") ? 2 : 1.4, priceLineVisible: false, lastValueVisible: false });
    line.setData(s.pts.map(p => ({ time: p[0], value: p[1] })));
    leg.push(`<span><i style="background:${colors[s.key] || css("--muted")}"></i>${esc(s.label)}</span>`);
  });
  ch.timeScale().fitContent();
  const l = document.createElement("div"); l.className = "chart-legend"; l.innerHTML = leg.join(""); box.appendChild(l);
}
function recordLog() {
  const sc = D.scorecard || [];
  return `<div class="card flush"><div class="card-head"><h3>Every buy alert the machine fired</h3><span class="hint">${sc.length} signals · append-only</span></div><div class="table-wrap max"><table class="t"><thead><tr><th>When</th><th>Stock</th><th>Type</th><th class="r">Score</th><th class="r">Alert ₹</th><th class="r">Return</th><th class="r" data-tip="Plan-followed R: the signal replayed through the backtest engine with a next-open fill and the two-lot exits.">Plan R</th><th class="r">Best R</th><th>Status</th></tr></thead>
    <tbody>${sc.slice(0, 400).map(r => `<tr data-sym="${esc(r.sym)}"><td class="num">${esc(String(r.d).slice(0, 10))}</td><td class="sym">${esc(r.sym)}</td><td class="muted">${esc((VOC.kindsShort || {})[r.kind] || r.kind)}</td>
      <td class="r num">${isNum(r.conv) ? r.conv.toFixed(0) : "—"}</td><td class="r num">${px(r.entry)}</td><td class="r num ${cls(r.ret)}">${pct(r.ret)}</td>
      <td class="r num ${cls(r.planr)}">${rr(r.planr)}${r.sized === false ? '<span class="faint" data-tip="The live risk engine would not size this (stop wider than 12%); measured against a reference stop.">*</span>' : ""}</td><td class="r num">${rr(r.maxr)}</td><td class="muted">${esc(r.status)}</td></tr>`).join("")}</tbody></table></div></div>`;
}

/* ------------------------------------------------------------------- PENNY */
function pagePenny() {
  const P = lazy("penny") || D.penny;
  if (!P) return `<div class="empty">The penny screen has not run.</div>`;
  const f = S.penny, q = f.q.trim().toLowerCase();
  let rows = (P.rows || []).filter(r => (!q || r.sym.toLowerCase().includes(q) || (r.company || "").toLowerCase().includes(q)) && (f.showVeto || !r.veto) && (!f.arm || (r.arm || "").includes(f.arm)));
  rows.sort((a, b) => f.dir * (((a[f.sort] ?? -1e9) > (b[f.sort] ?? -1e9)) ? 1 : -1));
  return `<div class="page-head"><div><h2>Penny lab</h2><div class="sub">A separate, never-backtested research surface for nano-caps. In this class you lose by not being able to get out, so the screen excludes first and scores only the survivors. Cap: 5% of the book, 1% per name.</div></div></div>
    <div class="toolbar"><input class="field" id="pq" placeholder="Symbol or company…" value="${esc(f.q)}" style="width:200px">
      <div class="seg">${[["", "Both arms"], ["price", "Under ₹100"], ["mcap", "Under ₹1,000 Cr"]].map(([k, l]) => `<button data-parm="${k}" class="${f.arm === k ? "on" : ""}">${l}</button>`).join("")}</div>
      <label class="muted" style="font-size:12.5px;display:flex;gap:6px;align-items:center"><input type="checkbox" id="pveto" ${f.showVeto ? "checked" : ""}>Show vetoed</label>
      <span class="right">${rows.length} names · as of ${esc(P.as_of || "")}</span></div>
    <div class="card flush"><div class="table-wrap max"><table class="t"><thead><tr><th>Stock</th><th class="r">Score</th><th>Stage</th><th class="r">RS</th><th class="r hide-sm">Size</th><th class="r" data-tip="Median daily traded value — whether an exit exists at all.">Turnover</th><th class="r hide-sm" data-tip="10% of median daily value: roughly what you could exit in one session without moving the price.">Max position</th><th class="r hide-sm">3 months</th><th class="r">Price</th><th class="hide-sm">Flags</th></tr></thead>
      <tbody>${rows.map(r => `<tr class="${r.veto ? "dim" : ""}" style="cursor:default"><td><div class="cell-sym"><span class="sym">${esc(r.sym)}</span><span class="co">${esc(r.company || "")}</span></div></td>
        <td class="r num">${isNum(r.score) ? r.score.toFixed(0) : "—"}${r.cov < 100 ? '<span class="faint">°</span>' : ""}</td><td>${stageChip(r.tag)}</td><td class="r num">${isNum(r.rs) ? r.rs.toFixed(0) : "—"}</td>
        <td class="r num hide-sm">${isNum(r.mcap) ? nf0.format(r.mcap) + " Cr" : "—"}</td><td class="r num">${isNum(r.turn) ? "₹" + r.turn.toFixed(2) + " Cr" : "—"}</td>
        <td class="r num hide-sm">${isNum(r.turn) ? inrShort(r.turn * 1e7 * 0.1) : "—"}</td><td class="r num hide-sm ${cls(r.run3m)}">${pct(r.run3m, 0)}</td><td class="r num">${px(r.close)}</td>
        <td class="hide-sm">${r.veto ? `<span class="chip sm risk" data-tip="${esc(r.vetowhy)}">vetoed</span>` : ""}${(r.flags || []).slice(0, 2).map(x => `<span class="chip sm watch">${esc(typeof x === "string" ? x : x.code || "")}</span>`).join("")}</td></tr>`).join("")}</tbody></table></div></div>
    ${(P.funnel || []).length ? `<details class="more" style="margin-top:14px"><summary>What the gates excluded</summary><div class="card">${P.funnel.map(x => `<div class="lrow" style="cursor:default"><span>${esc(x.why)}</span><span class="num">${num(x.n)}</span></div>`).join("")}</div></details>` : ""}`;
}

/* ------------------------------------------------------------------ SYSTEM */
function pageSystem() {
  const h = D.health || [];
  AFTER.push(() => probeRunPanel());
  return `<div class="page-head"><div><h2>System</h2><div class="sub">Every subsystem against its own cadence. A job that records its own failure reads red however recent it is.</div></div></div>
    <div class="card flush"><div class="table-wrap"><table class="t"><thead><tr><th></th><th>Subsystem</th><th>Status</th><th class="hide-sm">What it does</th></tr></thead>
      <tbody>${h.map(x => `<tr style="cursor:default"><td><span class="dot ${esc(x.state)}"></span></td><td><b>${esc(x.label)}</b><div class="muted" style="font-size:12px">${x.age != null ? (x.age < 1 ? "today" : x.age.toFixed(1) + " days ago") : ""}</div></td><td>${esc(x.detail || "")}</td><td class="hide-sm muted" style="max-width:520px">${esc(x.tip || "")}</td></tr>`).join("")}</tbody></table></div></div>
    <div class="card" id="runpanel" style="margin-top:16px;display:none"></div>
    <div class="card" style="margin-top:16px"><div class="card-head"><h3>Data on this page</h3></div><div class="memo">
      Built ${esc(D.generated || "")} · prices to ${esc(priceSession())} · last scan ${esc(D.scan_date || "")}.<br>
      ${(D.funnel || []).map(f => `${esc(f[0])}: <b>${num(f[1])}</b> <span class="muted">(${esc(f[2])})</span>`).join(" · ")}<br>
      <a href="dashboard_classic.html">Open the classic dashboard</a> — kept for a transition period.</div></div>`;
}
let _runPoll = null;
async function probeRunPanel() {
  if (!/^https?:/.test(location.protocol)) return;
  try {
    const r = await fetch("/api/status", { cache: "no-store" });
    if (!r.ok) return;
    const s = await r.json();
    const p = $("#runpanel"); if (!p) return;
    p.style.display = "";
    const jobs = [["daily", "Daily scan", "scan + paper book + outcomes + rebuild — mechanical only"], ["daily_ai", "Scan + AI analyst", "adds the analyst on your Claude subscription"], ["weekly", "Weekly refresh", "universe, prices, fundamentals, shortlist — committee skipped"], ["penny", "Penny screen", "rebuild the nano-cap research screen"]];
    p.innerHTML = `<div class="card-head"><h3>Run a job on this laptop</h3><span class="hint">${s.running ? "running: " + esc(s.job) : s.finished_at ? "last: " + esc(s.job) + " " + (s.exit_ok ? "finished" : "failed") + " at " + esc(s.finished_at) : "idle"}</span></div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">${jobs.map(([k, l, t]) => `<button class="btn" data-run="${k}" data-tip="${esc(t)}" ${s.running ? "disabled" : ""}>${l}</button>`).join("")}</div>
      <pre id="runlog" class="mono" style="margin-top:12px;max-height:260px;overflow:auto;font-size:11.5px;background:var(--surface-2);padding:10px;border-radius:8px;white-space:pre-wrap">${esc((s.log || []).join("\n"))}</pre>`;
    if (s.running && !_runPoll) _runPoll = setInterval(probeRunPanel, 2000);
    if (!s.running && _runPoll) { clearInterval(_runPoll); _runPoll = null; if (s.exit_ok) toast("Job finished — reload for fresh data"); }
  } catch (e) { /* static copy: no run panel */ }
}

/* ============================================================ STOCK SHEET */
function openStock(sym, ctx, fromRoute) {
  if (!sym) return;
  sym = String(sym).toUpperCase();
  if (ctx) S.ctx = ctx;
  S.stock = sym;
  if (!fromRoute) { history.pushState(null, "", "#/stock/" + encodeURIComponent(sym)); }
  $("#scrim").classList.add("on");
  const sh = $("#sheet"); sh.classList.add("on");
  renderSheet();
  document.body.style.overflow = "hidden";
}
function closeSheet(silent) {
  const sh = $("#sheet");
  if (!sh.classList.contains("on")) return;
  sh.classList.remove("on"); $("#scrim").classList.remove("on");
  document.body.style.overflow = "";
  S.stock = null;
  if (_sheetCharts) { _sheetCharts.forEach(c => { try { c.remove(); } catch (e) { } }); _sheetCharts = []; }
  if (!silent && /^#\/stock\//.test(location.hash)) history.back();
}
function stepStock(d) {
  const ctx = S.ctx || [];
  const i = ctx.indexOf(S.stock);
  if (i < 0 || !ctx.length) return;
  const n = ctx[(i + d + ctx.length) % ctx.length];
  history.replaceState(null, "", "#/stock/" + encodeURIComponent(n));
  S.stock = n; renderSheet();
}
let _sheetCharts = [];
let _pageCharts = [];
function renderSheet() {
  const sym = S.stock, r = rowBy[sym] || {}, d = detailOf(sym) || {}, st = setupBy[sym], v = verdictBy[sym], pk = pickBy[sym];
  const o = ohlcOf(sym) || [];
  const last = o.length ? o[o.length - 1] : null, prev = o.length > 1 ? o[o.length - 2] : null;
  const price = last ? last[4] : r.close, chg = last && prev ? (last[4] / prev[4] - 1) * 100 : null;
  const ctx = S.ctx || [], idx = ctx.indexOf(sym);
  const tabs = [["chart", "Chart & plan"], ["business", "Business"], ["news", "News"], ["research", "AI research"], ["history", "History"]];
  $("#sheet").innerHTML = `
    <div class="sheet-head">
      <div class="sheet-title">
        <div style="min-width:0"><h2>${esc(sym)}</h2><div class="co">${esc(r.company || "")}${r.ind ? " · " + esc(r.ind) : ""}${r.tier ? " · " + esc(r.tier) + " cap" : ""}${isNum(r.mcap) ? " (₹" + nf0.format(r.mcap) + " Cr)" : ""}</div></div>
        <div class="px"><div class="p">${px(price)}</div><div class="${cls(chg)} num nowrap" style="font-size:12.5px">${pct(chg, 2)}<span class="hide-sm"> last session</span></div></div>
        <div class="sheet-nav">${idx >= 0 && ctx.length > 1 ? `<button class="icon-btn" id="shprev" aria-label="Previous stock" data-tip="Previous (←)">${I.left}</button><button class="icon-btn" id="shnext" aria-label="Next stock" data-tip="Next (→)">${I.right}</button>` : ""}<button class="icon-btn" id="shclose" aria-label="Close">${I.close}</button></div>
      </div>
      <div class="sheet-chips">${stageChip(r.tag)} ${setupChip(r.trig || (st && st.status))} ${isNum(r.rs) ? `<span class="chip sm ghost" data-tip="Relative strength percentile vs the whole universe.">RS ${r.rs.toFixed(0)}</span>` : ""} ${verdictChip(v, true)} ${pk ? `<span class="chip sm ai">Committee pick · ${esc(pk.conviction || "")}</span>` : ""} ${survChips(sym)} ${r.veto ? '<span class="chip sm risk">Vetoed</span>' : ""} ${(posBy[sym] || []).length ? `<span class="chip sm info">In breakout paper book</span>` : ""} ${coreHeld.has(sym) ? `<span class="chip sm ai">In momentum core</span>` : corePreview.has(sym) ? `<span class="chip sm ghost" data-tip="In the top 20 of the latest momentum ranking: the list the next monthly rebalance would buy.">Momentum top 20</span>` : ""} ${(themeBy[sym] || []).slice(0, 3).map(t => `<span class="chip sm ghost">${esc(t)}</span>`).join("")}</div>
      <div class="tabs">${tabs.map(([k, l]) => `<button data-shtab="${k}" class="${S.sheetTab === k ? "on" : ""}">${l}</button>`).join("")}</div>
    </div>
    <div class="sheet-body" id="shbody"></div>`;
  renderSheetBody();
}
function renderSheetBody() {
  const b = $("#shbody"); if (!b) return;
  if (_sheetCharts) { _sheetCharts.forEach(c => { try { c.remove(); } catch (e) { } }); _sheetCharts = []; }
  const sym = S.stock;
  const fn = { chart: sheetChart, business: sheetBusiness, news: sheetNews, research: sheetResearch, history: sheetHistory }[S.sheetTab] || sheetChart;
  b.innerHTML = fn(sym);
  b.scrollTop = 0;
  afterRender();
}
function sheetChart(sym) {
  const r = rowBy[sym] || {}, d = detailOf(sym) || {}, st = setupBy[sym], a = actBy[sym];
  const plan = planOf(sym), sp = st && st.plan && !st.plan.skip ? st.plan : null;
  const pos = (posBy[sym] || [])[0];
  AFTER.push(() => {
    drawCandles($("#mainchart"), sym, { range: S.chartRange, pivot: st ? st.pivot : null, stop: pos ? pos.stop : sp ? sp.stop : plan ? plan.stop : null, entry: pos ? pos.entry : null, partial: pos && pos.rules ? (pos.rules.find(x => x.k === "partial") || {}).px : null, rsBox: $("#rschart") });
  });
  let planHtml = "";
  if (pos) {
    planHtml = `<div class="card accent-${pos.urgent && pos.urgent.length ? "watch" : "buy"}" style="margin-top:14px"><div class="card-head"><h3>Paper position</h3><span class="hint">since ${esc(dateLabel(pos.entered))}</span><span class="right num ${cls(pos.r_now)}">${rr(pos.r_now)} · ${pct(pos.pnl_pct)}</span></div>
      ${pos.urgent && pos.urgent.length ? `<div class="callout watch" style="margin-bottom:10px">⚠ ${esc(pos.urgent.join(" · "))}</div>` : ""}
      <div class="plan-grid"><div class="plan-cell"><div class="k">Entry</div><div class="v">${px(pos.entry)}</div><div class="s">${num(pos.shares)} shares open</div></div>
      ${(pos.rules || []).slice(0, 3).map(x => `<div class="plan-cell"><div class="k">${esc(x.label)}</div><div class="v">${px(x.px)}</div><div class="s">${isNum(x.gap) ? pct(x.gap) + " from here" : ""}</div></div>`).join("")}</div></div>`;
  } else if (st) {
    planHtml = `<div class="card" style="margin-top:14px"><div class="card-head"><h3>Breakout plan</h3>${setupChip(st.status)}<span class="hint">entry on a close above the pivot with ≥1.5× average volume</span>
      ${sp ? `<span class="right"><button class="btn sm" data-copy-one="${esc(sym)}">${I.copy}Copy alert</button></span>` : ""}</div>
      ${sp ? `<div class="plan-grid">
        <div class="plan-cell"><div class="k">Buy above</div><div class="v">${px(st.pivot)}</div><div class="s">zone to ${px(st.zone_top)} (+5%)</div></div>
        <div class="plan-cell"><div class="k">Volume to confirm</div><div class="v">${volFmt(st.vneed)}</div><div class="s">today ${isNum(st.vr) ? st.vr.toFixed(1) + "× average" : "—"}</div></div>
        <div class="plan-cell"><div class="k">Stop</div><div class="v neg">${px(sp.stop)}</div><div class="s">${pct(-sp.stop_pct)} · 2.5 × ATR</div></div>
        <div class="plan-cell"><div class="k">Quantity · risk</div><div class="v">${num(sp.shares)}</div><div class="s">${inr(sp.risk)} (${(sp.risk / CAPITAL * 100).toFixed(2)}%)</div></div>
      </div><div class="muted" style="font-size:12.5px;margin-top:10px">Then: sell a third of the trading half at ${px(sp.partial)} (+2.5R); both halves' stops to breakeven on a close above ${px(sp.be)} (+1.5R); the trading half trails the 50-day average; the core half leaves only on a weekly close under the 30-week average.</div>`
        : `<div class="callout watch">${esc(st.plan && st.plan.why || "No sized plan.")}</div>`}</div>`;
  } else if (plan && !plan.skip) {
    planHtml = `<div class="card" style="margin-top:14px"><div class="card-head"><h3>Plan at the last alert</h3><span class="hint">${esc(a ? "signalled " + a.d : "")}</span></div>
      <div class="plan-grid"><div class="plan-cell"><div class="k">Entry ≈</div><div class="v">${px(plan.entry)}</div></div><div class="plan-cell"><div class="k">Stop</div><div class="v neg">${px(plan.stop)}</div><div class="s">${pct(-plan.stop_pct)}</div></div>
      <div class="plan-cell"><div class="k">Quantity</div><div class="v">${num(plan.shares)}</div></div><div class="plan-cell"><div class="k">Risk</div><div class="v">${inr(plan.risk)}</div></div></div></div>`;
  }
  const facts = [
    ["Stage", esc(d.stage_name || stageWord(r.tag))],
    ["Trend checks", isNum(d.tt_checks) ? d.tt_checks + " of 8" : "—"],
    ["Base (VCP)", st ? "live, pivot " + px(st.pivot) : d.vcp ? "live" : "none"],
    ["Volatility", st && isNum(st.atr_pct) ? st.atr_pct + "% a day (ATR)" : "—"],
  ];
  return `<div class="chart-range">${["3M", "6M", "1Y"].map(k => `<button class="btn sm ${S.chartRange === k ? "primary" : ""}" data-range="${k}">${k}</button>`).join("")}
      <span class="muted" style="font-size:12px;margin-left:8px">Candles with 50- and 150-day averages · volume · dashed lines: pivot, stop, entry</span></div>
    <div class="chart-box" id="mainchart"></div>
    <div class="chart-box small" id="rschart"></div>
    ${planHtml}
    <div class="grid grid-4" style="margin-top:14px">${facts.map(([k, v]) => `<div class="plan-cell"><div class="k">${k}</div><div class="v" style="font-size:14px;font-family:var(--font)">${v}</div></div>`).join("")}</div>
    ${(d.reasons || []).length ? `<div class="muted" style="font-size:12.5px;margin-top:10px">${d.reasons.map(esc).join(" · ")}</div>` : ""}`;
}
const DIM_LABEL = {
  earnings_inflection: "Earnings inflection", rs_and_stage: "Relative strength & stage", theme_tailwind: "Theme tailwind",
  smart_money: "Institutional ownership", financial_strength_trend: "Financial strength", catalyst: "Catalyst (news)",
  governance: "Governance", valuation_sanity: "Valuation sanity",
};
function sheetBusiness(sym) {
  const d = detailOf(sym) || {}, r = rowBy[sym] || {}, dims = d.dims || [];
  AFTER.push(() => drawFund(sym));
  const icon = s => s == null ? ["na", "–"] : s >= 0.65 ? ["ok", "✓"] : s >= 0.4 ? ["mid", "~"] : ["bad", "✕"];
  return `<div class="grid grid-main">
    <div>
      <div class="card"><div class="card-head"><h3>Business checklist</h3>${isNum(d.score) ? `<span class="chip sm ${d.score >= 60 ? "buy" : d.score >= 50 ? "info" : "watch"}">Score ${d.score.toFixed(0)}</span>` : ""}<span class="hint">${isNum(d.coverage) ? d.coverage.toFixed(0) + "% of the eight questions answered" : ""}${d.dims_as_of || d.scored_at ? " · " + esc(d.dims_as_of || d.scored_at) : ""}</span></div>
        ${(d.veto_reasons || []).length ? `<div class="callout risk" style="margin-bottom:10px"><b>Vetoed.</b> ${d.veto_reasons.map(esc).join("; ")}</div>` : ""}
        <div class="checklist">${dims.length ? dims.map(x => { const [c, t] = icon(x.live ? x.s : null); return `<div class="check"><div class="ico ${c}">${t}</div><div><div class="t">${esc(DIM_LABEL[x.k] || x.k)}</div><div class="n">${esc(x.n || (x.live ? "" : "no data"))}</div></div><div class="w">${x.live ? Math.round(x.s * 100) + "/100" : "—"} · wt ${num(x.w)}</div></div>`; }).join("") : `<div class="muted">No fundamental read for this name yet.</div>`}</div>
        <div class="muted" style="font-size:12px;margin-top:10px">What the score is for: in the forward record, names scoring under 50 (and vetoed names) lagged the universe; above 50 the score did not sort outcomes. Use it to rule things out, not to choose between good setups.</div>
      </div>
    </div>
    <div class="stack">
      <div class="card"><div class="card-head"><h3>Key numbers</h3></div>
        <div class="grid grid-2" style="gap:10px">
          ${[["ROCE", isNum(r.roce) ? r.roce.toFixed(1) + "%" : "—"], ["P/E", isNum(r.pe) ? r.pe.toFixed(1) : "—"], ["Profit growth (TTM)", isNum(r.pgttm) ? pct(r.pgttm, 0) : "—"], ["Market cap", isNum(r.mcap) ? "₹" + nf0.format(r.mcap) + " Cr" : "—"], ["Turnover", isNum(r.turn) ? "₹" + r.turn.toFixed(1) + " Cr/day" : "—"], ["Archetype", esc(r.arch || "—")]].map(([k, v]) => `<div class="plan-cell"><div class="k">${k}</div><div class="v" style="font-size:14px">${v}</div></div>`).join("")}</div></div>
      <div class="card"><div class="card-head"><h3>Quarterly profit</h3><span class="hint">₹ Cr</span></div><div id="fund-np"></div></div>
      <div class="card"><div class="card-head"><h3>Who owns it</h3><span class="hint">% held</span></div><div id="fund-own"></div></div>
    </div></div>`;
}
function bars(labels, vals, h = 90) {
  const v = vals.map(x => isNum(x) ? x : 0), mx = Math.max(...v.map(Math.abs), 1), w = 100 / v.length;
  return `<svg width="100%" height="${h + 18}" viewBox="0 0 100 ${h + 18}" preserveAspectRatio="none">${v.map((x, i) => {
    const bh = Math.abs(x) / mx * (h / 2 - 2), y = x >= 0 ? h / 2 - bh : h / 2;
    return `<rect x="${(i * w + w * .15).toFixed(2)}" y="${y.toFixed(2)}" width="${(w * .7).toFixed(2)}" height="${Math.max(.6, bh).toFixed(2)}" fill="${x >= 0 ? css("--buy") : css("--risk")}" opacity=".8"><title>${esc(labels[i] || "")}: ${num(x)}</title></rect>`;
  }).join("")}<line x1="0" x2="100" y1="${h / 2}" y2="${h / 2}" stroke="${css("--border-strong")}" stroke-width=".3"/></svg>
  <div style="display:flex;justify-content:space-between;font-size:10.5px" class="faint"><span>${esc(labels[0] || "")}</span><span>${esc(labels[labels.length - 1] || "")}</span></div>`;
}
function lines(labels, series, h = 90) {
  const all = series.flatMap(s => s.v.filter(isNum));
  if (!all.length) return `<div class="muted">No data.</div>`;
  const mn = Math.min(...all), mx = Math.max(...all), rg = (mx - mn) || 1;
  const n = labels.length;
  return `<svg width="100%" height="${h}" viewBox="0 0 100 ${h}" preserveAspectRatio="none">${series.map(s => `<polyline fill="none" stroke="${s.c}" stroke-width="1.6" vector-effect="non-scaling-stroke" points="${s.v.map((x, i) => isNum(x) ? `${(i / Math.max(1, n - 1) * 100).toFixed(2)},${(h - 4 - (x - mn) / rg * (h - 8)).toFixed(2)}` : "").filter(Boolean).join(" ")}"/>`).join("")}</svg>
  <div class="legend">${series.map(s => `<span><i style="background:${s.c}"></i>${esc(s.l)} ${isNum(s.v[s.v.length - 1]) ? s.v[s.v.length - 1].toFixed(1) + "%" : ""}</span>`).join("")}</div>`;
}
function drawFund(sym) {
  const f = fundOf(sym);
  const a = $("#fund-np"), b = $("#fund-own");
  if (!f) { if (a) a.innerHTML = `<div class="muted">No filings read.</div>`; if (b) b.innerHTML = ""; return; }
  if (a) a.innerHTML = (f.np || []).length ? bars(f.q_labels || [], f.np) : `<div class="muted">No quarterly data.</div>`;
  if (b) b.innerHTML = (f.prom || []).length ? lines(f.sh_labels || [], [{ l: "Promoters", c: css("--info"), v: f.prom || [] }, { l: "FII", c: css("--ai"), v: f.fii || [] }, { l: "DII", c: css("--buy"), v: f.dii || [] }]) : `<div class="muted">No shareholding data.</div>`;
}
function sheetNews(sym) {
  const d = detailOf(sym) || {}, nm = newsMem[sym], arch = archiveNewsOf(sym);
  const n = d.news || {};
  const dl = (DEALS.rows90 || {})[sym] || [], dn = (DEALS.net90 || {})[sym];
  const dealsHtml = dl.length ? `<div class="card" style="margin-bottom:14px"><div class="card-head"><h3>Bulk &amp; block deals, 90 days</h3>${dealChip(sym)}<span class="hint">same-session buy+sell churn excluded${dn ? " · net " + inrShort(dn.net) : ""}</span></div>
      ${dl.map(r => `<div class="news-item"><div class="d">${esc(dateLabel(r.d))}</div><div><div class="h"><span class="${r.side === "BUY" ? "pos" : "neg"}">${r.side === "BUY" ? "▲ bought" : "▼ sold"}</span> ${num(r.qty)} shares at ${px(r.price)} · ${inrShort(r.qty * r.price)}</div><div class="src">${esc(r.client)} · ${esc(r.kind)} deal</div></div></div>`).join("")}</div>` : "";
  return `${dealsHtml}${nm ? `<div class="card" style="margin-bottom:14px"><div class="card-head"><h3>90-day story memory</h3>${nm.primed ? '<span class="chip sm info">news-primed</span>' : ""}${nm.n_neg ? `<span class="chip sm risk">${nm.n_neg} negative</span>` : ""}</div>
      <div class="memo">${esc(nm.summary || "")}</div>
      <div style="margin-top:8px">${(nm.events || []).slice(-12).reverse().map(e => `<div class="news-item"><div class="d">${esc(String(e[2]).slice(0, 10))}</div><div class="h"><span class="${e[1] === "neg" ? "neg" : e[1] === "pos" ? "pos" : "muted"}">${e[1] === "neg" ? "▼" : e[1] === "pos" ? "▲" : "·"}</span> ${esc(e[0])}</div></div>`).join("")}</div></div>` : ""}
    ${n.count ? `<div class="muted" style="font-size:12.5px;margin-bottom:8px">At the last scoring: ${num(n.stories)} stories from ${num(n.count)} articles (${num(n.trusted)} from tier-1 sources), net tone ${isNum(n.sentiment) ? n.sentiment.toFixed(2) : "—"}.</div>` : ""}
    <div class="card"><div class="card-head"><h3>Filings and headlines</h3><span class="hint">last 30 days</span></div>
      ${arch.length ? arch.map(x => `<div class="news-item"><div class="d">${esc(x.d)}</div><div><div class="h">${x.u && /^https?:/.test(x.u) ? `<a href="${esc(x.u)}" target="_blank" rel="noopener">${esc(x.t)}</a>` : esc(x.t)}</div><div class="src">${esc(x.src || "")}</div></div></div>`).join("") : `<div class="muted">No filings or matched headlines in the archive for the last 30 days.</div>`}</div>`;
}
function sheetResearch(sym) {
  const v = verdictBy[sym], pk = pickBy[sym];
  if (!v && !pk) return `<div class="empty">No AI research on ${esc(sym)} in the last 10 days. The analyst researches the top buy alerts each night; the committee picks 3–5 names a week.</div>`;
  return `${v ? `<div class="card accent-ai"><div class="card-head"><h3>Nightly analyst</h3>${verdictChip(v, true)}${v.size ? `<span class="chip sm ghost">${esc(v.size)}</span>` : ""}</div>
      <div class="memo"><p>${esc(v.why)}</p>${(v.whys || []).length ? `<h4>Evidence</h4><ul>${v.whys.map(w => `<li>${esc(w)}</li>`).join("")}</ul>` : ""}${(v.risks || []).length ? `<h4>Risks</h4><ul>${v.risks.map(w => `<li>${esc(w)}</li>`).join("")}</ul>` : ""}${v.flip ? `<h4>What would change the view</h4><p>${esc(v.flip)}</p>` : ""}</div></div>` : ""}
    ${pk ? `<div class="card accent-ai" style="margin-top:14px"><div class="card-head"><h3>Weekly committee</h3><span class="chip sm ai">${esc(pk.conviction || "")}</span></div>
      <div class="memo"><p><b>Thesis.</b> ${esc(pk.thesis || "")}</p>${pk.catalyst ? `<h4>Catalyst</h4><p>${esc(pk.catalyst)}</p>` : ""}${pk.risks ? `<h4>Risks</h4><p>${esc(Array.isArray(pk.risks) ? pk.risks.join(" ") : pk.risks)}</p>` : ""}${pk.watch_for ? `<h4>Watch for</h4><p>${esc(pk.watch_for)}</p>` : ""}</div></div>` : ""}`;
}
function sheetHistory(sym) {
  const sc = (D.scorecard || []).filter(r => r.sym === sym);
  const led = ((D.paper || {}).ledger || []).filter(l => l.sym === sym);
  return `<div class="card flush"><div class="card-head"><h3>Buy alerts on ${esc(sym)}</h3><span class="hint">${sc.length} in the journal</span></div>
    ${sc.length ? `<div class="table-wrap"><table class="t"><thead><tr><th>When</th><th>Type</th><th class="r">Score</th><th class="r">Alert ₹</th><th class="r">Return</th><th class="r">Plan R</th><th>Status</th></tr></thead><tbody>${sc.map(r => `<tr style="cursor:default"><td class="num">${esc(String(r.d).slice(0, 10))}</td><td>${esc((VOC.kinds || {})[r.kind] || r.kind)}</td><td class="r num">${isNum(r.conv) ? r.conv.toFixed(0) : "—"}</td><td class="r num">${px(r.entry)}</td><td class="r num ${cls(r.ret)}">${pct(r.ret)}</td><td class="r num ${cls(r.planr)}">${rr(r.planr)}</td><td class="muted">${esc(r.status)}</td></tr>`).join("")}</tbody></table></div>` : `<div class="muted" style="padding:0 18px 16px">Never alerted.</div>`}</div>
    ${led.length ? `<div class="card" style="margin-top:14px"><div class="card-head"><h3>Paper book fills</h3></div>${led.map(l => `<div class="lrow" style="cursor:default"><span>${esc(l.d)} · ${esc(l.action)} ${esc(l.lot)} · ${esc(l.shares)} @ ${esc(l.price)}</span><span class="num ${cls(+l.pnl)}">${l.pnl !== "" ? inr(+l.pnl) : ""}</span></div>`).join("")}</div>` : ""}`;
}

/* ================================================================= charts */
function makeChart(el, opt = {}) {
  // autoSize: the library's own ResizeObserver, which only redraws on a real
  // size change. A hand-rolled observer here re-applied the size on every
  // callback and could loop when a scrollbar appeared or vanished.
  const ch = LightweightCharts.createChart(el, {
    autoSize: true,
    layout: { background: { type: "solid", color: css("--surface") }, textColor: css("--muted"), fontFamily: "Inter, system-ui, sans-serif", fontSize: 11 },
    grid: { vertLines: { color: css("--chart-grid") }, horzLines: { color: css("--chart-grid") } },
    rightPriceScale: { borderColor: css("--border"), mode: opt.log ? 1 : 0 },
    timeScale: { borderColor: css("--border"), rightOffset: 3 },
    crosshair: { mode: 0 },
    handleScroll: !opt.compact, handleScale: !opt.compact,
  });
  (opt.bucket || _sheetCharts).push(ch);
  return ch;
}
function sma(vals, n) { const out = []; let s = 0; for (let i = 0; i < vals.length; i++) { s += vals[i]; if (i >= n) s -= vals[i - n]; out.push(i >= n - 1 ? s / n : null); } return out; }
function drawCandles(el, sym, o = {}) {
  if (!el) return;
  const data = ohlcOf(sym);
  if (!window.LightweightCharts) { el.innerHTML = `<div class="empty" style="margin:14px">Charts need an internet connection (the chart library loads from a CDN).</div>`; return; }
  if (!data || data.length < 5) { el.innerHTML = `<div class="empty" style="margin:14px">No price history on this build for ${esc(sym)}.</div>`; return; }
  const ch = makeChart(el, o);
  const up = css("--buy"), dn = css("--risk");
  const c = ch.addCandlestickSeries({ upColor: up, downColor: dn, borderVisible: false, wickUpColor: up, wickDownColor: dn, priceLineVisible: false });
  c.setData(data.map(r => ({ time: r[0], open: r[1], high: r[2], low: r[3], close: r[4] })));
  const vol = ch.addHistogramSeries({ priceFormat: { type: "volume" }, priceScaleId: "", lastValueVisible: false, priceLineVisible: false });
  vol.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
  vol.setData(data.map(r => ({ time: r[0], value: r[5] || 0, color: (r[4] >= r[1] ? up : dn) + "55" })));
  const closes = data.map(r => r[4]);
  const legend = [];
  [[50, css("--info"), "50-day"], [150, css("--watch"), "150-day (30-week)"]].forEach(([n, col, l]) => {
    const s = sma(closes, n); if (!s.some(x => x != null)) return;
    const ls = ch.addLineSeries({ color: col, lineWidth: 1.4, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    ls.setData(data.map((r, i) => s[i] != null ? { time: r[0], value: s[i] } : null).filter(Boolean));
    legend.push(`<span><i style="background:${col}"></i>${l}</span>`);
  });
  const line = (price, color, title) => { if (isNum(price)) c.createPriceLine({ price, color, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title }); };
  line(o.pivot, css("--watch"), "pivot");
  if (isNum(o.pivot)) line(o.pivot * 1.05, css("--faint"), "+5%");
  line(o.stop, css("--risk"), "stop");
  line(o.entry, css("--info"), "entry");
  line(o.partial, css("--buy"), "+2.5R");
  const alerts = (D.scorecard || []).filter(r => r.sym === sym).map(r => String(r.d).slice(0, 10));
  const dates = new Set(data.map(r => r[0]));
  const marks = [...new Set(alerts)].map(d => { let t = d; if (!dates.has(t)) { const nx = data.find(r => r[0] >= d); t = nx ? nx[0] : null; } return t; }).filter(Boolean).sort().map(t => ({ time: t, position: "belowBar", color: css("--ai"), shape: "arrowUp", text: o.compact ? "" : "alert" }));
  if (marks.length) c.setMarkers(marks);
  const n = { "3M": 63, "6M": 126, "1Y": 260 }[o.range || "6M"] || 126;
  const from = data[Math.max(0, data.length - n)][0];
  ch.timeScale().setVisibleRange({ from, to: data[data.length - 1][0] });
  if (!o.compact) { const lg = document.createElement("div"); lg.className = "chart-legend"; lg.innerHTML = legend.join(""); el.appendChild(lg); }
  if (o.rsBox) drawRS(o.rsBox, sym, data, ch, from);
}
function drawRS(el, sym, data, main, from) {
  const nifty = D.nifty || [];
  if (!nifty.length) { el.style.display = "none"; return; }
  const nm = Object.fromEntries(nifty.map(r => [r[0], r[1]]));
  const pts = data.filter(r => nm[r[0]]).map(r => ({ time: r[0], value: r[4] / nm[r[0]] }));
  if (pts.length < 10) { el.style.display = "none"; return; }
  const base = pts[0].value; pts.forEach(p => p.value = p.value / base * 100);
  const ch = makeChart(el, {});
  ch.applyOptions({ timeScale: { visible: false }, rightPriceScale: { scaleMargins: { top: .15, bottom: .1 } } });
  const s = ch.addLineSeries({ color: css("--ai"), lineWidth: 1.6, priceLineVisible: false, lastValueVisible: false });
  s.setData(pts);
  // mark relative-strength highs: leadership often shows up here before price
  // (IBD's "blue dot"). A high only counts once it is judged against at least
  // six months of history — early points in the window are trivially "new highs".
  let mx = -Infinity; const hi = [];
  pts.forEach((p, i) => { if (p.value > mx) { mx = p.value; if (i >= 120) hi.push({ time: p.time, position: "aboveBar", color: css("--ai"), shape: "circle", size: 0.4 }); } });
  if (hi.length) s.setMarkers(hi.slice(-6));
  const lg = document.createElement("div"); lg.className = "chart-legend"; lg.innerHTML = `<span><i style="background:${css("--ai")}"></i>Relative strength vs NIFTY 50 · dots = new highs</span>`; el.appendChild(lg);
  try {
    ch.timeScale().setVisibleRange({ from, to: pts[pts.length - 1].time });
    main.timeScale().subscribeVisibleTimeRangeChange(r => { if (r) try { ch.timeScale().setVisibleRange(r); } catch (e) { } });
  } catch (e) { }
}

/* ================================================================ palette */
let _pal = { items: [], i: 0 };
function openPalette() { $("#pal").classList.add("on"); const q = $("#palq"); q.value = ""; q.focus(); palSearch(""); }
function closePalette() { $("#pal").classList.remove("on"); }
function palSearch(q) {
  q = q.trim().toLowerCase();
  const pages = PAGES.filter(p => !(p.hidden && p.hidden())).map(p => ({ type: "page", id: p.id, label: p.label }));
  let items = [];
  if (!q) items = [...pages, ...buySignals().map(a => ({ type: "stock", sym: a.sym })), ...readySetups().slice(0, 8).map(s => ({ type: "stock", sym: s.sym }))];
  else {
    items = pages.filter(p => p.label.toLowerCase().includes(q));
    const scored = ROWS.map(r => {
      const s = r.sym.toLowerCase(), c = (r.company || "").toLowerCase();
      const k = s === q ? 0 : s.startsWith(q) ? 1 : c.startsWith(q) ? 2 : s.includes(q) ? 3 : c.includes(q) ? 4 : 9;
      return [k, r];
    }).filter(x => x[0] < 9).sort((a, b) => a[0] - b[0] || (b[1].rs || 0) - (a[1].rs || 0)).slice(0, 40);
    items = items.concat(scored.map(x => ({ type: "stock", sym: x[1].sym })));
  }
  _pal = { items, i: 0 };
  $("#pallist").innerHTML = items.map((it, i) => {
    if (it.type === "page") return `<div class="pal-item ${i === 0 ? "on" : ""}" data-pi="${i}"><span class="muted">Go to</span><span><b>${esc(it.label)}</b></span><span class="kbd">page</span></div>`;
    const r = rowBy[it.sym] || {};
    return `<div class="pal-item ${i === 0 ? "on" : ""}" data-pi="${i}"><span class="sym">${esc(it.sym)}</span><span class="co" style="max-width:none">${esc(r.company || "")}</span><span>${stageChip(r.tag)}</span></div>`;
  }).join("") || `<div class="muted" style="padding:14px">No match.</div>`;
}
function palMove(d) {
  if (!_pal.items.length) return;
  _pal.i = (_pal.i + d + _pal.items.length) % _pal.items.length;
  $$("#pallist .pal-item").forEach((el, i) => el.classList.toggle("on", i === _pal.i));
  const el = $(`#pallist [data-pi="${_pal.i}"]`); if (el) el.scrollIntoView({ block: "nearest" });
}
function palPick(i) {
  const it = _pal.items[i == null ? _pal.i : i]; if (!it) return;
  closePalette();
  if (it.type === "page") go(it.id); else openStock(it.sym, ROWS.map(r => r.sym));
}

/* ================================================================= events */
document.addEventListener("click", e => {
  const t = e.target;
  const goEl = t.closest("[data-go]");
  if (goEl) {
    const id = goEl.dataset.go;
    if (id === "more") { go(["research", "record", "penny", "system"].includes(S.page) ? S.page : "research"); return; }
    if (goEl.dataset.sub) { if (id === "research") S.research = goEl.dataset.sub; go(id, goEl.dataset.sub); } else go(id);
    return;
  }
  if (t.closest("#railsearch")) { openPalette(); return; }
  if (t.closest("#themebtn")) {
    const n = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = n; store("gs-theme", n); renderShell();
    if (S.stock) renderSheetBody(); else renderPage();
    return;
  }
  if (t.closest("#scrim") || t.closest("#shclose")) { closeSheet(); return; }
  if (t.closest("#shprev")) { stepStock(-1); return; }
  if (t.closest("#shnext")) { stepStock(1); return; }
  const tab = t.closest("[data-shtab]"); if (tab) { S.sheetTab = tab.dataset.shtab; $$("[data-shtab]").forEach(b => b.classList.toggle("on", b === tab)); renderSheetBody(); return; }
  const rg = t.closest("[data-range]"); if (rg) { S.chartRange = rg.dataset.range; renderSheetBody(); return; }
  const pi = t.closest("[data-pi]"); if (pi) { palPick(+pi.dataset.pi); return; }
  if (t.closest("#pal") && !t.closest(".pal-box")) { closePalette(); return; }
  const ca = t.closest("[data-copy-alerts]"); if (ca) { const list = ca.dataset.copyAlerts === "setups" ? setupsList().filter(s => s.pivot) : readySetups().slice(0, 10); copyText(alertText(list), "Alert list copied"); return; }
  const c1 = t.closest("[data-copy-one]"); if (c1) { const s = setupBy[c1.dataset.copyOne]; if (s) copyText(alertText([s]), "Alert copied"); return; }
  const sv = t.closest("[data-setview]"); if (sv) { S.setups.view = sv.dataset.setview; S.setups.sel = 0; history.replaceState(null, "", "#/setups/" + S.setups.view); S.sub = S.setups.view; renderPage(); return; }
  const srow = t.closest("#setuptbl tbody tr"); if (srow && !t.closest("[data-sym]:not(tr)")) {
    const i = +srow.dataset.idx;
    if (S.setups.sel === i && e.detail === 2) { const s = setupsList()[i]; if (s) openStock(s.sym, setupsList().map(x => x.sym)); return; }
    S.setups.sel = i; $$("#setuptbl tbody tr").forEach((r, k) => r.classList.toggle("sel", k === i)); drawSetupPreview(); return;
  }
  const sview = t.closest("[data-sview]"); if (sview) { S.screener.view = sview.dataset.sview; S.screener.limit = 150; renderPage(); return; }
  const smap = t.closest("[data-map]"); if (smap) { S.screener.map = smap.dataset.map === "1"; renderPage(); return; }
  const sort = t.closest("[data-sort]"); if (sort) { const k = sort.dataset.sort; if (S.screener.sort === k) S.screener.dir *= -1; else { S.screener.sort = k; S.screener.dir = ["sym", "tag", "tier", "ind"].includes(k) ? 1 : -1; } renderPage(); return; }
  if (t.closest("#smore")) { S.screener.limit += 200; renderPage(); return; }
  const rs = t.closest("[data-research]"); if (rs) { S.research = S.sub = rs.dataset.research; history.replaceState(null, "", "#/research/" + S.research); renderPage(); return; }
  const rc = t.closest("[data-record]"); if (rc) { S.record = S.sub = rc.dataset.record; history.replaceState(null, "", "#/record/" + S.record); renderPage(); return; }
  const pa = t.closest("[data-parm]"); if (pa) { S.penny.arm = pa.dataset.parm; renderPage(); return; }
  const run = t.closest("[data-run]"); if (run) {
    fetch("/api/run/" + run.dataset.run, { method: "POST" }).then(r => r.json()).then(j => { toast(j.error || ("Started " + j.started)); setTimeout(probeRunPanel, 600); }).catch(() => toast("Run panel unavailable"));
    return;
  }
  const symEl = t.closest("[data-sym]");
  if (symEl && !t.closest("a")) {
    const row = symEl.closest("tr[data-ctx]");
    let ctx = null;
    if (row) ctx = $$("tr[data-ctx='" + row.dataset.ctx + "']").map(r => r.dataset.sym);
    openStock(symEl.dataset.sym, ctx);
  }
});
document.addEventListener("input", e => {
  const t = e.target;
  if (t.id === "palq") { palSearch(t.value); return; }
  if (t.id === "sq") { S.screener.q = t.value; S.screener.limit = 150; debounce(() => { renderPage(); const i = $("#sq"); if (i) { i.focus(); i.setSelectionRange(i.value.length, i.value.length); } }, 180); return; }
  if (t.id === "pq") { S.penny.q = t.value; debounce(() => { renderPage(); const i = $("#pq"); if (i) { i.focus(); i.setSelectionRange(i.value.length, i.value.length); } }, 180); }
});
document.addEventListener("change", e => {
  const t = e.target;
  if (t.id === "sind") { S.screener.ind = t.value; renderPage(); }
  if (t.id === "stier") { S.screener.tier = t.value; renderPage(); }
  if (t.id === "sveto") { S.screener.hideVeto = t.checked; renderPage(); }
  if (t.id === "pveto") { S.penny.showVeto = t.checked; renderPage(); }
});
let _deb = null; function debounce(fn, ms) { clearTimeout(_deb); _deb = setTimeout(fn, ms); }
document.addEventListener("keydown", e => {
  const typing = /INPUT|TEXTAREA|SELECT/.test((e.target || {}).tagName || "");
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); openPalette(); return; }
  if ($("#pal").classList.contains("on")) {
    if (e.key === "Escape") closePalette();
    else if (e.key === "ArrowDown") { e.preventDefault(); palMove(1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); palMove(-1); }
    else if (e.key === "Enter") { e.preventDefault(); palPick(); }
    return;
  }
  if (typing) return;
  if (e.key === "/") { e.preventDefault(); openPalette(); return; }
  if (S.stock) {
    if (e.key === "Escape") closeSheet();
    else if (e.key === "ArrowRight") stepStock(1);
    else if (e.key === "ArrowLeft") stepStock(-1);
    return;
  }
  if (S.page === "setups" && ["ArrowDown", "ArrowUp", "j", "k", "Enter"].includes(e.key)) {
    const list = setupsList();
    if (!list.length) return;
    e.preventDefault();
    if (e.key === "Enter") { const s = list[S.setups.sel]; if (s) openStock(s.sym, list.map(x => x.sym)); return; }
    S.setups.sel = Math.max(0, Math.min(list.length - 1, S.setups.sel + ((e.key === "ArrowDown" || e.key === "j") ? 1 : -1)));
    $$("#setuptbl tbody tr").forEach((r, k) => r.classList.toggle("sel", k === S.setups.sel));
    const r = $(`#setuptbl tbody tr[data-idx="${S.setups.sel}"]`); if (r) r.scrollIntoView({ block: "nearest" });
    drawSetupPreview();
    return;
  }
  const n = parseInt(e.key, 10);
  if (n >= 1 && n <= 8 && !e.ctrlKey && !e.metaKey && !e.altKey) { const vis = PAGES.filter(p => !(p.hidden && p.hidden())); if (vis[n - 1]) go(vis[n - 1].id); }
});
/* tooltips: one floating element, positioned on hover (desktop) or tap (touch) */
(function () {
  const tip = $("#tip"); let cur = null;
  function show(el) {
    const txt = el.getAttribute("data-tip"); if (!txt) return;
    cur = el; tip.textContent = txt; tip.classList.add("on");
    const r = el.getBoundingClientRect(), tw = tip.offsetWidth, th = tip.offsetHeight;
    let x = r.left + r.width / 2 - tw / 2, y = r.bottom + 8;
    x = Math.max(8, Math.min(window.innerWidth - tw - 8, x));
    if (y + th > window.innerHeight - 8) y = r.top - th - 8;
    tip.style.left = x + "px"; tip.style.top = y + "px";
  }
  function hide() { cur = null; tip.classList.remove("on"); }
  document.addEventListener("mouseover", e => { const el = e.target.closest("[data-tip]"); if (el && el !== cur) show(el); else if (!el && cur) hide(); });
  document.addEventListener("scroll", hide, true);
  document.addEventListener("touchstart", e => { const el = e.target.closest(".info-i"); if (el) show(el); else hide(); }, { passive: true });
})();
window.addEventListener("hashchange", onRoute);
window.addEventListener("popstate", () => { if (!/^#\/stock\//.test(location.hash)) closeSheet(true); });

/* =================================================================== boot */
onRoute();
