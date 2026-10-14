/* Golden Stock — v10 interface (2026-10-14). DESIGN.md is the rulebook.

   PHONE FIRST, ONE STORY. Every screen is one step of the same job, making the
   investor money: FIND (Screener: all stocks with conviction, multibaggers,
   penny), UNDERSTAND (Research and the stock sheet), ACT (Home and Watchlist),
   TRACK (Performance). Nothing is hidden on a phone: tables swipe with the
   stock and its conviction frozen; everything else is a card.

   v9 history, kept below for the reasoning trail.

   ORGANISED AROUND WHAT YOU DO, not around what the system measures.
     Home         your to-do list: buy today, set price alerts, research, heads-up
     Watchlist    a terminal: the list on the left, everything about the stock on the right
     Explore      every stock, the market, themes and industries, penny stocks
     Research     the AI analyst, the committee, news and filings, deals, policy
     Performance  is the system working? paper books, the capital gate, the
                  forward record and backtests: everything that needs no action
                  from you lives here, away from the to-do list

   The ordering of every list follows the evidence: a fired trigger outranks a
   base, a base outranks an uptrend, and the research score rules names out
   rather than ranking the rest. Nothing here places an order or sizes a trade.
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
const MB = X.mbsleeve || {};                       // multibagger sleeve (paper, pre-registered)
const VB = X.vbsleeve || {};                       // value-breakout sleeve (paper, pre-registered)
const PM = X.pmsleeve || {};                       // promoter-buying sleeve (paper, pre-registered)
const MRS = (X.mbresearch || {}).items || {};      // the report analyst's reads (scripts/ai_multibagger.py)
const MBX = (X.radar || {}).mb || {};              // the rebuilt multibagger score (research/mb_live.py)
const MBS = MBX.stocks || {}, MBCFG = MBX.config || {};
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
/* Plans are sized for the system's paper account (D.capital, Rs 10 L) at up to
   D.risk_pct a trade. A reader can set their own account size in the Guide; it
   stays in this browser, and every quantity, position value and rupee risk
   scales with it. The percentages do not change. */
function myCapital() { try { const v = +localStorage.getItem("gs.capital"); return v >= 10000 ? v : CAPITAL; } catch (e) { return CAPITAL; } }
function sized(p) {
  if (!p || p.skip || !isNum(p.shares)) return p;
  const f = myCapital() / CAPITAL; if (f === 1) return p;
  const sh = Math.floor(p.shares * f), k = p.shares ? sh / p.shares : f;
  return Object.assign({}, p, { shares: sh, risk: isNum(p.risk) ? p.risk * k : p.risk, value: isNum(p.value) ? p.value * k : p.value });
}
function capWord() { return inrShort(myCapital()).replace(".00 L", " L").replace(".00 Cr", " Cr"); }
/* Saved stocks: the reader's own list, in this browser only (Watchlist > Saved). */
const SAVED = (function () { let s = []; try { s = JSON.parse(localStorage.getItem("gs.saved") || "[]"); } catch (e) { } return new Set(Array.isArray(s) ? s : []); })();
function toggleSaved(sym) {
  if (SAVED.has(sym)) SAVED.delete(sym); else SAVED.add(sym);
  try { localStorage.setItem("gs.saved", JSON.stringify([...SAVED])); } catch (e) { }
  return SAVED.has(sym);
}
function saveBtn(sym) {
  const on = SAVED.has(sym);
  return `<button class="icon-btn save-btn ${on ? "on" : ""}" data-save="${esc(sym)}" aria-pressed="${on}" aria-label="${on ? "Remove from saved stocks" : "Save this stock"}">${I.star}</button>`;
}

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
function sentenceCase(w) { w = String(w || ""); return w && w === w.toUpperCase() ? w.charAt(0) + w.slice(1).toLowerCase() : w; }
function stageWord(t) { const w = VOC.tags && VOC.tags[t] || t || "—"; return w === "—" ? w : w.charAt(0).toUpperCase() + w.slice(1).toLowerCase(); }
function stageChip(t) { return t ? `<span class="tag-stage stage-${esc(t)}" data-tip="${esc(VOC.tagtips && VOC.tagtips[t] || "")}">${esc(stageWord(t))}</span>` : `<span class="faint">—</span>`; }
const SETUP_WORD = { "VALIDATED": "Breakout", "VALIDATED (EXTENDED)": "Breakout · extended", "AWAITING TRIGGER": "Base ready", "NO VCP BASE": "No base", "EP EVENT": "Gap-up" };
function setupChip(st) {
  const c = st === "VALIDATED" ? "buy" : st === "EP EVENT" ? "ep" : st === "AWAITING TRIGGER" ? "watch" : st === "VALIDATED (EXTENDED)" ? "watch" : "ghost";
  return st ? `<span class="chip sm ${c}">${esc(SETUP_WORD[st] || st)}</span>` : `<span class="faint">—</span>`;
}
function sizeChip(sz) {
  const s = String(sz || "").toUpperCase();
  const w = s.includes("HALF") ? "half size" : s.includes("FULL") ? "full size" : "";
  return w ? `<span class="chip sm ghost" data-tip="The size the AI check suggests for this position.">${w}</span>` : "";
}
function verdictChip(v, withDate) {
  if (!v) return "";
  const c = v.verdict === "BUY" ? "buy" : v.verdict === "SKIP" ? "risk" : v.verdict === "WAIT" ? "watch" : "ghost";
  return `<span class="chip sm ${c}" data-tip="${esc("AI check" + (v.conv ? " (" + String(v.conv).toLowerCase() + " confidence)" : "") + ": " + (v.why || ""))}">AI check: ${esc(VERDICT_WORD[v.verdict] || v.verdict)}${withDate && v.stamp ? " · " + dateLabel(v.stamp) : ""}</span>`;
}
/* exchange surveillance in words a buyer understands */
function survWords(f) {
  const c = String(f.code || ""), d = String(f.detail || "");
  if (/^ASM/i.test(c)) return "on the exchange's extra-surveillance list (ASM" + (d ? ", " + d.replace(/^LT\b/, "long-term").replace(/^ST\b/, "short-term") : "") + ")";
  if (/^GSM/i.test(c)) return "on the exchange's graded-surveillance list (GSM" + (d ? ", " + d : "") + ")";
  const b = c.match(/BAND\s*(\d+)/i);
  if (b) return "allowed to move at most " + b[1] + "% a day";
  if (/^(BE|BZ|T2T)/i.test(c)) return "trade-for-trade only: every buy must be paid for and delivered, no intraday trading";
  return c + (d ? " (" + d + ")" : "");
}
function survText(flags) {
  const w = (flags || []).map(survWords);
  if (!w.length) return "";
  const s = w.join("; ");
  return s.charAt(0).toUpperCase() + s.slice(1) + ".";
}
function survChips(sym) {
  const s = survBy[sym];
  if (!s || !s.flags) return "";
  return s.flags.map(f => `<span class="chip sm risk" data-tip="${esc(survText([f]))}">${esc(f.code)}</span>`).join("");
}
function clip(t, n) {
  t = String(t || "").trim();
  if (t.length <= n) return t;
  const cut = t.slice(0, n), sp = cut.lastIndexOf(" ");
  return (sp > n * 0.6 ? cut.slice(0, sp) : cut).replace(/[\s,;:(—-]+$/, "") + "…";
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
function toast(msg) { const t = $("#toast"); t.textContent = msg; t.classList.add("on"); clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove("on"), Math.max(2200, String(msg).length * 55)); }
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
function riskShare(plan) { return plan && isNum(plan.risk) ? plan.risk / myCapital() * 100 : null; }
/* ---- v8 (2026-09-28): the classic dashboard's visual language inside the v7
   layout. Bars for every score, a ring for the market, sparklines in lists and
   mini charts for the business; measurements only where a decision needs them. */
function scoreCol(v) { return !isNum(v) ? "var(--faint)" : v >= 70 ? "var(--buy)" : v >= 50 ? "var(--info)" : v >= 40 ? "var(--watch)" : "var(--risk)"; }
function dimCol(s) { return s == null ? "var(--faint)" : s >= 0.7 ? "var(--buy)" : s >= 0.4 ? "var(--watch)" : "var(--risk)"; }
function rsCol(v) { return !isNum(v) ? "var(--faint)" : v >= 90 ? "var(--buy)" : v >= 70 ? "var(--info)" : "var(--faint)"; }
function cbar(v, col, tip) {
  if (!isNum(v)) return `<span class="faint">—</span>`;
  const p = Math.max(0, Math.min(100, v));
  return `<span class="cbar"${tip ? ` data-tip="${esc(tip)}"` : ""}><span class="track"><i style="width:${p.toFixed(0)}%;background:${col}"></i></span><b>${Math.round(v)}</b></span>`;
}
function scoreCell(v) { return cbar(v, scoreCol(v)); }
function rsCell(v) { return cbar(v, rsCol(v)); }
function ring(frac, big, small, col, size) {
  size = size || 86;
  const r = size / 2 - 6, c = 2 * Math.PI * r, p = Math.max(0, Math.min(1, frac || 0)), m = size / 2;
  return `<div class="ring" style="width:${size}px;height:${size}px"><svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" aria-hidden="true">
    <circle cx="${m}" cy="${m}" r="${r}" fill="none" stroke="var(--surface-3)" stroke-width="7"/>
    <circle cx="${m}" cy="${m}" r="${r}" fill="none" stroke="${col}" stroke-width="7" stroke-linecap="round" stroke-dasharray="${(c * p).toFixed(1)} ${c.toFixed(1)}" transform="rotate(-90 ${m} ${m})"/></svg>
    <div class="c"><b>${big}</b>${small ? `<span>${small}</span>` : ""}</div></div>`;
}
/* the eight weighted questions as bars — the classic drawer's "Why this score" */
const PLAIN_DIM = [
  [/\bVCP none\b/g, "no base"], [/\bVCP live\b/g, "a base is forming"], [/\bVCP\b/g, "base"],
  [/\bRS percentile 100\b/g, "among the very strongest stocks"],
  [/\bRS percentile (\d+)/g, "stronger than $1% of stocks"],
  [/\bCONFIRMED\b/g, "confirmed"], [/\bNOT\b/g, "not"], [/\bWHY\b/g, "why"], [/\bMARGIN-LED\b/g, "margin-led"], [/\bOPM\b/g, "operating margin"],
  [/\bforeign accumulation into domestic distribution\b/g, "foreign investors buying while domestic funds sell"], [/\bdomestic accumulation into foreign distribution\b/g, "domestic funds buying while foreign investors sell"],
  [/\s*\(legs disagree[^)]*\)/g, ""], [/;\s*bulk\/block deals[^;]*$/g, ""], [/ > /g, " above "], [/ < /g, " below "], [/\bRs ?(\d)/g, "₹$1"], [/\bTT (\d)\/8\b/g, "$1 of 8 trend checks pass"],
  [/\bstage 2\b/gi, "in a rising stage"], [/\bVCP live\b/g, "a base is forming"], [/\bqtr PAT YoY\b/g, "quarterly profit vs a year ago"],
  [/\bPAT\b/g, "profit"], [/\bTTM\b/g, "last 12 months"], [/\b(\d+)y\b/g, "$1 years"], [/\bYoY\b/g, "on a year ago"],
  [/(\d)pp\b/g, "$1 points"], [/->/g, " to "], [/\s*\(news-based v\d+\)/g, ""], [/\bscoreable\b/g, "usable"],
  [/;\s*bulk\/block deals not yet wired in/g, ""], [/\bfroth: /g, "expensive: "], [/\blead: news;\s*/g, ""],
  [/\s*\(theme map, price-derived\)/g, ""], [/\bdatapage\b/g, "price pages"], [/\bprice_move\b/g, "price-move stories"],
  [/;?\s*\d+ filtered \([^)]*\)/g, ""], [/sentiment (\w+) \((\d+)\+\/(\d+)-\)/g, "tone $1 ($2 positive, $3 negative)"],
  [/(\d+) consecutive quarter\(s\)/g, "$1 quarters in a row"], [/\s*\(not a verified zero[^)]*\)/g, ""],
  [/;\s*adverse-filing check \([^)]*\) shown separately on this card/g, ""], [/\bon heat across the (\d+) themes\b/g, "for momentum among $1 themes"],
];
const PLAIN_AI = [
  [/\bStage 2\s*\/\s*VCP base\b/g, "rising-stage base"], [/\bVCP base\b/g, "base"], [/\bVCP\b/g, "base"],
  [/\bAWAITING TRIGGER\b/g, "waiting for a breakout"], [/\bpivot\b/g, "alert price"], [/\bthe card's own read\b/g, "the system's own read"], [/\b(?:the )?card's\b/g, "the alert's"], [/\bveto checks\b/g, "red-flag checks"],
  [/\bthe card\b/g, "the alert"], [/\bATR stop\b/g, "The stop"], [/\bEP\b/g, "gap-up"], [/(\d)pp\b/g, "$1 points"],
];
function plainAI(t) { let s = String(t || ""); PLAIN_AI.forEach(([re, w]) => { s = s.replace(re, w); }); return s; }
function plainDim(t) { let s = String(t || ""); PLAIN_DIM.forEach(([re, w]) => { s = s.replace(re, w); }); return s.charAt(0).toUpperCase() + s.slice(1); }
function scoreBars(sym, compact) {
  const d = detailOf(sym);
  if (!d || !(d.dims || []).length) return `<div class="muted" style="font-size:12.5px">No score breakdown yet: the eight questions are scored for names in an uptrend or basing, and this one re-enters scoring when its chart qualifies.</div>`;
  const dims = d.dims.slice().sort((a, b) => (b.w || 0) - (a.w || 0));
  const dark = dims.filter(x => !x.live);
  return `${dark.length ? `<div class="warn" style="font-size:12px;margin-bottom:10px">Not scored: ${dark.map(x => esc(DIM_LABEL[x.k] || x.k)).join(", ")} (${num(dark.reduce((a, x) => a + (x.w || 0), 0))} of 100 points); the rest were re-weighted.</div>` : ""}
    <div class="sbars">${dims.map(x => {
      const s = x.live && isNum(x.s) ? x.s : null, p = s == null ? 0 : Math.round(s * 100);
      return `<div class="sbar"><div class="top"><span>${esc(DIM_LABEL[x.k] || x.k)}<span class="w">weight ${num(x.w)}</span></span><b style="color:${dimCol(s)}">${s == null ? "no data" : p}</b></div>
        <div class="track"><i style="width:${p}%;background:${dimCol(s)}"></i></div>${compact || !x.n ? "" : `<div class="n">${esc(plainDim(x.n))}</div>`}</div>`;
    }).join("")}</div>`;
}
const VETO_WORDS = { promoter_pledge: "Promoters have pledged their shares", leverage_plus_froth: "Heavy debt with a very high P/E" };
function vetoWords(v) {
  const s = String(v || ""), i = s.indexOf(":"), k = i > 0 ? s.slice(0, i).trim() : s.trim(), d = i > 0 ? s.slice(i + 1).trim() : "";
  const dd = d.replace(/^D\/E ([\d.]+) with P\/E ([\d.]+)$/, "debt is $1 times equity, P/E $2").replace(/% of promoter holding pledged$/, "% of their holding");
  return (VETO_WORDS[k] || sentenceCase(k.replace(/_/g, " "))) + (dd ? ": " + dd : "");
}
/* the eight answers before a veto's cap */
function rawConviction(d) {
  const live = (d.dims || []).filter(x => x.live !== false && isNum(x.w) && isNum(x.s)), w = live.reduce((a, x) => a + x.w, 0);
  return w ? live.reduce((a, x) => a + x.w * x.s, 0) / w * 100 : null;
}
/* The conviction read is dated (weekly for most names); the stage chip is
   tonight's. When the uptrend has turned since, say so beside the score. */
function convMoved(sym) {
  const d = detailOf(sym) || {}, r = rowBy[sym] || {}, day = String(d.dims_as_of || d.scored_at || "").slice(0, 10);
  if (!day || !(day < String(priceSession() || "").slice(0, 10)) || !isNum(d.tt_checks) || !r.tag) return null;
  return (d.tt_checks === 8) !== ["CONFIRMED", "EXTENDED"].includes(r.tag) ? day : null;
}
function scoreCard(sym) {
  const d = detailOf(sym) || {}, r = rowBy[sym] || {}, b = convBand(d.score, r.veto);
  return `<div class="card"><div class="card-head"><h3>Conviction</h3>${isNum(d.score) ? `<span class="chip sm ${b.cls === "buy" ? "buy" : b.cls === "watch" ? "watch" : b.cls === "risk" ? "risk" : ""}">${d.score.toFixed(0)} · ${b.word}</span>` : ""}${info("Eight weighted questions: trend and strength, earnings, balance sheet, news and catalysts, big investors, theme, governance and valuation. Each bar is how well this stock answers one of them. Measured on this system's own alerts: names under 50, and vetoed ones, lagged the market, so the score rules weak or risky companies out. Above 50 it does not rank stocks against each other.")}
      <span class="hint">${d.dims_as_of || d.scored_at ? "read " + esc(dateLabel(d.dims_as_of || d.scored_at)) : ""}${isNum(d.coverage) && d.coverage < 100 ? " · " + d.coverage.toFixed(0) + "% answered" : ""}</span></div>
    ${(d.veto_reasons || []).length ? `<div class="callout risk" style="margin-bottom:12px"><b>Vetoed.</b> ${d.veto_reasons.map(v => esc(vetoWords(v))).join("; ")}. A veto caps the score at 25 whatever the eight answers add up to${isNum(rawConviction(d)) ? ` (here ${Math.round(rawConviction(d))})` : ""}.</div>` : ""}
    ${convMoved(sym) ? `<div class="callout" style="margin-bottom:12px">The chart has changed since this read on ${esc(dateLabel(convMoved(sym)))}: tonight it is <b>${esc(stageWord(r.tag))}</b>. The trend answer below is from the read and catches up at the next one.</div>` : ""}
    ${scoreBars(sym)}</div>`;
}
/* what each layer says about one name — the classic drawer's convergence panel */
function voicesCard(sym) {
  const r = rowBy[sym] || {}, d = detailOf(sym) || {}, v = verdictBy[sym], pk = pickBy[sym], st = setupBy[sym];
  const reviewed = (D.reviewed || []).includes(sym);
  const hit = ((D.radar || {}).hits || []).find(h => h.sym === sym);
  const nm = newsMem[sym];
  const rows = [
    ["AI check", "var(--ai)", v ? (VERDICT_WORD[v.verdict] || v.verdict) + (v.stamp ? " (" + dateLabel(v.stamp) + ")" : "") : "none in the last 10 days"],
    ["Weekly pick", "var(--buy)", pk ? "picked this week" : reviewed ? "reviewed this week, passed over" : "not in this week's review"],
    ["News", "var(--watch)", hit ? hit.event + (hit.date ? " (" + dateLabel(hit.date) + ")" : "") : nm && nm.n_neg ? nm.n_neg + " negative filing(s) in 90 days" : "quiet since the last scan"],
  ];
  return `<div class="card"><div class="card-head"><h3>What the analysts say</h3>${info("The nightly analyst, the weekly committee and the news layer. They inform attention; entries and sizing stay mechanical.")}</div>
    <div class="voices">${rows.map(([k, c, t]) => `<div class="k" style="color:${c}">${k}</div><div>${esc(t)}</div>`).join("")}</div></div>`;
}
function howItWorks(text, pre) {
  return `<details class="more" style="margin-top:14px"><summary>How it works, and how it was chosen</summary><div class="card"><div class="memo"><p>${esc(text)}</p>
    ${(pre || []).length ? `<h4>Backtest</h4><ul>${pre.map(([l, v, n]) => `<li><b>${esc(l)}:</b> ${esc(v)}, ${esc(n)}</li>`).join("")}</ul>` : ""}</div></div></details>`;
}

/* ============================================================ v10 vocabulary
   One name per thing (DESIGN.md §3). Conviction is the 0-100 eight-question
   check; the weekly deep-dive's 1-5 is the "AI rating"; the nightly analyst's
   read is the "AI check"; the committee's choice is a "Weekly pick". */
const VERDICT_WORD = { BUY: "Buy", WAIT: "Wait", SKIP: "Skip" };
function convBand(v, veto) {
  if (isNum(v)) v = Math.round(v);
  if (veto) return { word: "Avoid", cls: "risk", tip: "vetoed for a governance or leverage red flag" };
  if (!isNum(v)) return { word: "—", cls: "x", tip: "not scored" };
  if (v >= 70) return { word: "Strong", cls: "buy", tip: "70 or more: strong on most of the eight questions" };
  if (v >= 50) return { word: "Moderate", cls: "mod", tip: "50 to 69: a moderate score. Above 50 the score does not rank stocks against each other" };
  return { word: "Weak", cls: "watch", tip: "under 50: names this weak have lagged the market" };
}
function convBadge(sym, val) {
  const r = rowBy[sym] || {}, s = val != null ? val : r.score;
  if (!isNum(s)) return `<div class="cvb x"><b>—</b><span class="cvb-w">${rowBy[sym] ? "not scored" : "not scanned"}</span></div>`;
  const b = convBand(s, r.veto);
  return `<div class="cvb ${b.cls}"><b>${Math.round(s)}</b><span class="cvb-w">${b.word}</span><span class="cvb-t">conviction</span></div>`;
}
function convCell(v, veto) {
  if (!isNum(v)) return `<span class="faint">—</span>`;
  const b = convBand(v, veto), col = { buy: "var(--buy)", mod: "var(--text-2)", watch: "var(--watch)", risk: "var(--risk)" }[b.cls] || "var(--faint)";
  return `<span class="cvc"><b>${Math.round(v)}</b><span class="w ${b.cls}">${b.word}</span><span class="track"><i style="width:${Math.max(0, Math.min(100, v)).toFixed(0)}%;background:${col}"></i></span></span>`;
}
function shortCo(c) { return String(c || "").replace(/\s+(Ltd\.?|Limited|Ltd)\s*$/i, "").trim(); }
function briefOf(sym) { const b = (lazy("brief") || {})[sym]; return b && b[0] ? b[0] : ""; }
function nameOf(sym) { const r = rowBy[sym]; if (r && r.company) return r.company; const b = (lazy("brief") || {})[sym]; return b && b[1] ? b[1] : ""; }
function coName(sym) { const c = shortCo(nameOf(sym)); return c && c.toUpperCase() !== String(sym).toUpperCase() ? c : ""; }
function coLine(sym) {
  const r = rowBy[sym] || {};
  const bits = [coName(sym), r.ind, r.tier ? r.tier + " cap" : ""].filter(Boolean);
  return bits.length ? bits.join(" · ") : "Outside the nightly scan";
}
function quoteOf(sym) {
  const c = closesOf(sym), r = rowBy[sym] || {}, m = MBS[sym] || {};
  const price = c.length ? c[c.length - 1] : isNum(r.close) ? r.close : m.close;
  const chg = c.length > 1 && c[c.length - 2] ? (c[c.length - 1] / c[c.length - 2] - 1) * 100 : null;
  return { price, chg };
}
/* ▲1.2% / ▼0.5%: one decimal under 10%, none above (DESIGN.md §8) */
function movePct(v) {
  if (!isNum(v)) return "";
  if (Math.abs(v) < 0.05) return "0.0%";
  return (v > 0 ? "▲" : "▼") + Math.abs(v).toFixed(Math.abs(v) < 10 ? 1 : 0) + "%";
}
/* the same card for a stock on every list (DESIGN.md §6.2) */
function stockCard(sym, o = {}) {
  const q = quoteOf(sym), cl = closesOf(sym);
  const key = o.wsel ? `data-wsel="${esc(sym)}"` : `data-sym="${esc(sym)}"`;
  return `<div class="scard ${o.sel ? "sel" : ""}" ${key}${o.ctx ? ` data-ctx="${esc(o.ctx)}"` : ""}>
    <div class="scard-m">
      <div class="l1"><span class="sym">${esc(sym)}</span>${cl.length > 2 ? `<span class="l1-spark">${spark(cl.slice(-60), 58, 20)}</span>` : ""}<span class="px num">${isNum(q.price) ? px(q.price) : ""}</span>${isNum(q.chg) ? `<span class="chg num ${cls(q.chg)}">${movePct(q.chg)}</span>` : ""}</div>
      <div class="l2">${esc(coLine(sym))}</div>
      ${o.chips ? `<div class="chips">${o.chips}</div>` : ""}
      ${o.line ? `<div class="l4">${o.line}</div>` : ""}
      ${o.sub ? `<div class="l5">${o.sub}</div>` : ""}
    </div>
    ${o.right != null ? o.right : convBadge(sym)}
  </div>`;
}
function seeAll(page, sub, label) { return `<button class="btn sm" data-go="${page}"${sub ? ` data-sub="${sub}"` : ""}>${esc(label)}</button>`; }

/* ===================================================================== icons */
const I = {
  home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/></svg>',
  watchlist: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>',
  explore: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M15.5 8.5l-2.2 4.8-4.8 2.2 2.2-4.8z"/></svg>',
  performance: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M5 20V11"/><path d="M11 20V4"/><path d="M17 20v-7"/><path d="M3 20h18"/></svg>',
  today: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/></svg>',
  setups: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 17l5-5 4 3 8-9"/><path d="M15 6h5v5"/></svg>',
  screener: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M4 6h16M7 12h10M10 18h4"/></svg>',
  portfolio: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>',
  research: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M18.5 15.5l.7 1.8 1.8.7-1.8.7-.7 1.8-.7-1.8-1.8-.7 1.8-.7z"/></svg>',
  stories: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5a2 2 0 012-2h9l5 5v11a2 2 0 01-2 2H6a2 2 0 01-2-2z"/><path d="M14 3v5h5"/><path d="M8 13h8M8 17h5"/></svg>',
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
  bolt: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2.5L4.5 13.5H11l-1 8 8.5-11H12z"/></svg>',
  bell: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8.5a6 6 0 10-12 0c0 6.5-2.5 8.5-2.5 8.5h17S18 15 18 8.5"/><path d="M13.7 20.5a2 2 0 01-3.4 0"/></svg>',
  gem: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6.5 3.5h11l4 5.5-10.5 12L.5 9z"/><path d="M.8 9h22.4M11 21L7.5 9l3.5-5.5L14.5 9z"/></svg>',
  news: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4.5h12.5a2 2 0 012 2V19a1.5 1.5 0 003 0V9h-3"/><path d="M4 4.5V19a2 2 0 002 2h14.5"/><path d="M7.5 8.5h7M7.5 12.5h7M7.5 16.5h4"/></svg>',
  pulse: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2.5 12h4l2.5-6.5 4.5 13 2.5-6.5h5.5"/></svg>',
  filter: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3.5 5h17l-6.5 8v6l-4 1.5V13z"/></svg>',
  star: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z"/></svg>',
  help: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M9.6 9.3a2.5 2.5 0 014.8 1c0 1.7-2.4 2.2-2.4 3.7"/><path d="M12 17.2h.01"/></svg>',
  back: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19.5 12h-15M10.5 18l-6-6 6-6"/></svg>',
};

/* ============================================== shared state, lists and renderers */
function healthSummary() {
  const h = D.health || [];
  const bad = h.filter(x => x.state === "fail"), warn = h.filter(x => x.state === "warn");
  return { state: bad.length ? "fail" : warn.length ? "warn" : "ok", bad, warn };
}
/* Data health without the capital gate (DESIGN.md §5.3). The gate going quiet
   for two weeks is a research fact about the trigger, not late data; it lit
   "1 stale" on every page and read as a broken system. It lives on
   Performance › System with everything else. */
function dataHealth() {
  const h = (D.health || []).filter(x => x.k !== "gate");
  const bad = h.filter(x => x.state === "fail"), warn = h.filter(x => x.state === "warn");
  return { state: bad.length ? "fail" : warn.length ? "warn" : "ok", word: bad.length ? "failing" : warn.length ? "late" : "fresh", bad, warn };
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
function underStop(a) {
  const plan = planOf(a.sym);
  return !!(plan && !plan.skip && isNum(plan.stop) && isNum(a.now_px) && a.now_px <= plan.stop);
}
function buySignals() {
  if (_buy) return _buy;
  _buy = (D.actionable || []).filter(a => (a.dokind === "act" || a.dokind === "ep") && a.status === "ACTIONABLE" && !stoppedSince(a) && !underStop(a));
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
/* The whole-market multibagger radar (scripts/multibagger_radar.py): the three
   signals that raised the odds of a stock tripling within a year in BOTH halves
   of 2005-2026 on the survivorship-free NSE panel. A research watchlist under
   forward test — never presented as a buy list. */
const RADAR_WORD = { H7: "Power play", H9: "RS leader", H14: "Discovery", H20: "Value breakout", H25: "Promoter buying" };
const RADAR_TIP = {
  H7: "Up 90%+ within 40 sessions with no pullback deeper than 25%, closing at a new high — often the surge itself, sometimes the break of a short flag after it.",
  H9: "6-month AND 12-month return both in the top 10% of the liquid market — the day it first got there.",
  H14: "Daily traded value rose from the market's bottom half to its top quarter within 60 sessions — new money arriving.",
  H25: "A promoter bought shares in the market (≥ ₹10 lakh) in the last 60 sessions AND the stock is an RS leader or passes the trend template. The smart-money survivor: in 2021–2026, 8.8% tripled within a year (market 3.7%) and the median 12-month return was +19%, twice momentum alone.",
  H20: "Cheap on free cash flow AND book value (both in the market's cheapest 30%, cash flow positive) and breaking out of a 2-year base or starting a new stage-2 uptrend. 2016–2026 evidence only; under forward test.",
};
function planOf(sym) {
  const d = detailOf(sym);
  const p = d && d.plan;
  if (!p || p.skip) return p || null;
  const risk = isNum(p.capital_at_risk) ? p.capital_at_risk : (isNum(p.shares_total) && isNum(p.risk_per_share) ? p.shares_total * p.risk_per_share : null);
  return { entry: p.entry_price, stop: p.stop_loss_price, shares: p.shares_total, t: p.shares_trading_lot, c: p.shares_core_lot, risk,
           stop_pct: isNum(p.entry_price) && isNum(p.stop_loss_price) ? (1 - p.stop_loss_price / p.entry_price) * 100 : null };
}
function buyCard(a) {
  const r = rowBy[a.sym] || {}, v = verdictBy[a.sym], plan = sized(planOf(a.sym)), st = setupBy[a.sym];
  const isEP = a.dokind === "ep";
  let zone = "";
  if (isEP && isNum(a.alert_px) && isNum(a.now_px)) {
    const ext = (a.now_px / a.alert_px - 1) * 100;
    zone = ext > 5 ? `<span class="chip sm watch">${pct(ext)} past the gap-day close — don't chase</span>`
      : ext < -3 ? `<span class="chip sm watch">${pct(ext)} below the gap-day close — the gap is being given back</span>`
      : `<span class="chip sm buy">Near the gap-day close ${px(a.alert_px)}</span>`;
  } else if (st && isNum(st.pivot) && isNum(a.now_px)) {
    const ext = (a.now_px / st.pivot - 1) * 100;
    zone = ext < -2 ? `<span class="chip sm watch">${pct(ext)} back below the alert price ${px(st.pivot)}: the breakout is failing</span>`
      : ext <= 5 ? `<span class="chip sm buy">In the buy zone (up to 5% above the alert price ${px(st.pivot)})</span>` : `<span class="chip sm watch">${pct(ext)} above the alert price, past the buy zone</span>`;
  }
  const ch = closesOf(a.sym).slice(-60);
  return `<div class="acard ${isEP ? "ep" : "buy"}" data-sym="${esc(a.sym)}">
    <div>
      <div class="top"><span class="title">${esc(a.sym)}</span>
        <span class="chip sm ${isEP ? "ep" : "buy"}">${isEP ? "Gap-up" : "Breakout"}</span>
        ${verdictChip(v)} ${survChips(a.sym)} ${a.n > 1 ? `<span class="chip sm ghost">alerted ${a.n}×</span>` : ""}</div>
      <div class="desc">${esc(r.company || "")}${r.ind ? " · " + esc(r.ind) : ""} · signalled ${esc(a.d)} at ${px(a.alert_px)} · now ${px(a.now_px)} <span class="${cls(a.chg)}">${pct(a.chg)}</span></div>
      ${zone ? `<div style="margin-top:8px">${zone}</div>` : ""}
      ${plan && !plan.skip ? `<div class="plan">
        <div><div class="k">Entry ≈</div><div class="v">${px(plan.entry)}</div></div>
        <div><div class="k">Stop</div><div class="v neg">${px(plan.stop)} <span class="muted" style="font-size:11px">(${pct(-plan.stop_pct)})</span></div></div>
        <div><div class="k">Quantity</div><div class="v">${num(plan.shares)}</div></div>
        <div><div class="k">Risk</div><div class="v">${inr(plan.risk)} <span class="muted" style="font-size:11px">${isNum(riskShare(plan)) ? riskShare(plan).toFixed(2) + "%" : ""}</span></div></div>
      </div>` : plan && plan.skip ? `<div class="why warn">No sized plan: ${esc(plan.skip_reason || "stop wider than the 12% cap")}</div>` : ""}
      ${plan && !plan.skip && isNum(a.now_px) && isNum(plan.stop) && a.now_px <= plan.stop ? `<div class="why neg"><b>Below the stop.</b> Now ${px(a.now_px)}, under the ${px(plan.stop)} stop: the setup has failed. Don't buy it.</div>`
        : plan && !plan.skip && isNum(a.now_px) && isNum(plan.stop) && a.now_px < plan.entry * 0.97 ? `<div class="why warn">Now ${px(a.now_px)}: ${Math.abs((a.now_px / plan.entry - 1) * 100).toFixed(1)}% under the signal price and only ${((a.now_px / plan.stop - 1) * 100).toFixed(1)}% above the stop.</div>` : ""}
      ${v && v.why ? `<div class="why"><span class="muted">AI:</span> ${esc(clip(v.why, 220))}</div>` : ""}
    </div>
    <div class="side">${spark(ch, 120, 40)}<button class="btn sm" data-sym="${esc(a.sym)}">Open</button></div>
  </div>`;
}
function alertText(list) {
  const day = dayName(priceSession());
  const lines = list.filter(s => s.plan && !s.plan.skip).map(s => { const p = sized(s.plan);
    return `${s.sym}: alert at ${px(s.pivot)} · buy only on a close above it with at least ${volFmt(s.vneed)} shares traded · stop ${px(p.stop)} · ${p.shares} shares (risk ${inr(p.risk)} on a ${capWord()} account)`; });
  return `Golden Stock price alerts (prices to ${day})\n` + lines.join("\n") + `\n\nSet each one as a price alert in your broker's app. An alert is a prompt to check, not an order: buy only if the day CLOSES above the alert price on at least 1.5× normal volume.`;
}
function marketPulseCard() {
  const m = X.market || {};
  const ew = (m.ew || []);
  const nf = (D.nifty || []).map(r => [r[0], r[1]]);
  function chg(series, n) { if (series.length <= n) return null; const a = series[series.length - 1 - n][1], b = series[series.length - 1][1]; return (b / a - 1) * 100; }
  const t = D.tags || {}, tot = Object.values(t).reduce((a, b) => a + b, 0) || 1;
  const segs = [["CONFIRMED", "--buy"], ["EXTENDED", "--watch"], ["ANTICIPATION", "--info"], ["WATCH", "--faint"], ["BROKEN", "--risk"]];
  return `<div class="card"><div class="card-head"><h3>Market pulse</h3><span class="hint">the last six months</span></div>
    <div class="pulse" style="grid-template-columns:repeat(2,minmax(0,1fr))">
      <div><div class="k">Small &amp; mid caps ${info("An equal-weight index of every stock this system watches: the market it actually trades, rather than the NIFTY 50.")}</div>
        <div class="v ${cls(chg(ew, 21))}">${pct(chg(ew, 21))}</div><div class="s">1 month · ${pct(chg(ew, 63))} 3 months</div></div>
      <div><div class="k">NIFTY 50</div><div class="v ${cls(chg(nf, 21))}">${pct(chg(nf, 21))}</div><div class="s">1 month · ${pct(chg(nf, 63))} 3 months</div></div>
    </div>
    <div style="margin-top:14px">${areaSpark(ew.slice(-130), 300, 64, css("--info"))}</div>
    <div class="muted" style="font-size:12px;margin-top:12px">Where the ${num(tot)} watched stocks stand</div>
    <div class="stagebar" style="margin-top:6px">${segs.map(([k, c]) => `<i style="width:${((t[k] || 0) / tot * 100).toFixed(1)}%;background:var(${c})" data-tip="${esc(stageWord(k))}: ${t[k] || 0}"></i>`).join("")}</div>
    <div class="legend">${segs.map(([k, c]) => `<span><i style="background:var(${c})"></i>${esc(stageWord(k))} ${t[k] || 0}</span>`).join("")}</div>
  </div>`;
}
function themesCard() {
  const th = ((D.themes || {}).themes || []).filter(x => !x.thin).slice().sort((a, b) => (b.heat || 0) - (a.heat || 0)).slice(0, 8);
  if (!th.length) return "";
  return `<div class="card"><div class="card-head"><h3>Hottest themes</h3>${info("Relative heat across cross-industry themes, from the 3-month move, chart breadth and news. A research ranking: tested as an entry filter and rejected, so it changes no trade.")}</div>
    <div class="hbars">${th.map(x => `<div class="hbar" style="cursor:default"><span class="nm">${esc(x.name)}</span><span class="track"><i style="width:${Math.min(100, x.heat || 0).toFixed(0)}%;background:${(x.heat || 0) >= 60 ? "var(--buy)" : "var(--watch)"}"></i></span><b>${num(x.heat)}</b></div>`).join("")}</div>
  </div>`;
}
function universeMap(rows) {
  const alerted = new Set((D.actionable || []).map(a => a.sym));
  const col = { CONFIRMED: "--buy", EXTENDED: "--watch", ANTICIPATION: "--info", WATCH: "--surface-3", BROKEN: "--risk" };
  const sorted = rows.slice().sort((a, b) => (b.rs || 0) - (a.rs || 0));
  return `<div class="card"><div class="card-head"><h3>Universe map</h3><span class="hint">Each square is a stock, strongest relative strength first; colour is the chart stage; a ring marks a buy alert in the last 7 days.</span></div>
    <div class="umap" id="umap">${sorted.map(r => `<i data-sym="${esc(r.sym)}" class="${alerted.has(r.sym) ? "alerted" : ""}" style="background:var(${col[r.tag] || "--surface-3"})" data-tip="${esc(r.sym + " · " + stageWord(r.tag) + " · RS " + (isNum(r.rs) ? r.rs.toFixed(0) : "—") + (r.company ? " · " + r.company : ""))}"></i>`).join("")}</div>
    <div class="legend" style="margin-top:12px">${Object.entries(col).map(([k, c]) => `<span><i style="background:var(${c})"></i>${esc(stageWord(k))}</span>`).join("")}</div></div>`;
}
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
const SORT_LABEL = { setup: "setup first", score: "conviction", rs: "RS", close: "price", tag: "stage", dist: "distance to alert", tier: "size", ind: "industry", roce: "ROCE", pe: "P/E", pgttm: "profit growth", sym: "symbol", chg: "day move" };
function activeFilters() {
  const f = S.screener, out = [];
  if (f.view !== "all") out.push({ k: "view", l: (VIEWS.find(v => v[0] === f.view) || [0, f.view])[1] });
  if (f.ind) out.push({ k: "ind", l: f.ind });
  if (f.tier) out.push({ k: "tier", l: f.tier + " cap" });
  if (f.hideVeto) out.push({ k: "veto", l: "No vetoed" });
  return out;
}
function filterPanel() {
  const f = S.screener, inds = [...new Set(ROWS.map(r => r.ind).filter(Boolean))].sort();
  const cnt = {};
  VIEWS.forEach(([k]) => { cnt[k] = k === "all" ? ROWS.length : k === "setup" ? ROWS.filter(r => ["VALIDATED", "AWAITING TRIGGER", "VALIDATED (EXTENDED)"].includes(r.trig)).length : ROWS.filter(r => r.tag === k).length; });
  return `<div class="card fpanel">
    <div class="fp-row"><span class="fp-k">Stage</span><div class="chipset">${VIEWS.map(([k, l]) => `<button class="chip ${f.view === k ? "on" : ""}" data-sview="${k}">${esc(l)} <span class="faint">${cnt[k]}</span></button>`).join("")}</div></div>
    <div class="fp-two">
      <div class="fp-row"><label class="fp-k" for="sind">Industry</label><select class="field" id="sind"><option value="">All industries</option>${inds.map(i => `<option ${f.ind === i ? "selected" : ""}>${esc(i)}</option>`).join("")}</select></div>
      <div class="fp-row"><label class="fp-k" for="stier">Size</label><select class="field" id="stier"><option value="">All sizes</option>${["Micro", "Small", "Mid", "Large"].map(t => `<option value="${t}" ${f.tier === t ? "selected" : ""}>${t} cap</option>`).join("")}</select></div>
    </div>
    <label class="fp-check"><input type="checkbox" id="sveto" ${f.hideVeto ? "checked" : ""}>Hide vetoed stocks</label>
    <div class="fp-actions"><button class="btn sm" id="sreset">Clear all</button><button class="btn sm primary" id="sdone">Done</button></div></div>`;
}
function screenStocks() {
  const f = S.screener, rows = screenerRows(), nf = activeFilters();
  S.ctx = rows.map(r => r.sym);
  const shown = rows.slice(0, f.limit);
  const th = (k, l, extra = "", tip = "") => `<th class="sortable ${extra}" data-sort="${k}"${tip ? ` data-tip="${esc(tip)}"` : ""}>${l}${f.sort === k ? `<span class="arrow">${f.dir > 0 ? "▲" : "▼"}</span>` : ""}</th>`;
  return `<div class="sc-tools">
      <div class="searchbox">${I.search}<input class="field" id="sq" placeholder="Symbol or company" value="${esc(f.q)}" autocomplete="off" spellcheck="false" aria-label="Search the screener"></div>
      <button class="btn ${f.open ? "on" : ""}" id="sfilter" aria-expanded="${!!f.open}">${I.filter}Filter${nf.length ? `<span class="count-badge">${nf.length}</span>` : ""}</button></div>
    ${f.open ? filterPanel() : ""}
    ${nf.length ? `<div class="fchips">${nf.map(x => `<button class="chip" data-unfilter="${x.k}" aria-label="Remove filter ${esc(x.l)}">${esc(x.l)} ✕</button>`).join("")}</div>` : ""}
    <div class="meta-line"><span><b>${num(rows.length)}</b> stocks · sorted by ${esc(SORT_LABEL[f.sort] || f.sort)}</span><span class="swipe-hint">Swipe for more →</span></div>
    <div class="card flush"><div class="table-wrap max"><table class="t freeze2" id="stbl">
    <thead><tr>${th("sym", "Stock", "c1")}${th("score", "Conviction", "c2", "Conviction (0–100): the eight-question check. Under 50 and vetoed names have lagged the market; above 50 it does not rank.")}${th("close", "Price", "r")}${th("rs", "RS", "r", "Relative strength: 6- and 12-month return ranked against the whole universe (100 = strongest).")}
      ${th("tag", "Stage")}${th("setup", "Setup", "", "Fired breakout, then live base, then none. The base is where the forward record shows the edge.")}${th("dist", "To alert", "r", "How far below its alert price a base-ready stock sits.")}<th>120 days</th>
      ${th("tier", "Size", "", "Market cap at tonight's price: Large over ₹50,000 Cr, Mid over ₹12,000 Cr, Small over ₹2,000 Cr, Micro below.")}${th("ind", "Industry")}${th("roce", "ROCE", "r")}${th("pe", "P/E", "r", "Price over the last 12 months' earnings, at tonight's price.")}${th("pgttm", "Profit growth", "r", "Profit over the last 12 months against the 12 before.")}</tr></thead>
    <tbody>${shown.map(r => { const s = setupBy[r.sym], q = quoteOf(r.sym); return `<tr data-sym="${esc(r.sym)}" data-ctx="screener" class="${r.veto ? "dim" : ""}">
      <td class="c1"><div class="cell-sym"><span class="sym">${esc(r.sym)}</span><span class="co">${esc(coName(r.sym) || nameOf(r.sym) || r.ind || "")}</span></div></td>
      <td class="c2">${convCell(r.score, r.veto)}</td>
      <td class="r num">${px(q.price)}${isNum(q.chg) ? `<div class="chg ${cls(q.chg)}">${movePct(q.chg)}</div>` : ""}</td>
      <td class="r">${rsCell(r.rs)}</td><td>${stageChip(r.tag)}</td><td>${setupChip(r.trig)}</td>
      <td class="r num">${s && isNum(s.dist) ? (s.dist >= 0 ? pct(s.dist) : "above") : "—"}</td>
      <td>${spark(closesOf(r.sym), 84, 22)}</td>
      <td class="muted">${esc(r.tier || "")}</td><td class="muted ind">${esc(r.ind || "")}</td>
      <td class="r num">${isNum(r.roce) ? r.roce.toFixed(0) + "%" : "—"}</td><td class="r num">${isNum(r.pe) ? r.pe.toFixed(1) : "—"}</td>
      <td class="r num ${cls(r.pgttm)}">${isNum(r.pgttm) ? pct(r.pgttm, 0) : "—"}</td></tr>`; }).join("")}</tbody></table></div>
    ${rows.length > shown.length ? `<div style="padding:12px 16px"><button class="btn" id="smore">Show ${Math.min(200, rows.length - shown.length)} more of ${rows.length - shown.length}</button></div>` : ""}</div>`;
}
function screenMultibaggers() {
  const f = S.mb, q = f.q.trim().toLowerCase();
  let rows = mbTop(100000).filter(m => !q || m.sym.toLowerCase().includes(q) || nameOf(m.sym).toLowerCase().includes(q));
  const val = m => f.sort === "conv" ? (rowBy[m.sym] || {}).score : f.sort === "ai" ? +((MRS[m.sym] || {}).conviction) : f.sort === "n" ? (m.factors || []).length : m.score;
  rows.sort((a, b) => { const x = val(a), y = val(b); if (!isNum(x) && !isNum(y)) return 0; if (!isNum(x)) return 1; if (!isNum(y)) return -1; return f.dir * (x - y); });
  S.ctx = rows.map(m => m.sym);
  const shown = rows.slice(0, f.limit);
  const th = (k, l, extra = "", tip = "") => `<th class="sortable ${extra}" data-mbsort="${k}"${tip ? ` data-tip="${esc(tip)}"` : ""}>${l}${f.sort === k ? `<span class="arrow">${f.dir > 0 ? "▲" : "▼"}</span>` : ""}</th>`;
  if (!rows.length && !q) return `<div class="empty">The multibagger score was not computed on this build.</div>`;
  return `<div class="page-intro">The whole liquid market ranked by the proven multibagger ingredients present at once. Research ideas, not buy signals: even the best signal is followed by a triple about 1 time in 10. ${info(mbExplain(null) + " The top 10% by this score made 27% a year over 2016–2026 as a 10-stock portfolio, against 17% for momentum alone.")}</div>
    <div class="sc-tools"><div class="searchbox">${I.search}<input class="field" id="mq" placeholder="Symbol or company" value="${esc(f.q)}" autocomplete="off" spellcheck="false" aria-label="Search multibaggers"></div></div>
    <div class="meta-line"><span><b>${num(rows.length)}</b> stocks · scored ${esc(dateLabel(MBX.asof))}</span><span class="swipe-hint">Swipe for more →</span></div>
    <div class="card flush"><div class="table-wrap max"><table class="t freeze2">
    <thead><tr><th class="c1">Stock</th>${th("score", "Multibagger", "c2", "Points for the proven ingredients present; all nine make 100. Open a stock's Scores tab for its sum.")}${th("conv", "Conviction", "r", "The eight-question check. Only stocks in the nightly scan have one.")}<th class="r">Price</th>${th("ai", "AI rating", "r", "The weekly AI deep-dive's 1–5 view, where one exists.")}${th("n", "Ingredients", "", "Which of the proven ingredients it has today.")}</tr></thead>
    <tbody>${shown.map(m => { const r = rowBy[m.sym] || {}, q2 = quoteOf(m.sym), mr = MRS[m.sym]; return `<tr data-sym="${esc(m.sym)}" data-ctx="mb">
      <td class="c1"><div class="cell-sym"><span class="sym">${esc(m.sym)}</span><span class="co">${esc(shortCo(nameOf(m.sym)) || "outside the scan")}</span></div></td>
      <td class="c2">${cbar(m.score, "var(--teal)")}</td>
      <td class="r">${isNum(r.score) ? convCell(r.score, r.veto) : `<span class="faint" style="font-size:12px" data-tip="Outside the nightly scan, so it has no conviction check yet.">not scanned</span>`}</td>
      <td class="r num">${isNum(q2.price) ? px(q2.price) : "—"}${isNum(q2.chg) ? `<div class="chg ${cls(q2.chg)}">${movePct(q2.chg)}</div>` : ""}</td>
      <td class="r num">${mr && isNum(+mr.conviction) ? `<span style="color:${convCol(+mr.conviction)}">${esc(mr.conviction)}/5</span>` : `<span class="faint">—</span>`}</td>
      <td class="ingr-cell">${pennyRow(m.sym) && !pennyRow(m.sym).veto ? `<span class="chip sm ghost" data-tip="${pennyRow(m.sym).asd === false ? "Also on the Penny list, not checked yet." : "Also on the Penny list: a very small company that passed the safety checks."}">penny</span> ` : ""}${(m.factors || []).map(n => `<span class="chip sm ghost" data-tip="${esc((m.evidence || {})[n] || "")}">${esc(fShort(n))}</span>`).join(" ")}</td></tr>`; }).join("")}</tbody></table></div>
    ${rows.length > shown.length ? `<div style="padding:12px 16px"><button class="btn" id="mbmore">Show ${Math.min(200, rows.length - shown.length)} more of ${rows.length - shown.length}</button></div>` : ""}</div>`;
}
/* The Penny tab is a LIST, not a score (user, 2026-10-14: "multibagger and
   penny scores, it's confusing"). The penny screen decides who is safe enough
   to trade; the multibagger score, the app's one long-term score, ranks them.
   Three tiers, never mixed: checked and passed, not checked (fundamentals
   unreadable, so no veto could run: these had floated to the top), failed. */
const PENNY_TIER = r => r.veto ? 2 : r.asd === false ? 1 : 0;
function pennyFlag(x) { const s = typeof x === "string" ? x : (x.code || ""); return s.split(" — ")[0].replace(/\bRs ?(\d)/g, "₹$1").replace(/\bpts\b/g, "points"); }
function pennySafety(r) {
  if (r.veto) return `<span class="chip sm risk" data-tip="${esc(String(r.vetowhy || "").replace(/\bRs ?(\d)/g, "₹$1"))}">failed</span>`;
  if (r.asd === false) return `<span class="chip sm watch" data-tip="screener.in had no readable company data for it, so the pledge, dilution and shell checks could not run. It is listed below every checked name.">not checked</span>`;
  return `<span class="chip sm buy">passed</span>${(r.flags || []).slice(0, 2).map(x => ` <span class="chip sm ghost" data-tip="${esc(pennyFlag(x))}">${esc(clip(pennyFlag(x), 30))}</span>`).join("")}`;
}
function explorePenny() {
  const P = lazy("penny") || D.penny;
  if (!P) return `<div class="empty">The penny screen has not run.</div>`;
  const f = S.penny, q = f.q.trim().toLowerCase();
  const mbOf = r => MBS[r.sym] ? MBS[r.sym].score : -1;
  const all = P.rows || [];
  let rows = all.filter(r => (!q || r.sym.toLowerCase().includes(q) || (r.company || "").toLowerCase().includes(q)) && (f.showVeto || !r.veto) && (!f.arm || (r.arm || "").includes(f.arm)));
  rows.sort((a, b) => PENNY_TIER(a) - PENNY_TIER(b) || mbOf(b) - mbOf(a) || (b.turn || 0) - (a.turn || 0));
  S.ctx = rows.map(r => r.sym);
  const nPass = all.filter(r => PENNY_TIER(r) === 0).length, nUnchecked = all.filter(r => PENNY_TIER(r) === 1).length;
  return `<div class="page-intro">Very small companies, under ₹100 a share or under ₹1,000 Cr, that are safe enough to trade: you can sell them, they are not under exchange surveillance, and their shares are not heavily pledged or diluted. They are ranked by the same multibagger score as the Multibaggers list. Keep penny stocks to 5% of your portfolio and 1% in any one name. ${info("The penny screen decides who is safe; it removes stocks you could not sell and checks pledges, dilution and shells. The ranking is the multibagger score, the app's one long-term score. The penny screen's own score is still recorded every run for a forward test, but it has no track record yet, so it is not shown.")}</div>
    <div class="sc-tools"><div class="searchbox">${I.search}<input class="field" id="pq" placeholder="Symbol or company" value="${esc(f.q)}" autocomplete="off" spellcheck="false" aria-label="Search penny stocks"></div></div>
    <div class="toolbar"><div class="seg">${[["", "Both"], ["price", "Under ₹100"], ["mcap", "Under ₹1,000 Cr"]].map(([k, l]) => `<button data-parm="${k}" class="${f.arm === k ? "on" : ""}">${l}</button>`).join("")}</div>
      <label class="muted" style="font-size:12.5px;display:flex;gap:6px;align-items:center"><input type="checkbox" id="pveto" ${f.showVeto ? "checked" : ""}>Show the ones that failed</label></div>
    <div class="meta-line"><span><b>${num(nPass)}</b> passed the safety checks${nUnchecked ? ` · ${num(nUnchecked)} not checked yet` : ""} · as of ${esc(dateLabel(P.as_of))}</span><span class="swipe-hint">Swipe for more →</span></div>
    <div class="card flush"><div class="table-wrap max"><table class="t freeze2"><thead><tr><th class="c1">Stock</th><th class="c2" data-tip="The multibagger score: points for the proven ingredients present; all nine make 100.">Multibagger</th><th>Safety</th><th class="r">Price</th><th class="r" data-tip="Median daily traded value.">Traded a day</th><th class="r" data-tip="10% of the median daily value: roughly what you could sell in one session without moving the price.">Most you could sell a day</th><th class="r">3 months</th><th class="r">Market cap</th><th>Stage</th><th class="r">RS</th></tr></thead>
      <tbody>${rows.map(r => `<tr class="${r.veto ? "dim" : ""}" data-sym="${esc(r.sym)}" data-ctx="penny"><td class="c1"><div class="cell-sym"><span class="sym">${esc(r.sym)}</span><span class="co">${esc(shortCo(r.company))}</span></div></td>
        <td class="c2">${MBS[r.sym] ? cbar(MBS[r.sym].score, "var(--teal)") : `<span class="faint" style="font-size:12px" data-tip="Too new or too thinly traded for the multibagger score.">not scored</span>`}</td>
        <td>${pennySafety(r)}</td><td class="r num">${px(r.close)}</td>
        <td class="r num">${isNum(r.turn) ? "₹" + r.turn.toFixed(2) + " Cr" : "—"}</td><td class="r num">${isNum(r.turn) ? inrShort(r.turn * 1e7 * 0.1) : "—"}</td><td class="r num ${cls(r.run3m)}">${pct(r.run3m, 0)}</td>
        <td class="r num">${isNum(r.mcap) ? "₹" + nf0.format(r.mcap) + " Cr" : "—"}</td><td>${stageChip(r.tag)}</td><td class="r num">${isNum(r.rs) ? r.rs.toFixed(0) : "—"}</td></tr>`).join("")}</tbody></table></div></div>
    ${(P.funnel || []).length ? `<details class="more" style="margin-top:14px"><summary>Why the rest of the market is not here</summary><div class="card">${P.funnel.map(x => `<div class="lrow" style="cursor:default"><span>${esc(x.why)}</span><span class="num">${num(x.n)}</span></div>`).join("")}</div></details>` : ""}`;
}
function momentumSection() {
  const pv = MC.preview || {}, nav = MC.nav || [], cmp = MC.compare || {}, book = MC.book || {};
  const targets = pv.targets || [];
  const when = nextRebalanceLabel().replace("the first session of ", "1 ");
  const head = nav.length ? `<div class="kpis" style="margin-bottom:14px">
      <div class="kpi"><div class="label">Since ${esc(dateLabel(nav[0][0]))}</div><div class="value ${cls(cmp.sleeve)}">${pct(cmp.sleeve)}</div><div class="note">NAV ${inrShort(nav[nav.length - 1][1])} on ₹10L</div></div>
      <div class="kpi"><div class="label">MIDSMALL ETF</div><div class="value sm ${cls(cmp.midsmall)}">${pct(cmp.midsmall)}</div><div class="note">same dates: the bar it is judged by</div></div>
      <div class="kpi"><div class="label">Invested</div><div class="value sm">${Math.round(((MC_LAST || {}).exposure || 1) * 100)}%</div><div class="note">${coreHeld.size} names</div></div>
      <div class="kpi"><div class="label">Next rebalance</div><div class="value text">${esc(when)}</div><div class="note">${(pv.adds || []).length} adds and ${(pv.drops || []).length} drops if it were tonight</div></div></div>`
    : `<div class="callout info" style="margin-bottom:14px">First rebalance at the open on <b>${esc(when)}</b>. If the month ended tonight, it would buy these ${targets.length} names, ${Math.round((pv.exposure || 1) * 100)}% invested.</div>`;
  const tbl = `<div class="card flush"><div class="card-head"><h3>${nav.length ? "Next rebalance, if the month ended tonight" : "What the rules would buy tonight"}</h3>
      <span class="hint">as of ${esc(pv.asof || "")}</span></div>
    <div class="table-wrap"><table class="t"><thead><tr><th class="r">Rank</th><th>Stock</th><th class="r">6 months</th><th class="r">12 months</th><th class="">120 days</th><th class="r" data-tip="Annualised volatility of daily returns. The score divides by it, so steady strength outranks wild swings.">Volatility</th><th class="r">Price</th><th>Status</th></tr></thead>
    <tbody>${targets.map(t => `<tr data-sym="${esc(t.sym)}" data-ctx="core"><td class="r num">${num(t.rank)}</td>
      <td><div class="cell-sym"><span class="sym">${esc(t.sym)}</span><span class="co">${esc((rowBy[t.sym] || {}).company || "")}</span></div></td>
      <td class="r num ${cls(t.r6)}">${pct(t.r6, 0)}</td><td class="r num ${cls(t.r12)}">${pct(t.r12, 0)}</td>
      <td class="">${closesOf(t.sym).length ? spark(closesOf(t.sym), 80, 22) : `<span class="faint">—</span>`}</td><td class="r num">${num(t.vol)}%</td>
      <td class="r num">${px(t.close)}</td><td>${t.held ? '<span class="chip sm ghost">held</span>' : nav.length ? '<span class="chip sm buy">add</span>' : '<span class="chip sm ghost">new</span>'}</td></tr>`).join("")}
      ${(pv.drops || []).map(s => `<tr data-sym="${esc(s)}"><td class="r faint">—</td><td class="sym">${esc(s)}</td><td colspan="5" class="muted">fell below rank 40</td><td><span class="chip sm risk">drop</span></td></tr>`).join("")}</tbody></table></div></div>`;
  const held = nav.length && (book.rows || []).length ? `<div class="card flush" style="margin-top:16px"><div class="card-head"><h3>Holdings</h3><span class="hint">cash ${inrShort(book.cash)}</span></div><div class="table-wrap"><table class="t"><thead><tr><th>Stock</th><th class="r">Weight</th><th class="r">Since</th><th class="r">Return</th><th class="r">Price</th></tr></thead>
    <tbody>${book.rows.map(r => `<tr data-sym="${esc(r.sym)}" data-ctx="coreheld"><td class="sym">${esc(r.sym)}</td><td class="r num">${num(r.weight, 1)}%</td><td class="r">${esc(dateLabel(r.since))}</td><td class="r num ${cls(r.ret)}">${pct(r.ret)}</td><td class="r num">${px(r.close)}</td></tr>`).join("")}</tbody></table></div></div>` : "";
  return head + (nav.length ? held + `<div style="margin-top:16px">${tbl}</div>` : tbl) +
    howItWorks("The top 20 stocks by volatility-adjusted 6- and 12-month momentum (NSE's momentum-index method), liquid names only, rebalanced on the first session of each month at the open. A holding stays while it ranks in the top 40, and the book is half invested when market breadth is under 50%. It is meant to run as one book with the breakout trades, and it catches the fast V-shaped recoveries a base-breakout system cannot enter.",
      [["2020–2026 backtest", "+43.6% a year", "−23.4% worst drawdown, at 0.25% costs"]]);
}
const SLEEVES = {
  mb: { title: "RS leaders", what: "6- and 12-month return both in the market's top 10%", color: "--buy", slots: 5,
        info: "RS leaders from the whole liquid NSE market: the 6- and 12-month returns both in the top 10%. 5 slots, bought at the next open; sold on a close 20% below entry or, after 20 sessions, a close under the 30-week average; everything goes to cash while fewer than half of stocks are above their 200-day average. Chosen on 2006–2015 alone and registered with its weaker 2016–2026 result, because choosing with hindsight is what the process forbids.",
        pre: [["2006–2015 (chosen here)", "+29.9% a year", "−31.9% worst drawdown"], ["2016–2026 (run once)", "+18.2% a year", "−50.9% worst drawdown"]] },
  vb: { title: "Value breakout", what: "Cheap on cash flow and book value, starting a new uptrend", color: "--ep", slots: 10,
        info: "Companies in the market's cheapest 30% on both free-cash-flow yield and book value (cash flow positive), bought when they break out of a 2-year base or start a new stage-2 uptrend. 10 slots, with the same exits and breadth rule as the RS-leaders book. Fundamentals only reach back to 2016, so this is the least-proven of the forward tests.",
        pre: [["2016–2020 (chosen here)", "+6.6% a year", "−45.3% worst drawdown; the market made 4.7%"], ["2021–2026 (run once)", "+31.1% a year", "−30.8% worst drawdown; the market made 22.1%"]] },
  pm: { title: "Promoter buying", what: "A promoter bought in the last 60 sessions, and the stock is a price leader", color: "--teal", slots: 5,
        info: "A promoter or promoter-group entity bought the company's shares in the open market (at least ₹10 lakh, as disclosed to NSE) within the last 60 sessions, and the stock is already a price leader (RS leader or trend template). 5 slots, bought at the next open; sold on a close 20% below entry or, after 20 sessions, 3×ATR below the highest close since entry; everything goes to cash while fewer than half of stocks are above their 200-day average.",
        pre: [["2016–2020 (chosen here)", "+51.5% a year", "−26.3% worst drawdown; the market made 4.7%"], ["2021–2026 (run once)", "+23.5% a year", "−43.4% worst drawdown; the market made 22.1%, momentum alone 14.3%"]] },
};
function sleeveSection(Sx, o) {
  if (!Sx || !Sx.registered) return "";
  const nav = Sx.nav || [], hold = Sx.holdings || [];
  const regimeTxt = Sx.breadth_exit === false ? "no regime exit" : Sx.risk_on === false ? "regime off: in cash" : "regime on";
  const head = nav.length ? `<div class="kpis" style="margin-bottom:14px">
      <div class="kpi"><div class="label">Since ${esc(dateLabel(nav[0][0]))}</div><div class="value ${cls(Sx.since_pct)}">${pct(Sx.since_pct)}</div><div class="note">NAV ${inrShort(nav[nav.length - 1][1])} on ₹10L</div></div>
      <div class="kpi"><div class="label">MIDSMALL ETF</div><div class="value sm ${cls(Sx.midsmall_pct)}">${pct(Sx.midsmall_pct)}</div><div class="note">same dates: the bar it is judged by</div></div>
      <div class="kpi"><div class="label">Holdings</div><div class="value sm">${hold.length} / ${o.slots}</div><div class="note">cash ${inrShort(Sx.cash)} · ${esc(regimeTxt)}</div></div></div>`
    : `<div class="callout info" style="margin-bottom:14px">Starts on the first session after <b>${esc(dateLabel(Sx.registered))}</b> and buys at the next open after a signal close${(Sx.pending_buys || []).length ? `, starting with <b>${esc(Sx.pending_buys.join(", "))}</b>` : ""}.</div>`;
  const feed = Sx.insider_asof ? `<div class="muted" style="font-size:12px;margin:-4px 0 12px">Promoter disclosures up to <b>${esc(dateLabel(Sx.insider_asof))}</b>. If this date stops moving, NSE's feed is blocked.</div>` : "";
  const tbl = hold.length ? `<div class="card flush"><div class="card-head"><h3>Holdings</h3><span class="hint">${(Sx.pending_sells || []).length ? "selling at the next open: " + esc(Sx.pending_sells.join(", ")) : ""}</span></div><div class="table-wrap"><table class="t"><thead><tr><th>Stock</th><th class="r">Since</th><th class="r">Entry</th><th class="r">Last</th><th class="r">Return</th><th class="">120 days</th></tr></thead>
    <tbody>${hold.map(h => `<tr ${rowBy[h.sym] ? `data-sym="${esc(h.sym)}"` : `style="cursor:default"`}><td class="sym">${esc(h.sym)}</td><td class="r">${esc(dateLabel(h.since))}</td><td class="r num">${px(h.entry)}</td><td class="r num">${px(h.last)}</td><td class="r num ${cls(h.ret_pct)}">${pct(h.ret_pct)}</td><td class="">${closesOf(h.sym).length ? spark(closesOf(h.sym), 80, 22) : `<span class="faint">—</span>`}</td></tr>`).join("")}</tbody></table></div></div>`
    : nav.length ? `<div class="empty">${(Sx.pending_buys || []).length ? "Buying at the next open: <b>" + esc(Sx.pending_buys.join(", ")) + "</b>." : "In cash: nothing qualifies right now."}</div>` : "";
  return head + feed + tbl + howItWorks(o.info, o.pre);
}
/* The paper books as ONE table: what each buys, whether it has started, and
   how it is doing against the MIDSMALL ETF. The backtests that chose each
   book's rules sit behind "How it works" — they are the hypothesis, not the
   result, and six sets of them on one screen read as noise (user, 2026-09-28). */
function books() {
  const P = D.paper || {}, paper = POS.paper || [];
  const dates = [...(P.ledger || []).map(l => String(l.d || "")), ...paper.map(p => String(p.entered || ""))].filter(Boolean).sort();
  const mcNav = MC.nav || [], cmp = MC.compare || {};
  const out = [
    { id: "breakout", name: "Breakout book", what: "Every stock the AI check said to buy, run by the two-lot plan", color: "--info",
      started: dates[0] || null, ret: P.net_pct, mid: null, nav: [], held: paper.length, slots: null },
    { id: "core", name: "Momentum core", what: "Top 20 by 6- and 12-month momentum, rebalanced monthly", color: "--ai",
      started: mcNav.length ? mcNav[0][0] : (((MC.rebalances || [])[0] || {}).fill || null), startsLabel: nextRebalanceLabel().replace("the first session of ", "1 "),
      ret: mcNav.length ? cmp.sleeve : null, mid: mcNav.length ? cmp.midsmall : null, nav: mcNav, held: coreHeld.size, slots: 20 },
  ];
  [["mb", MB], ["vb", VB], ["pm", PM]].forEach(([id, Sx]) => {
    const o = SLEEVES[id];
    if (!Sx || !Sx.registered) return;
    const nav = Sx.nav || [];
    out.push({ id, name: o.title, what: o.what, color: o.color, started: nav.length ? nav[0][0] : null,
      startsLabel: "after " + dateLabel(Sx.registered), ret: Sx.since_pct, mid: Sx.midsmall_pct, nav,
      held: (Sx.holdings || []).length, slots: o.slots, sleeve: Sx, o });
  });
  return out;
}
function drawBooks(list) {
  const box = $("#bookchart");
  if (!box || !window.LightweightCharts) return;
  const ch = makeChart(box, { bucket: _pageCharts });
  const leg = [];
  list.forEach(b => {
    const base = b.nav[0][1] || 1;
    const s = ch.addLineSeries({ color: css(b.color), lineWidth: 2, priceLineVisible: false, lastValueVisible: false });
    s.setData(b.nav.map(p => ({ time: p[0], value: p[1] / base * 100 })));
    leg.push(`<span><i style="background:${css(b.color)}"></i>${esc(b.name)}</span>`);
  });
  ch.timeScale().fitContent();
  const l = document.createElement("div"); l.className = "chart-legend"; l.innerHTML = leg.join(""); box.appendChild(l);
}
function bookDetail(b) {
  if (!b) return "";
  if (b.id === "breakout") return breakoutDetail();
  if (b.id === "core") return momentumSection();
  return sleeveSection(b.sleeve, b.o);
}
function breakoutDetail() {
  const paper = POS.paper || [], P = D.paper || {}, led = P.ledger || [];
  return `<div class="kpis" style="margin-bottom:14px">
      <div class="kpi"><div class="label">Net result</div><div class="value ${cls(P.net)}">${inrShort(P.net)}</div><div class="note">${pct(P.net_pct, 1)} of the ₹10L book</div></div>
      <div class="kpi"><div class="label">Realised</div><div class="value sm ${cls(P.realized)}">${inrShort(P.realized)}</div><div class="note">${num(P.n_closed)} positions closed</div></div>
      <div class="kpi"><div class="label">Open, marked to market</div><div class="value sm ${cls(P.unrealized)}">${inrShort(P.unrealized)}</div><div class="note">${paper.length} positions open</div></div>
      <div class="kpi"><div class="label">Waiting to fill</div><div class="value sm">${(P.pending || []).length}</div><div class="note">${(P.pending || []).map(p => esc(p.sym)).join(", ") || "none"}</div></div>
    </div>
    ${paper.length ? positionsTable(paper) : `<div class="empty">The breakout book has no open positions.</div>`}
    ${led.length ? `<details class="more" style="margin-top:14px"><summary>Recent fills (${led.length})</summary><div class="card flush" style="margin-top:8px"><div class="table-wrap"><table class="t"><thead><tr><th>Date</th><th>Stock</th><th>Action</th><th class="r">Shares</th><th class="r">Price</th><th class="r">P&amp;L</th><th class="">Reason</th></tr></thead>
    <tbody>${led.map(l => `<tr data-sym="${esc(l.sym)}"><td class="num">${esc(l.d)}</td><td class="sym">${esc(l.sym)}</td><td>${l.action === "BUY" ? '<span class="chip sm buy">Buy</span>' : l.action === "SELL" ? '<span class="chip sm">Sell ' + esc(l.lot) + "</span>" : '<span class="chip sm ghost">' + esc(l.action) + "</span>"}</td>
      <td class="r num">${esc(l.shares)}</td><td class="r num">${isNum(+l.price) && l.price !== "" ? px(+l.price) : "—"}</td><td class="r num ${cls(+l.pnl)}">${l.pnl !== "" && isNum(+l.pnl) ? inr(+l.pnl) : ""}</td><td class=" muted" style="max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(l.reason)}</td></tr>`).join("")}</tbody></table></div></div></details>` : ""}
    ${howItWorks("Every AI-analyst BUY verdict is entered at the next session's open, sized by the mechanical plan, and managed by the two-lot rules: a third of the trading half is sold at +2.5R, both halves move to breakeven at +1.5R, the trading half trails the 50-day average, and the core half leaves only on a weekly close under the 30-week average. It is the running test of whether the analyst layer adds money.", [])}`;
}
function positionsTable(list) {
  return `<div class="card flush"><div class="table-wrap"><table class="t"><thead><tr><th>Stock</th><th class="r">Entry</th><th class="r">Last</th><th class="r">Result</th><th class="">60 days</th><th class="r">Shares</th><th>Next rules</th></tr></thead>
    <tbody>${list.map(p => `<tr data-sym="${esc(p.sym)}" data-ctx="positions">
      <td><div class="cell-sym"><span class="sym">${esc(p.sym)}</span><span class="co">since ${esc(dateLabel(p.entered))}${p.verdict ? " · " + esc(p.verdict) : ""}</span></div></td>
      <td class="r num">${px(p.entry)}</td><td class="r num">${px(p.last)}</td>
      <td class="r num ${cls(p.r_now)}">${rr(p.r_now)}<div class="muted" style="font-size:11.5px">${pct(p.pnl_pct)} · ${inrShort(p.pnl)}</div></td>
      <td class="">${spark(closesOf(p.sym).slice(-60), 80, 22)}</td>
      <td class="r num">${num(p.shares)}</td>
      <td style="min-width:260px">${p.urgent && p.urgent.length ? `<div class="warn" style="font-size:12.5px;font-weight:600">⚠ ${esc(p.urgent.join(" · "))}</div>` : ""}
        ${(p.rules || []).map(r => `<div style="font-size:12px;display:flex;gap:8px;justify-content:space-between"><span class="muted">${esc(r.label)}</span><span class="num">${px(r.px)} <span class="faint">${isNum(r.gap) ? pct(r.gap) : ""}</span></span></div>`).join("")}</td></tr>`).join("")}</tbody></table></div></div>`;
}
function researchAnalyst() {
  const items = D.verdict_items || [];
  if (!items.length) return `<div class="empty">No analyst verdicts in the last 10 days.</div>`;
  const es = X.event_study || {};
  return `<div class="callout" style="margin-bottom:14px">Each night an AI analyst checks the top buy alerts and answers <b>buy, wait or skip</b>. Treat it as research, not a filter. ${info("It can only be more cautious than the machine, never less. Its forward record so far: Buy checks ran slightly ahead of Wait checks, and Skips did not underperform.")}</div>
    <div class="grid grid-2">${items.map(v => `<div class="vcard" data-sym="${esc(v.sym)}" style="cursor:pointer">
      <div class="top"><span class="sym" style="font-size:15px">${esc(v.sym)}</span>${verdictChip(v)}${sizeChip(v.size)}<span class="muted" style="margin-left:auto;font-size:12px">${esc(dateLabel(v.stamp))}</span></div>
      <div class="why">${esc(clip(plainAI(v.why), 220))}</div>
      ${(v.whys && v.whys.length) || (v.risks && v.risks.length) || String(v.why || "").length > 220 ? `<details><summary>Full reasoning, evidence and risks</summary><div class="memo">${String(v.why || "").length > 220 ? `<p>${esc(plainAI(v.why))}</p>` : ""}
        ${v.whys && v.whys.length ? `<h4>Why</h4><ul>${v.whys.map(w => `<li>${esc(plainAI(w))}</li>`).join("")}</ul>` : ""}
        ${v.risks && v.risks.length ? `<h4>Risks</h4><ul>${v.risks.map(w => `<li>${esc(plainAI(w))}</li>`).join("")}</ul>` : ""}
        ${v.flip ? `<h4>What would change the view</h4><p>${esc(plainAI(v.flip))}</p>` : ""}</div></details>` : ""}
    </div>`).join("")}</div>`;
}
function researchCommittee() {
  const P = D.ai_picks || {};
  const picks = P.picks || [];
  if (!picks.length) return `<div class="empty">No committee picks yet.</div>`;
  const age = P.age_days;
  return `${age != null && age > 8 ? `<div class="callout watch" style="margin-bottom:12px"><b>Not this week's read:</b> the committee last ran ${age} days ago.</div>` : ""}
    <div style="margin-bottom:14px">${fold("The committee's view of the five", "weekly · " + dateLabel(P.generated), `<div class="memo">${esc(P.portfolio_view || "")}</div>`)}</div>
    <div class="grid grid-2">${picks.map(p => { const m = p.meta || {}, pl = m.plan || {}; return `<div class="vcard">
      <div class="top"><button class="btn link sym" data-sym="${esc(p.symbol)}" style="font-size:16px;color:var(--text)">${esc(p.symbol)}</button>
        <span class="chip sm ai">Weekly pick${p.conviction ? " · " + esc(String(p.conviction).toLowerCase()) + " confidence" : ""}</span><span class="chip sm ghost">${esc(m.sector || "")}</span>
        ${stageChip((rowBy[p.symbol] || {}).tag)} ${setupChip((rowBy[p.symbol] || {}).trig)}</div>
      <div class="muted" style="font-size:12.5px;margin-top:4px">${esc(m.company || "")}</div>
      <div class="why">${esc(clip(plainAI(p.thesis), 220))}</div>
      <details><summary>Full thesis, catalyst, risks, what to watch</summary><div class="memo">${String(p.thesis || "").length > 220 ? `<p>${esc(plainAI(p.thesis))}</p>` : ""}
        ${p.catalyst ? `<h4>Catalyst</h4><p>${esc(p.catalyst)}</p>` : ""}${p.risks ? `<h4>Risks</h4><p>${esc(Array.isArray(p.risks) ? p.risks.join(" ") : p.risks)}</p>` : ""}
        ${p.watch_for ? `<h4>Watch for</h4><p>${esc(p.watch_for)}</p>` : ""}${p.selected_because ? `<h4>Why selected</h4><p>${esc(p.selected_because)}</p>` : ""}
        ${isNum(pl.entry_price) ? `<h4>Mechanical plan</h4><p class="num">entry ${px(pl.entry_price)} · stop ${px(pl.stop_loss_price)} · ${num(pl.shares_total)} shares · risk ${inr(pl.capital_at_risk)}</p>` : ""}</div></details>
    </div>`; }).join("")}</div>`;
}
/* AI prose quotes heat as it was when written ("heat 79.0"); the table beside
   it shows tonight's. The number goes; the words stay. */
function noHeat(t) { return String(t || "").replace(/\s*\(heat \d+(?:\.\d+)?\)/gi, ""); }
function researchThemes() {
  const T = D.themes || {}, th = (T.themes || []).slice().sort((a, b) => (a.thin - b.thin) || (b.heat || 0) - (a.heat || 0));
  const intel = T.intel || {};
  return `<div class="callout" style="margin-bottom:14px">Themes group stocks the way markets trade them (grid capex, defence, EMS…). <b>Heat</b> ranks them by 3-month move, chart breadth and news: context only. ${info("Sector heat was tested as an entry filter and rejected: it cut expectancy from +1.27R to +0.22R.")}</div>
    <div class="card flush"><div class="table-wrap"><table class="t"><thead><tr><th>Theme</th><th class="r">Heat</th><th class="r">3 months</th><th class="r">In uptrend</th><th class="r">Names</th><th>Leaders</th></tr></thead>
    <tbody>${th.map(t => `<tr style="cursor:default"><td><div class="cell-sym"><span class="sym">${esc(t.name)}</span><span class="co" style="max-width:300px">${esc(t.blurb || "")}</span></div></td>
      <td class="r">${t.thin ? `<span class="faint" style="font-size:12px" data-tip="Too few stocks in this theme to rank its heat.">too few</span>` : cbar(t.heat, (t.heat || 0) >= 60 ? "var(--buy)" : "var(--watch)")}</td>
      <td class="r num ${cls(t.ret3m)}">${pct(t.ret3m)}</td><td class="r num">${num(t.breadth)}%</td><td class="r num">${num(t.n)}</td>
      <td>${(t.leaders || []).filter(l => l.tag === "CONFIRMED" || l.tag === "EXTENDED").slice(0, 5).map(l => `<button class="chip sm" data-sym="${esc(l.sym)}">${esc(l.sym)}</button>`).join(" ")}</td></tr>`).join("")}</tbody></table></div></div>
    ${intel.summary ? `<div class="card accent-ai" style="margin-top:16px"><div class="card-head"><h3>This week's thematic research</h3><span class="chip sm ai">AI · weekly</span><span class="hint">${esc(intel.generated || "")}</span></div><div class="memo">${esc(noHeat(intel.summary))}</div>
      ${(intel.themes || []).slice(0, 8).map(x => `<details class="more"><summary><b>${esc(x.name || x.key)}</b> — ${esc(x.direction || "")}${x.strength ? " · strength " + esc(x.strength) : ""}</summary><div class="memo">${esc(x.thesis || x.summary || "")}
        ${(x.calls || x.beneficiaries || []).length ? `<ul>${(x.calls || x.beneficiaries || []).slice(0, 8).map(c => `<li><b>${esc(c.symbol || c.sym || "")}</b> ${esc(c.effect || "")} — ${esc(c.mechanism || c.why || "")}</li>`).join("")}</ul>` : ""}</div></details>`).join("")}</div>` : ""}
    ${(D.heat || []).length ? `<div style="margin-top:16px">${fold("By NSE industry", "average strength of the stocks watched in each", `<div class="hbars">${D.heat.slice(0, 24).map(h => `<div class="hbar" style="cursor:default"><span class="nm">${esc(h.ind)} <span class="faint">· ${num(h.n)}</span></span><span class="track"><i style="width:${Math.min(100, h.rs || 0).toFixed(0)}%;background:${rsCol(h.rs)}"></i></span><b>${num(h.rs)}</b></div>`).join("")}</div>`)}</div>` : ""}
    ${T.read ? `<details class="more" style="margin-top:12px"><summary>The committee's theme read</summary><div class="card"><div class="memo">${esc(noHeat(T.read))}</div></div></details>` : ""}`;
}
function researchNews() {
  const tracked = trackedSyms();
  const risk = [], building = [];
  Object.entries(newsMem).forEach(([sym, m]) => {
    const tag = (rowBy[sym] || {}).tag;
    if (m.n_neg && (tracked.has(sym) || actBy[sym])) risk.push({ sym, m, tag });
    if (m.primed && !["CONFIRMED", "EXTENDED"].includes(tag)) building.push({ sym, m, tag });
  });
  building.sort((a, b) => (b.m.p || 0) - (a.m.p || 0));
  const hits = (D.radar || {}).hits || [];
  return `<div class="callout" style="margin-bottom:14px">News here warns you about risks. It is not a list of things to buy. ${info("Measured on this system's own archive, positive news did not lead the technical trigger: names with a positive filing alerted 7.3% of the time against a 16.6% base rate.")}</div>
    <div class="grid grid-2">
      <div class="card accent-risk"><div class="card-head"><h3>Negative filings on tracked stocks</h3>${info("Tracked: your saved stocks, the watchlist, this week's signals and the 30 highest multibagger scores.")}</div>
        ${risk.length ? risk.slice(0, 20).map(x => `<div class="lrow" data-sym="${esc(x.sym)}"><div><span class="sym">${esc(x.sym)}</span> ${stageChip(x.tag)}<div class="meta">${esc(memWords(x.m.summary))}</div></div><span class="chip sm risk">${x.m.n_neg} negative</span></div>`).join("") : `<div class="muted">No negative filings on tracked stocks.</div>`}</div>
      <div>${fold("Good news building, chart not ready yet", building.length ? building.length + " stocks" : "none", `<div>
        ${building.length ? building.slice(0, 15).map(x => `<div class="lrow" data-sym="${esc(x.sym)}"><div><span class="sym">${esc(x.sym)}</span> ${stageChip(x.tag)}<div class="meta">${esc(memWords(x.m.summary))}</div></div><span class="muted num" style="font-size:12px" data-tip="News pressure: how strongly recent filings lean positive, 0 to 1.">${(x.m.p || 0).toFixed(2)}</span></div>`).join("") : `<div class="muted">Nothing building.</div>`}</div>`)}</div>
    </div>
    <div class="card flush" style="margin-top:16px"><div class="card-head"><h3>Filings since the last scan</h3><span class="hint">${hits.length} classified</span></div><div class="table-wrap"><table class="t"><thead><tr><th></th><th>Stock</th><th>Chart</th><th class="r">RS</th><th>Event</th><th class="">Filing</th></tr></thead>
      <tbody>${hits.map(h => `<tr data-sym="${esc(h.sym)}"><td>${h.cls === "neg" ? '<span class="neg">▼</span>' : h.cls === "pos" ? '<span class="pos">▲</span>' : "·"}</td><td class="sym">${esc(h.sym)}</td><td>${stageChip(h.tag)}</td><td class="r num">${isNum(h.rs) ? h.rs.toFixed(0) : "—"}</td>
        <td>${esc(h.event || "")}${h.confluence ? ' <span class="chip sm buy" data-tip="Positive filing on a stock already in an uptrend.">confluence</span>' : ""}</td><td class=" muted" style="max-width:420px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(cleanHeadline(h.subject || ""))}</td></tr>`).join("")}</tbody></table></div></div>`;
}
function dedupeDeals(list) {
  const by = new Map();
  (list || []).forEach(r => {
    const k = [r.d, r.sym, r.side, r.client, r.qty, r.price].join("|");
    if (by.has(k)) { const o = by.get(k); if (!String(o.kind).includes(r.kind)) o.kind = o.kind + " and " + r.kind; }
    else by.set(k, Object.assign({}, r));
  });
  return [...by.values()];
}
function researchDeals() {
  const rec = dedupeDeals(DEALS.recent || []);
  const intro = `<div class="callout" style="margin-bottom:14px">Bulk and block deals on the names this system watches: who ended the day holding more, or less. Context only. ${info(`Most bulk-deal rows in small caps are trading desks buying and selling the same stock in the same session${isNum(DEALS.churn_pct) ? ` (${DEALS.churn_pct}% of rows so far)` : ""}; those net to nothing and are left out. Archived from ${dateLabel(DEALS.since)}, so the history grows nightly.`)}</div>`;
  if (!rec.length) return intro + `<div class="empty">No named deal of ₹1 crore or more on a watched name in the last 30 days.</div>`;
  return intro + `<div class="card flush"><div class="card-head"><h3>Named deals, last 30 days</h3><span class="hint">₹1 crore and above</span></div><div class="table-wrap max"><table class="t"><thead><tr><th>Date</th><th>Stock</th><th>Side</th><th>Client</th><th class="r">Shares</th><th class="r">Price</th><th class="r">Value</th><th class="">Type</th></tr></thead>
    <tbody>${rec.map(r => `<tr data-sym="${esc(r.sym)}"><td class="num">${esc(dateLabel(r.d))}</td><td class="sym">${esc(r.sym)} ${stageChip((rowBy[r.sym] || {}).tag)}</td>
      <td>${r.side === "BUY" ? '<span class="chip sm buy">Buy</span>' : '<span class="chip sm risk">Sell</span>'}</td><td class="muted" style="max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(r.client)}</td>
      <td class="r num">${num(r.qty)}</td><td class="r num">${px(r.price)}</td><td class="r num">${inrShort(r.value)}</td><td class=" muted">${esc(r.kind)}</td></tr>`).join("")}</tbody></table></div></div>`;
}
function researchPolicy() {
  const M = X.macro || {};
  const themeMeta = Object.fromEntries(((D.themes || {}).themes || []).map(t => [t.key, t]));
  const list = Object.entries(M.themes || {}).map(([k, v]) => ({ key: k, ...v }))
    .sort((a, b) => Math.abs(b.pressure || 0) - Math.abs(a.pressure || 0));
  if (!list.length) return `<div class="empty">No policy event in the last ${num(M.window_days)} days.</div>`;
  return `<div class="callout" style="margin-bottom:14px">Government and regulator decisions that move a whole theme, read from <b>${num(M.headlines_read)}</b> headlines that name no company (${num(M.policy_hits)} qualified in the last ${num(M.window_days)} days). ${info("Bounded on purpose: it can move a stock's catalyst score by at most 0.12 and moves nothing else.")}</div>
    <div class="grid grid-2">${list.map(t => { const meta = themeMeta[t.key] || {}; const names = (meta.leaders || []).filter(l => ["CONFIRMED", "EXTENDED"].includes(l.tag)).slice(0, 8);
      return `<div class="vcard"><div class="top"><span class="sym" style="font-size:15px">${esc(meta.name || t.key)}</span>
      <span class="chip sm ${(t.pressure || 0) >= 0 ? "buy" : "risk"}" data-tip="Decayed policy pressure on this theme (half-life ${num(M.half_life_days)} days).">${(t.pressure || 0) >= 0 ? "+" : ""}${(t.pressure || 0).toFixed(2)}</span></div>
      <div style="margin-top:6px">${(t.top || []).slice(0, 3).map(e => `<div class="news-item" style="grid-template-columns:62px minmax(0,1fr)"><div class="d">${esc(dateLabel(e.date))}</div><div><div class="h"><span class="${e.polarity === "neg" ? "neg" : "pos"}">${e.polarity === "neg" ? "▼" : "▲"}</span> ${e.link && /^https?:/.test(e.link) ? `<a href="${esc(e.link)}" target="_blank" rel="noopener">${esc(e.title)}</a>` : esc(e.title)}</div><div class="src">${esc(e.source || "")}${e.event ? " · " + esc(e.event) : ""}${isNum(e.amount_cr) ? " · ₹" + nf0.format(e.amount_cr) + " Cr" : ""}</div></div></div>`).join("")}</div>
      ${names.length ? `<div class="muted" style="font-size:11.5px;margin-top:8px">In an uptrend in this theme</div><div style="display:flex;gap:4px;flex-wrap:wrap;margin-top:4px">${names.map(l => `<button class="chip sm" data-sym="${esc(l.sym)}">${esc(l.sym)}</button>`).join("")}</div>` : ""}</div>`; }).join("")}</div>`;
}
function gateWord(v) { return ({ ACCRUING: "In progress", PASS: "Passed", PASSED: "Passed", FAIL: "Failed", FAILED: "Failed" })[String(v || "").toUpperCase()] || "In progress"; }
function recordGate() {
  const g = D.gate || {}, c = g.cohort || {}, req = g.required || {}, cond = g.conditions || {}, obs = g.observation || {};
  const bm = g.benchmark || {}, bm2 = g.benchmark2 || {};
  const names = { sample: "Sample size", expectancy: "Expectancy", beats_benchmark: "Beats the ETF", hit_stop: "Stop-out rate", concentration: "Not one lucky trade" };
  return `<div class="callout" style="margin-bottom:14px">The test that decides when real money goes in. 40 live signals must, on average, earn at least half of what the backtest earned at the same age, beat the momentum ETF, and not lean on one lucky trade. Deadline ${esc(g.deadline || "")}.</div>
  <div class="grid grid-main">
    <div class="card"><div class="card-head"><h3>Capital gate</h3><span class="chip sm ${g.verdict === "PASS" ? "buy" : g.verdict === "FAIL" ? "risk" : "info"}">${esc(gateWord(g.verdict))}</span><span class="hint">registered ${esc(g.registered || "")} · deadline ${esc(g.deadline || "")} (${num(g.days_to_deadline)} days)</span></div>
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
    <div class="callout" style="margin-top:14px"><b>Reading it.</b> The setup matters most: live-base and trigger alerts beat the universe, uptrend-only alerts barely do. The research score separates the <b>bottom</b> (under 50, including vetoes, lags the universe) but does not rank the rest, so lists sort by setup first and use the score only to rule names out.</div>
    <details class="more" style="margin-top:14px"><summary>More detail: by research score at the alert</summary>
    <div class="card flush" style="margin-top:8px"><div class="table-wrap"><table class="t"><thead><tr><th>Score band</th><th class="r">Alerts</th><th class="r">10 sessions</th><th class="r">20 sessions</th><th class="r">40 sessions</th></tr></thead>
      <tbody>${(es.by_conv || []).map(esRow).join("")}</tbody></table></div></div></details>
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
  const tbl = keys => `<table class="t"><thead><tr><th>Strategy</th><th class="r">CAGR</th><th class="r">Max drawdown</th><th class="r" data-tip="CAGR divided by the worst drawdown — return per unit of pain.">MAR</th><th class="r">Sharpe</th><th class="r">₹1 became</th></tr></thead>
    <tbody>${keys.map(k => rows.find(r => r.config === k)).filter(Boolean).map(r => `<tr style="cursor:default" class="${/^F[12]|^L[12]/.test(r.config) ? "" : "dim"}"><td>${esc(HR_LABEL[r.config] || r.config)}</td>
      <td class="r num ${cls(r.cagr_pct)}">${pct(r.cagr_pct)}</td><td class="r num neg">${pct(r.max_dd_pct)}</td><td class="r num">${isNum(r.mar) ? r.mar.toFixed(2) : "—"}</td><td class="r num">${isNum(r.sharpe) ? r.sharpe.toFixed(2) : "—"}</td><td class="r num">${isNum(r.total_x) ? "₹" + r.total_x.toFixed(2) : "—"}</td></tr>`).join("")}</tbody></table>`;
  AFTER.push(() => drawCurves());
  return `<div class="callout watch" style="margin-bottom:14px"><b>Read this first.</b> Every figure here uses today's index members, so it carries survivorship bias: simply owning the whole universe returned 33% a year since 2020, while the real, investable Midcap-100 ETF returned 21%. Compare rows with each other, never with a bank deposit.</div>
    <div class="card"><div class="card-head"><h3>Growth of ₹100 since 2020</h3><span class="hint">weekly, log scale</span></div><div class="chart-box" id="curvebox" style="height:340px"></div></div>
    <div class="card flush" style="margin-top:16px"><div class="card-head"><h3>Full history, 2020 → today</h3></div><div class="table-wrap">${tbl(full)}</div></div>
    <details class="more" style="margin-top:12px"><summary>The headline window, 2023-08 → today</summary><div class="card flush" style="margin-top:8px"><div class="table-wrap">${tbl(recent)}</div></div></details>
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
  return `<div class="card flush"><div class="card-head"><h3>Every buy alert the machine fired</h3><span class="hint">${sc.length} signals · append-only</span></div><div class="table-wrap max"><table class="t"><thead><tr><th>When</th><th>Stock</th><th>Type</th><th class="r">Conviction</th><th class="r">Alert ₹</th><th class="r">Return</th><th class="r" data-tip="Plan-followed R: the signal replayed through the backtest engine with a next-open fill and the two-lot exits.">Plan R</th><th class="r">Best R</th><th>Status</th></tr></thead>
    <tbody>${sc.slice(0, 400).map(r => `<tr data-sym="${esc(r.sym)}"><td class="num">${esc(String(r.d).slice(0, 10))}</td><td class="sym">${esc(r.sym)}</td><td class="muted">${esc(sentenceCase((VOC.kindsShort || {})[r.kind] || r.kind))}</td>
      <td class="r num">${isNum(r.conv) ? r.conv.toFixed(0) : "—"}</td><td class="r num">${px(r.entry)}</td><td class="r num ${cls(r.ret)}">${pct(r.ret)}</td>
      <td class="r num ${cls(r.planr)}">${rr(r.planr)}${r.sized === false ? '<span class="faint" data-tip="The live risk engine would not size this (stop wider than 12%); measured against a reference stop.">*</span>' : ""}</td><td class="r num">${rr(r.maxr)}</td><td class="muted">${esc(r.status)}</td></tr>`).join("")}</tbody></table></div></div>`;
}
function pageSystem() {
  const h = D.health || [];
  AFTER.push(() => probeRunPanel());
  return `<div class="page-intro">Every subsystem against its own cadence. A job that records its own failure reads red however recent it is.</div>
    <div class="card flush"><div class="table-wrap"><table class="t"><thead><tr><th></th><th>Subsystem</th><th>Status</th><th class="">What it does</th></tr></thead>
      <tbody>${h.map(x => `<tr style="cursor:default"><td><span class="dot ${esc(x.state)}"></span></td><td><b>${esc(x.label)}</b><div class="muted" style="font-size:12px">${x.age != null ? (x.age < 1 ? "today" : x.age.toFixed(1) + " days ago") : ""}</div></td><td>${esc(x.detail || "")}</td><td class=" muted" style="max-width:520px">${esc(x.tip || "")}</td></tr>`).join("")}</tbody></table></div></div>
    <div class="card" id="runpanel" style="margin-top:16px;display:none"></div>
    <div class="card" style="margin-top:16px"><div class="card-head"><h3>Data on this page</h3></div><div class="memo">
      Built ${esc(D.generated || "")} · prices to ${esc(priceSession())} · last scan ${esc(D.scan_date || "")}.<br>
      ${(D.funnel || []).map(f => `${esc(f[0])}: <b>${num(f[1])}</b> <span class="muted">(${esc(f[2])})</span>`).join(" · ")}<br>
      <a href="dashboard_classic.html">Open the classic dashboard</a> — kept for a transition period.</div></div>`;
}
let _runPoll = null;
async function probeRunPanel() {
  // the run panel exists only on the laptop's own server (dashboard_server.py);
  // on the public site the probe was a 404 in the console on every visit
  if (!/^https?:/.test(location.protocol) || !/^(localhost|127\.0\.0\.1)$/.test(location.hostname)) return;
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
const DIM_LABEL = {
  rs_and_stage: "Trend and strength", earnings_inflection: "Earnings turning up",
  financial_strength_trend: "Balance sheet", catalyst: "News and catalysts",
  smart_money: "Big investors (FII and DII)", theme_tailwind: "Theme",
  governance: "Governance", valuation_sanity: "Valuation",
};
function bars(labels, vals, h = 90) {
  // zero sits where the data puts it: at the bottom when every quarter is a
  // profit (as in the classic's mini charts), mid-chart only when losses exist
  const v = vals.map(x => isNum(x) ? x : 0), w = 100 / v.length;
  const hi = Math.max(0, ...v), lo = Math.min(0, ...v), rg = (hi - lo) || 1;
  const zero = 2 + (hi / rg) * (h - 4);
  const last = [...vals].reverse().find(isNum);
  return `<div style="display:flex;justify-content:space-between;font-size:10.5px" class="faint"><span>peak ${num(hi)}</span>${lo < 0 ? `<span class="neg">low ${num(lo)}</span>` : ""}<span>latest <b style="color:var(--text-2)">${isNum(last) ? num(last) : "—"}</b></span></div>
  <svg width="100%" height="${h}" viewBox="0 0 100 ${h}" preserveAspectRatio="none">${v.map((x, i) => {
    const bh = Math.abs(x) / rg * (h - 4), y = x >= 0 ? zero - bh : zero;
    return `<rect x="${(i * w + w * .15).toFixed(2)}" y="${y.toFixed(2)}" width="${(w * .7).toFixed(2)}" height="${Math.max(.6, bh).toFixed(2)}" rx=".6" fill="${x >= 0 ? css("--buy") : css("--risk")}" opacity=".85"><title>${esc(labels[i] || "")}: ${num(x)}</title></rect>`;
  }).join("")}<line x1="0" x2="100" y1="${zero.toFixed(2)}" y2="${zero.toFixed(2)}" stroke="${css("--border-strong")}" stroke-width=".3"/></svg>
  <div style="display:flex;justify-content:space-between;font-size:10.5px" class="faint"><span>${esc(labels[0] || "")}</span><span>${esc(labels[labels.length - 1] || "")}</span></div>`;
}
function lines(labels, series, h = 90, unit = "%") {
  const all = series.flatMap(s => s.v.filter(isNum));
  if (!all.length) return `<div class="muted">No data.</div>`;
  const mn = Math.min(...all), mx = Math.max(...all), rg = (mx - mn) || 1;
  const n = labels.length;
  const fmt = x => unit === "%" ? x.toFixed(1) + "%" : nf0.format(x) + unit;
  return `<svg width="100%" height="${h}" viewBox="0 0 100 ${h}" preserveAspectRatio="none">${series.map(s => `<polyline fill="none" stroke="${s.c}" stroke-width="1.8" vector-effect="non-scaling-stroke" points="${s.v.map((x, i) => isNum(x) ? `${(i / Math.max(1, n - 1) * 100).toFixed(2)},${(h - 4 - (x - mn) / rg * (h - 8)).toFixed(2)}` : "").filter(Boolean).join(" ")}"/>`).join("")}</svg>
  <div style="display:flex;justify-content:space-between;font-size:10.5px" class="faint"><span>${esc(labels[0] || "")}</span><span>${esc(labels[labels.length - 1] || "")}</span></div>
  <div class="legend">${series.map(s => { const last = [...s.v].reverse().find(isNum); return `<span><i style="background:${s.c}"></i>${esc(s.l)} ${isNum(last) ? fmt(last) : ""}</span>`; }).join("")}</div>`;
}
/* Headlines for one stock: the archive (NSE filings and market headlines,
   30 days, matched by the scan's own matchers), falling back to the top story
   of the last scored read. Until 2026-10-14 the archive was built only for
   names WITHOUT a scored read, so the 472 alerted and focus names, the ones
   that matter most, showed "no filings" (user-reported: "I'm not seeing news
   for the stock"). The builder now ships it for every stock. */
const ROUTINE = /trading window|certificate under (sebi|regulation)|regulation 74|newspaper (advertisement|publication)|copy of newspaper|loss of share certificate|duplicate share|record date|book closure|investor complaints|compliance certificate/i;
function cleanHeadline(t) {
  let s = String(t || "");
  s = s.replace(/^.*?\bhas informed the Exchange (?:about|regarding|that)\s*/i, "");
  s = s.replace(/\s*\|\s*SUBJECT\s*:.*$/i, "").replace(/[-\s]*XBRL\b/gi, "").replace(/\s+Para\s+[A-Z]\b/g, "").trim();
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : String(t || "");
}
function newsItems(sym) {
  const out = (archiveNewsOf(sym) || []).map(x => ({ d: String(x.d || ""), t: cleanHeadline(x.t), src: x.src, u: x.u, routine: ROUTINE.test(String(x.t || "")) }));
  const top = ((detailOf(sym) || {}).news || {}).top_story;
  if (!out.length && top && top.text) out.push({ d: top.date || "", t: top.text, src: top.source || "", u: top.link || "" });
  return out;
}
function newsList(items) {
  return items.map(x => `<div class="news-item${x.routine ? " routine" : ""}"><div class="d">${esc(/^\d{4}-\d{2}-\d{2}/.test(x.d) ? dateLabel(x.d) : x.d)}</div><div><div class="h">${x.u && /^https?:/.test(x.u) ? `<a href="${esc(x.u)}" target="_blank" rel="noopener">${esc(x.t)}</a>` : esc(x.t)}</div>${x.src || x.routine ? `<div class="src">${esc(x.src || "")}${x.routine ? " · routine paperwork" : ""}</div>` : ""}</div></div>`).join("");
}
function toneWord(s) { return !isNum(s) ? "unknown" : s > 0.2 ? "positive" : s > 0.05 ? "mildly positive" : s < -0.2 ? "negative" : s < -0.05 ? "mildly negative" : "neutral"; }
function memWords(t) {
  return String(t || "").replace(/\b(\d+)d\b/g, (m, n) => n + (n === "1" ? " day" : " days"))
    .replace(/\b(\d+)x ([^,;)]+)/g, "$2 ×$1")
    .replace(/\b(\d{4}-\d{2}-\d{2})\b/g, (m, d) => dateLabel(d));
}
function memoryBody(nm) {
  return `${nm.summary ? `<div class="memo" style="margin-bottom:6px">${esc(memWords(nm.summary))}</div>` : ""}${(nm.events || []).slice(-12).reverse().map(e => `<div class="news-item"><div class="d">${esc(dateLabel(String(e[2]).slice(0, 10)))}</div><div class="h"><span class="${e[1] === "neg" ? "neg" : e[1] === "pos" ? "pos" : "muted"}">${e[1] === "neg" ? "▼" : e[1] === "pos" ? "▲" : "·"}</span> ${esc(e[0])}</div></div>`).join("")}`;
}
function dealsBody(dl) {
  return dedupeDeals(dl).map(r => `<div class="news-item"><div class="d">${esc(dateLabel(r.d))}</div><div><div class="h"><span class="${r.side === "BUY" ? "pos" : "neg"}">${r.side === "BUY" ? "▲ bought" : "▼ sold"}</span> ${num(r.qty)} shares at ${px(r.price)} · ${inrShort(r.qty * r.price)}</div><div class="src">${esc(r.client)} · ${esc(r.kind)} deal</div></div></div>`).join("")
    + `<div class="muted" style="font-size:12px;margin-top:6px">Trading desks that bought and sold in the same session are left out.</div>`;
}
function aiCheckBody(v) {
  return `<div class="memo"><p>${esc(plainAI(v.why || ""))}</p>${(v.whys || []).length ? `<h4>Evidence</h4><ul>${v.whys.map(w => `<li>${esc(plainAI(w))}</li>`).join("")}</ul>` : ""}${(v.risks || []).length ? `<h4>Risks</h4><ul>${v.risks.map(w => `<li>${esc(plainAI(w))}</li>`).join("")}</ul>` : ""}${v.flip ? `<h4>What would change the view</h4><p>${esc(plainAI(v.flip))}</p>` : ""}</div>`;
}
function pickBody(pk) {
  return `<div class="memo"><p>${esc(plainAI(pk.thesis || ""))}</p>${pk.catalyst ? `<h4>Catalyst</h4><p>${esc(plainAI(pk.catalyst))}</p>` : ""}${pk.risks ? `<h4>Risks</h4><p>${esc(Array.isArray(pk.risks) ? pk.risks.join(" ") : pk.risks)}</p>` : ""}${pk.watch_for ? `<h4>Watch for</h4><p>${esc(pk.watch_for)}</p>` : ""}</div>`;
}
function sheetHistory(sym) {
  const sc = (D.scorecard || []).filter(r => r.sym === sym);
  const led = ((D.paper || {}).ledger || []).filter(l => l.sym === sym);
  return `<div class="card flush"><div class="card-head"><h3>Buy alerts on ${esc(sym)}</h3><span class="hint">${sc.length} in the journal</span></div>
    ${sc.length ? `<div class="table-wrap"><table class="t"><thead><tr><th>When</th><th>Type</th><th class="r">Conviction</th><th class="r">Alert ₹</th><th class="r">Return</th><th class="r" data-tip="What following the plan made, as a multiple of what it risked: +2R made twice the risk, −1R lost it.">Plan result</th><th>Status</th></tr></thead><tbody>${sc.map(r => `<tr style="cursor:default"><td class="num">${esc(dateLabel(r.d))}</td><td>${esc(sentenceCase((VOC.kinds || {})[r.kind] || r.kind))}</td><td class="r num">${isNum(r.conv) ? r.conv.toFixed(0) : "—"}</td><td class="r num">${px(r.entry)}</td><td class="r num ${cls(r.ret)}">${pct(r.ret)}</td><td class="r num ${cls(r.planr)}">${rr(r.planr)}</td><td class="muted">${esc(r.status)}</td></tr>`).join("")}</tbody></table></div>` : `<div class="muted" style="padding:0 18px 16px">Never alerted.</div>`}</div>
    ${led.length ? `<div class="card" style="margin-top:14px"><div class="card-head"><h3>Paper book fills</h3></div>${led.map(l => `<div class="lrow" style="cursor:default"><span>${esc(l.d)} · ${esc(l.action)} ${esc(l.lot)} · ${esc(l.shares)} @ ${esc(l.price)}</span><span class="num ${cls(+l.pnl)}">${l.pnl !== "" ? inr(+l.pnl) : ""}</span></div>`).join("")}</div>` : ""}`;
}
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
  line(o.pivot, css("--watch"), "alert");
  if (isNum(o.pivot)) line(o.pivot * 1.05, css("--faint"), "buy zone");
  line(o.stop, css("--risk"), "stop");
  line(o.entry, css("--info"), "entry");
  line(o.partial, css("--buy"), "sell part");
  const alerts = (D.scorecard || []).filter(r => r.sym === sym).map(r => String(r.d).slice(0, 10));
  const dates = new Set(data.map(r => r[0]));
  const marks = [...new Set(alerts)].map(d => { let t = d; if (!dates.has(t)) { const nx = data.find(r => r[0] >= d); t = nx ? nx[0] : null; } return t; }).filter(Boolean).sort().map(t => ({ time: t, position: "belowBar", color: css("--ai"), shape: "arrowUp", text: o.compact ? "" : "alert" }));
  if (marks.length) c.setMarkers(marks);
  const n = { "3M": 63, "6M": 126, "1Y": 260 }[o.range || "6M"] || 126;
  const from = data[Math.max(0, data.length - n)][0];
  ch.timeScale().setVisibleRange({ from, to: data[data.length - 1][0] });
  if (!o.compact) { const lg = document.createElement("div"); lg.className = "chart-legend"; lg.innerHTML = legend.join(""); el.appendChild(lg); }
  if (o.rsBox) drawRS(o.rsBox, sym, data, ch, from, o.bucket);
}
function drawRS(el, sym, data, main, from, bucket) {
  const nifty = D.nifty || [];
  if (!nifty.length) { el.style.display = "none"; return; }
  const nm = Object.fromEntries(nifty.map(r => [r[0], r[1]]));
  const pts = data.filter(r => nm[r[0]]).map(r => ({ time: r[0], value: r[4] / nm[r[0]] }));
  if (pts.length < 10) { el.style.display = "none"; return; }
  const base = pts[0].value; pts.forEach(p => p.value = p.value / base * 100);
  const ch = makeChart(el, { bucket });
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
let _pal = { items: [], i: 0 };
function openPalette() { $("#pal").classList.add("on"); const q = $("#palq"); q.value = ""; q.focus(); palSearch(""); }
function closePalette() { $("#pal").classList.remove("on"); }
function palSearch(q) {
  q = q.trim().toLowerCase();
  const pages = PAGES.filter(p => !(p.hidden && p.hidden())).map(p => ({ type: "page", id: p.id, label: p.label }))
    .concat(PAL_PLACES.map(([label, id, sub]) => ({ type: "page", id, sub, label })));
  let items = [];
  if (!q) items = [...pages, ...buySignals().map(a => ({ type: "stock", sym: a.sym })), ...readySetups().slice(0, 8).map(s => ({ type: "stock", sym: s.sym }))];
  else {
    items = pages.filter(p => p.label.toLowerCase().includes(q));
    const scored = searchUniverse().map(u => {
      const s = u.sym.toLowerCase(), c = u.co.toLowerCase();
      const k = s === q ? 0 : s.startsWith(q) ? 1 : c.startsWith(q) ? 2 : s.includes(q) ? 3 : c.includes(q) ? 4 : 9;
      return [k, u];
    }).filter(x => x[0] < 9).sort((a, b) => a[0] - b[0] || b[1].rank - a[1].rank).slice(0, 40);
    items = items.concat(scored.map(x => ({ type: "stock", sym: x[1].sym, u: x[1] })));
  }
  _pal = { items, i: 0 };
  $("#pallist").innerHTML = items.map((it, i) => {
    if (it.type === "page") return `<div class="pal-item ${i === 0 ? "on" : ""}" data-pi="${i}"><span class="muted">Go to</span><span><b>${esc(it.label)}</b></span><span class="kbd">page</span></div>`;
    const r = rowBy[it.sym], u = it.u || {};
    const where = r ? stageChip(r.tag) : MBS[it.sym] ? `<span class="chip sm teal">Multibagger ${Math.round(MBS[it.sym].score)}</span>` : u.where === "penny" ? '<span class="chip sm ghost">Penny</span>' : '<span class="chip sm ghost">Radar</span>';
    return `<div class="pal-item ${i === 0 ? "on" : ""}" data-pi="${i}"><span class="sym">${esc(it.sym)}</span><span class="co" style="max-width:none">${esc((r && r.company) || u.co || nameOf(it.sym))}</span><span>${where}</span></div>`;
  }).join("") || `<div class="muted" style="padding:14px">No stock matches “${esc(q)}”. Golden Stock covers ${num(searchUniverse().length)} NSE stocks, mostly small and mid caps, so many large caps are not here. Try the NSE symbol.</div>`;
}
/* everything a reader can open: the scan, the multibagger table, the radar
   and the penny screen (a penny name searched by name was "No match") */
const PAL_PLACES = [["Multibaggers", "screener", "multibaggers"], ["Penny stocks", "screener", "penny"], ["Themes & market", "screener", "themes"],
  ["Base ready", "watchlist", "ready"], ["Saved stocks", "watchlist", "saved"], ["Deep-dives", "research", "deepdives"], ["Buy checks", "research", "checks"],
  ["Weekly picks", "research", "picks"], ["News", "research", "news"], ["Paper books", "performance", "books"], ["Capital gate", "performance", "gate"], ["Guide", "guide", ""]];
function searchUniverse() {
  if (searchUniverse._u) return searchUniverse._u;
  const u = new Map();
  const add = (sym, co, where, rank) => {
    if (!sym) return;
    const k = String(sym).toUpperCase(), e = u.get(k);
    if (e) { if (!e.co && co) e.co = co; return; }
    u.set(k, { sym: k, co: co || "", where, rank: isNum(rank) ? rank : 0 });
  };
  ROWS.forEach(r => add(r.sym, r.company, "scan", 100 + (r.rs || 0)));
  Object.entries(MBS).forEach(([s, m]) => add(s, nameOf(s), "mb", m.score));
  (RD.rows || []).forEach(r => add(r.sym, nameOf(r.sym), "radar", 0));
  const P = lazy("penny") || D.penny;
  ((P && P.rows) || []).forEach(r => add(r.sym, r.company, "penny", 0));
  return (searchUniverse._u = [...u.values()]);
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
  if (it.type === "page") go(it.id, it.sub); else openStock(it.sym, _pal.items.filter(x => x.type === "stock").map(x => x.sym));
}
let _deb = null; function debounce(fn, ms) { clearTimeout(_deb); _deb = setTimeout(fn, ms); }

/* tooltips: one floating element. Hover on a desktop; on a phone a TAP shows
   it, because phones have no hover (DESIGN.md §6.8). An element that also does
   something (opens a stock, sorts, navigates) keeps its action, and its
   explanation lives where that action leads. */
const TIP = (function () {
  const tip = $("#tip"); let cur = null;
  function show(el) {
    const txt = el.getAttribute("data-tip"); if (!txt) return;
    cur = el; tip.textContent = txt; tip.classList.add("on");
    const r = el.getBoundingClientRect(), tw = tip.offsetWidth, th = tip.offsetHeight;
    let x = r.left + r.width / 2 - tw / 2, y = r.bottom + 8;
    x = Math.max(8, Math.min(window.innerWidth - tw - 8, x));
    if (y + th > window.innerHeight - 8) y = r.top - th - 8;
    tip.style.left = x + "px"; tip.style.top = Math.max(8, y) + "px";
  }
  function hide() { cur = null; tip.classList.remove("on"); }
  document.addEventListener("pointerover", e => { if (e.pointerType !== "mouse") return; const el = e.target.closest("[data-tip]"); if (el && el !== cur) show(el); else if (!el && cur) hide(); });
  document.addEventListener("scroll", hide, true);
  document.addEventListener("click", e => {
    const el = e.target.closest("[data-tip]");
    if (!el) { hide(); return; }
    const acts = el.closest("button, a, [data-sym], [data-go], [data-sort], [data-mbsort], [data-wsel], [data-stab], summary, input, select, label");
    if (!acts || el.classList.contains("info-i")) { if (cur === el) hide(); else show(el); }
  }, true);
  return { show, hide };
})();

/* ==================================================================== routes */
const PAGES = [
  { id: "home", label: "Home", icon: "home" },
  { id: "screener", label: "Screener", icon: "screener" },
  { id: "watchlist", label: "Watchlist", icon: "watchlist" },
  { id: "research", label: "Research", icon: "research" },
  { id: "performance", label: "Performance", icon: "performance" },
];
/* the v7 routes still resolve (bookmarks, old digests) */
/* Old links keep working (bookmarks, Telegram digests, shared story links):
   v7/v9 page names and sub-tabs map onto the five v10 places. */
function canonRoute(h) {
  let [a, b, c] = h;
  if (a === "today") return ["home"];
  if (a === "setups") return ["watchlist", b].filter(Boolean);
  if (a === "portfolio") { if (b) S.book = b; return ["performance", "books"]; }
  if (a === "record") return ["performance", b === "signals" || b === "backtest" ? "evidence" : b].filter(Boolean);
  if (a === "penny") return ["screener", "penny"];
  if (a === "system") return ["performance", "system"];
  if (a === "explore") return ["screener", b === "market" ? "themes" : b].filter(Boolean);
  if (a === "stories") return ["research", "deepdives", b].filter(Boolean);
  if (a === "watchlist" && b === "radar") return ["screener", "multibaggers"];
  if (a === "research") {
    if (b === "deals" || b === "policy") { S.newsView = b; return ["research", "news"]; }
    const m = { reports: "deepdives", analyst: "checks", committee: "picks" };
    return ["research", m[b] || b, c].filter(Boolean);
  }
  if (a === "performance" && (b === "signals" || b === "backtest")) return ["performance", "evidence"];
  return h;
}
const S = {
  page: "home", sub: null,
  stock: null, ctx: [],
  watch: { tab: "ready", sel: null },
  sc: "stocks",
  screener: { q: "", view: "all", ind: "", tier: "", sort: "setup", dir: -1, limit: 150, hideVeto: false, open: false },
  mb: { q: "", sort: "score", dir: -1, limit: 150 },
  research: "deepdives", newsView: "filings", story: null,
  perf: "overview",
  book: "breakout",
  penny: { q: "", arm: "", showVeto: false, sort: "score", dir: -1 },
  chartRange: "6M",
  sheetTab: "overview",
};
let _pageCharts = [], _detailCharts = [], _sheetCharts = [];

function parseHash() {
  return (location.hash || "").replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
}
function go(page, sub) { location.hash = "#/" + page + (sub ? "/" + String(sub).split("/").map(encodeURIComponent).join("/") : ""); }
function onRoute() {
  let h = parseHash();
  if (h[0] === "stock" && h[1]) {
    openStock(h[1], null, true);
    if (!$("#main").dataset.rendered) { renderShell(); renderPage(); }
    return;
  }
  closeSheet(true);
  h = canonRoute(h);
  const id = PAGES.some(p => p.id === h[0]) || h[0] === "guide" ? h[0] : "home";
  S.page = id; S.sub = h[1] || null;
  if (id === "watchlist" && S.sub) S.watch.tab = S.sub;
  if (id === "screener" && S.sub) S.sc = S.sub;
  if (id === "research") { if (S.sub) S.research = S.sub; S.story = S.research === "deepdives" && h[2] ? String(h[2]).toUpperCase() : null; }
  if (id === "performance" && S.sub) S.perf = S.sub;
  renderShell();
  renderPage();
  window.scrollTo(0, 0);
  if (id === "guide" && S.sub) setTimeout(() => { const el = document.getElementById("g-" + S.sub); if (el) el.scrollIntoView({ block: "start" }); }, 60);
}
/* ===================================================================== guide
   One page a first-time reader can finish in two minutes: what this is, the
   four steps, every word the app uses (DESIGN.md §3) and their account size. */
function glossary() {
  const rp = isNum(D.risk_pct) ? D.risk_pct : 1.25;
  return [
    ["Scores", [
      ["Conviction", "0 to 100. An eight-question check of a stock: trend, earnings, money flow, balance sheet, news, governance, valuation and theme. 70 and above is Strong, 50 to 69 Moderate, under 50 Weak. Avoid means a red flag vetoed it. It separates weak stocks from the rest; it does not rank good ones against each other."],
      ["RS", "Relative strength, 0 to 100: how the stock's 6- and 12-month return ranks against the others. 98 means stronger than 98% of them."],
      ["Multibagger score", "0 to 100: how many of the nine ingredients that came before past Indian multibaggers are present at once, such as a turnaround, a low valuation, few institutions, promoters buying, a volume surge or price leadership. A research idea, not a buy signal: even the best signal is followed by a triple about 1 time in 10."],
    ]],
    ["The AI", [
      ["AI rating", "1 to 5. Each week an AI reads the filings, results calls and reports of the top multibagger names and writes a deep-dive. 5 is its strongest long-term view."],
      ["AI check", "Buy, Wait or Skip. Each night an AI analyst reads the top buy alerts and looks for reasons not to buy: results due, red flags, governance. Research, not a filter."],
      ["Weekly pick", "Five stocks a panel of AI analysts picks each week from everything above."],
    ]],
    ["Price stages", [
      ["Uptrend", "All eight trend checks pass. A good backdrop, not a buy by itself."],
      ["Extended", "Ran far above its trend. Don't chase it; wait for it to rest."],
      ["Basing", "A base is forming but the uptrend isn't confirmed yet."],
      ["Neutral", "No clear trend."],
      ["Downtrend", "Falling. Avoid it."],
    ]],
    ["Signals", [
      ["Base", "A stretch where the price moves sideways in tighter and tighter swings after a rise. Breakouts from bases are what the system buys."],
      ["Alert price", "The top of the base. A close above it on at least 1.5 times normal volume is the buy signal."],
      ["Base ready", "A stock in an uptrend with a live base, at any distance from its alert price."],
      ["Near breakout", "A base within 5% of its alert price, or above it and waiting for volume."],
      ["Buy now", "A signal that fired and is still valid. Buy at the next open, unless the price opens more than 5% above the alert price (past the buy zone)."],
      ["Triggered", "Signals from the last 7 days. Opened too high: it gapped past the buy zone, so the plan skipped it. Faded: it fell back under the alert price. Hit its stop: the setup failed."],
      ["Forming", "A base in a stock whose uptrend isn't confirmed yet. Watch only."],
      ["Gap-up", "A stock that jumped on big news with heavy volume. A separate kind of signal, with its own stop."],
      ["Penny stocks", "Very small companies, under ₹100 a share or under ₹1,000 Cr, that passed safety checks: easy enough to sell, not under exchange surveillance, shares not heavily pledged or diluted. They are ranked by the multibagger score; there is no separate penny score."],
      ["Vetoed", "A governance, debt or exchange-surveillance red flag. The system will not buy it, whatever the chart says."],
    ]],
    ["The plan", [
      ["Stop", "The price at which you sell to cap the loss. Place it with your broker as soon as you buy."],
      ["Quantity and risk", `How many shares to buy so that hitting the stop loses at most ${rp}% of your account. Worked out for ${capWord()}; set your own below.`],
      ["Exit plan", "How a winner is sold: part of it at 2.5 times the amount risked, the stop raised to the buy price at 1.5 times, and the rest on a close under the 50-day or 30-week average."],
    ]],
    ["The record", [
      ["Paper books", "Simulated portfolios that follow each set of rules exactly, costs included, so anyone can see whether the rules make money before real money is used."],
      ["Capital gate", "The rule for real money: the system stays on paper until enough signals have qualified and their results clear a bar set in advance. Progress is on Performance."],
      ["Tracked stocks", "Your saved stocks, the watchlist, this week's signals and the 30 highest multibagger scores. Breaking news warns you about these first."],
    ]],
  ];
}
function pageGuide() {
  const groups = glossary();
  return `<div class="guide">
    <section class="card guide-lead"><h2 class="display">How Golden Stock works</h2>
      <p>Every night after the market closes, Golden Stock checks ${num(ROWS.length)} NSE stocks, mostly small and mid caps, and scores the whole market for multibagger ingredients. It looks for one pattern: a strong stock that rests in a tight base, then breaks out on heavy volume. When one is close, it gives you the price to set an alert at, where to put the stop and how many shares to buy.</p>
      <p class="muted">It is decision support, not advice. It places no orders and holds no money: you decide, and you place every trade in your own broker account.</p></section>
    <section class="card" id="g-start"><div class="card-head"><h3>Your first five minutes</h3></div>
      <ol class="guide-steps">
        <li><b>Home</b> answers "anything to do today?" Each tile opens the page behind it. Most days nothing is a buy: the system averages 2 to 3 entries a month.</li>
        <li><b>Find</b> in the <a href="#/screener/stocks">Screener</a>: all stocks by conviction, the <a href="#/screener/multibaggers">multibagger</a> ranking, <a href="#/screener/penny">penny stocks</a> and themes. Tap a column name to sort.</li>
        <li><b>Understand</b> a stock by tapping it. Overview says what the company does and what to do; Chart, Scores, Business and News &amp; AI hold the detail. The star saves it to your list.</li>
        <li><b>Act</b> from the <a href="#/watchlist/ready">Watchlist</a>. Copy the alerts into your broker's price alerts. When one fires, buy only if the day closes above the alert price on heavy volume, then place the stop.</li>
        <li><b>Track</b> on <a href="#/performance/overview">Performance</a>: paper portfolios that follow the rules, compared with the market over the same dates.</li></ol></section>
    ${groups.map(([g, rows], i) => fold(g, rows.length + " terms", `<dl class="gloss">${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl>`, i === 0)).join("")}
    <section class="card" id="g-account"><div class="card-head"><h3>Your account size</h3></div>
      <p class="muted" style="font-size:13px;margin:0 0 10px">Every plan's quantity and rupee risk is worked out for this amount. It is kept in this browser only.</p>
      <div class="acct-row"><label for="gcap" class="muted">₹</label><input class="field" id="gcap" inputmode="numeric" autocomplete="off" value="${esc(String(Math.round(myCapital())))}" aria-label="Account size in rupees">
        <button class="btn sm primary" id="gcapset">Use this</button>${myCapital() !== CAPITAL ? `<button class="btn sm" id="gcapreset">Back to ${esc(inrShort(CAPITAL).replace(".00 L", " L"))}</button>` : ""}</div>
      <div class="muted" style="font-size:12.5px;margin-top:8px">Plans are sized for <b>${esc(capWord())}</b> now.</div></section>
    <div class="guide-foot"><a class="btn sm" href="./">About Golden Stock</a><button class="btn sm" data-go="home">Go to Home</button></div>
  </div>`;
}
/* ===================================================================== shell */
function renderShell() {
  const nb = buySignals().length, nr = readySetups().length, dh = dataHealth();
  const counts = { home: nb, watchlist: nr };
  $("#rail").innerHTML = `
    <div class="brand"><div class="brand-mark">G</div><div><div class="brand-name display">Golden Stock</div><div class="brand-sub">NSE small &amp; mid caps</div></div></div>
    <button class="search-btn" id="railsearch">${I.search}<span>Search stocks</span><kbd>Ctrl K</kbd></button>
    ${PAGES.map(p => `<button class="nav-item ${S.page === p.id ? "on" : ""}" data-go="${p.id}">${I[p.icon]}<span>${p.label}</span>
      ${counts[p.id] ? `<span class="badge-count chip sm ${p.id === "home" ? "buy" : "ghost"}">${counts[p.id]}</span>` : ""}</button>`).join("")}
    <div class="rail-foot">
      <button class="row linkish" data-go="performance" data-sub="system" data-tip="Data freshness for every part of the system."><span class="dot ${dh.state}"></span><span>Prices to ${esc(dateLabel(priceSession()))}</span></button>
      <button class="row linkish" data-go="guide">${I.help}<span>How it works</span></button>
      <div class="row faint">Updated ${esc(D.generated || "")}</div>
    </div>`;
  const title = (PAGES.find(p => p.id === S.page) || {}).label || (S.page === "guide" ? "Guide" : "");
  $("#topbar").innerHTML = `
    <div class="brand-mark sm show-sm" aria-hidden="true">G</div><h1 class="display">${esc(title)}</h1>
    <span class="spacer"></span>
    ${dh.state !== "ok" ? `<button class="pill" data-go="performance" data-sub="system" data-tip="Some data is older than it should be, or a job failed. Open System for the details."><span class="dot ${dh.state}"></span>Data ${dh.word}</button>` : ""}
    <button class="icon-btn" data-go="guide" aria-label="How Golden Stock works" data-tip="How Golden Stock works, and what every word means.">${I.help}</button>
    <button class="icon-btn" id="searchbtn" aria-label="Search stocks">${I.search}</button>
    <button class="icon-btn" id="themebtn" aria-label="Switch between light and dark">${document.documentElement.dataset.theme === "light" ? I.moon : I.sun}</button>`;
  $("#bottomnav").innerHTML = PAGES.map(p => `<button data-go="${p.id}" class="${S.page === p.id ? "on" : ""}" aria-current="${S.page === p.id ? "page" : "false"}"><span class="bn-ic">${I[p.icon]}${p.id === "home" && nb ? `<i class="bn-badge">${nb}</i>` : ""}</span><span class="bn-l">${p.label}</span></button>`).join("");
}
function renderPage() {
  const m = $("#main");
  m.dataset.rendered = "1";
  [_pageCharts, _detailCharts].forEach(b => { b.forEach(c => { try { c.remove(); } catch (e) { } }); b.length = 0; });
  const fn = { home: pageHome, screener: pageScreener, watchlist: pageWatchlist, research: pageResearch, performance: pagePerformance, guide: pageGuide }[S.page] || pageHome;
  m.innerHTML = `<div class="fade-in">${fn()}</div>` + footer();
  afterRender();
}
function footer() {
  return `<div class="foot"><span>Decision support only, not investment advice. You place every order yourself. <a href="#/guide">How it works</a></span>
    <span>Prices: Yahoo daily and NSE bhavcopy · Fundamentals: screener.in · Filings: NSE</span></div>`;
}
const AFTER = [];
function afterRender() { while (AFTER.length) { try { AFTER.shift()(); } catch (e) { console.error(e); } } }

/* ====================================================================== HOME
   A to-do list, in the order you act on it. Anything that needs no action
   from you (paper books, the capital gate, backtests) is on Performance. */
function homeAlerts() {
  return readySetups().filter(s => isNum(s.dist)).sort((a, b) => Math.abs(a.dist) - Math.abs(b.dist)).slice(0, 6);
}
function radarLast(r) { return Object.values(r.signals || {}).sort().slice(-1)[0] || ""; }
function radarRecent(n) { return (RD.rows || []).slice().sort((a, b) => radarLast(b).localeCompare(radarLast(a))).slice(0, n); }
function radarCls(k) { return k === "H7" ? "buy" : k === "H25" ? "teal" : k === "H14" ? "ai" : k === "H20" ? "info" : "watch"; }
function radarOdds(k) { const R = (RD.research || {})[k]; return R && R.universe_pct > 0 && isNum(R.tripled_within_1y_pct) ? R.tripled_within_1y_pct / R.universe_pct : null; }
function radarChip(k, d) {
  const R = (RD.research || {})[k] || {}, x = radarOdds(k);
  const tip = (RADAR_TIP[k] || "") + (x ? ` Stocks with this signal tripled within a year ${x.toFixed(1)}× as often as the average liquid stock (${num(R.tripled_within_1y_pct, 1)}% against ${num(R.universe_pct, 1)}%).` : "") + (d ? " Fired " + d + "." : "") + (k === "H25" && RD.insider_asof ? " Promoter disclosures up to " + dateLabel(RD.insider_asof) + "." : "");
  return `<span class="chip sm ${radarCls(k)}" data-tip="${esc(tip)}">${esc(RADAR_WORD[k] || k)}</span>`;
}
function step(n, title, hint, body) {
  return `<section class="step"><div class="step-n">${n}</div><div class="step-body">
    <div class="step-head"><h3>${esc(title)}</h3>${hint ? `<span class="hint">${esc(hint)}</span>` : ""}</div>${body}</div></section>`;
}
function headsUp(syms) {
  const out = [];
  syms.forEach(sym => {
    const m = newsMem[sym];
    if (m && m.n_neg) {
      const negs = (m.events || []).filter(e => e[1] === "neg"), last = negs[negs.length - 1];
      const age = last ? daysSince(last[2]) : null;
      if (age != null && age <= 30) out.push({ sym, kind: "risk", text: `${last[0]} filing ${age === 0 ? "today" : age + (age === 1 ? " day ago" : " days ago")}` });
    }
    const s = survBy[sym];
    if (s && s.flags && s.flags.length) out.push({ sym, kind: "watch", text: survText(s.flags) });
  });
  return out;
}
/* The banner (DESIGN.md §6.1): one tile per question you open the app with,
   each a button to the page that answers it. Then the to-do list, three rows a
   section. Nothing that runs by itself (books, the gate) appears here. */
/* "Tracked" stocks, one definition everywhere (the Guide says it in words):
   saved, the watchlist, this week's signals and the 30 top multibagger scores. */
function trackedSyms() {
  return new Set([...SAVED, ...buySignals().map(a => a.sym), ...readySetups().map(s => s.sym), ...recentTriggers().map(a => a.sym), ...mbTop(30).map(m => m.sym), ...heldSyms()]);
}
function breakingNews() {
  const hits = (D.radar || {}).hits || [];
  const follow = trackedSyms();
  const negF = hits.filter(h => h.cls === "neg" && follow.has(h.sym));
  const surv = [...follow].filter(s => survBy[s] && (survBy[s].flags || []).length);
  return { hits, negF, surv };
}
function aiLatest() {
  const P = D.ai_picks || {}, vi = D.verdict_items || [];
  const vDate = vi.map(v => String(v.stamp || "")).sort().slice(-1)[0] || "";
  const dives = Object.values(MRS), dDate = dives.map(m => String(m.date || "")).sort().slice(-1)[0] || "";
  return { picks: (P.picks || []).length, pDate: String(P.generated || "").slice(0, 10),
    checks: vi.filter(v => String(v.stamp || "") === vDate).length, vDate,
    dives: dives.filter(m => String(m.date || "") === dDate).length, dDate };
}
function bannerTiles() {
  const buys = buySignals(), ready = readySetups(), near = homeAlerts()[0];
  const nearN = ready.filter(s => isNum(s.dist) && s.dist <= 5).length;
  const faded = recentTriggers().filter(a => !buys.some(b => b.sym === a.sym));
  const top = mbTop(1)[0], nMB = Object.keys(MBS).length;
  const bn = breakingNews(), ai = aiLatest(), rg = regime(), dh = dataHealth();
  const newsNote = bn.negF.length
    ? `${bn.negF.length} negative on ${bn.negF.length === 1 ? "a tracked stock" : "tracked stocks"}: ${bn.negF.slice(0, 2).map(h => h.sym).join(", ")}${bn.negF.length > 2 ? " +" + (bn.negF.length - 2) : ""}`
    : bn.hits.length ? "Filings since the last scan. None negative on tracked stocks." : "No new filings since the last scan.";
  return [
    { label: "Buy now", icon: I.bolt, s: buys.length ? "buy" : "", val: String(buys.length),
      note: buys.length ? buys.slice(0, 3).map(a => a.sym).join(", ") + (buys.length > 3 ? " +" + (buys.length - 3) : "") : "None today" + (faded.length ? `. ${faded.length} triggered this week` : ""),
      go: "watchlist", sub: buys.length || !faded.length ? "buy" : "triggered" },
    { label: "Near breakout", icon: I.bell, s: "info", val: String(nearN),
      note: nearN ? `Within 5% of their alert price. Closest: ${near.sym}${isNum(near.dist) && near.dist >= 0 ? ", " + Math.abs(near.dist).toFixed(1) + "% away" : ", already above it"}` : `None within 5%. ${ready.length} bases are ready further away`,
      go: "watchlist", sub: "ready" },
    { label: "Multibaggers", icon: I.gem, s: "teal", val: top ? top.sym : "—", word: true,
      note: top ? `Score ${Math.round(top.score)}, top of ${num(nMB)} ranked` : "Not computed on this build", go: "screener", sub: "multibaggers" },
    { label: "Breaking news", icon: I.news, s: bn.negF.length ? "warn" : "", val: num(bn.hits.length) + " new", word: true, note: newsNote, go: "research", sub: "news" },
    { label: "AI research", icon: I.research, s: "ai", val: ai.picks ? ai.picks + " picks" : ai.checks + " checks", word: true,
      note: [ai.picks ? `Weekly picks ${dateLabel(ai.pDate)}` : "", ai.checks ? `${ai.checks} buy checks ${dateLabel(ai.vDate)}` : ""].filter(Boolean).join(" · ") || "No AI research yet",
      go: "research", sub: ai.picks ? "picks" : "checks" },
    { label: "Health", icon: I.pulse, s: dh.state === "fail" ? "risk" : dh.state === "warn" || rg.defensive ? "warn" : "ok",
      val: dh.state !== "ok" ? "Data " + dh.word : rg.defensive ? "Market weak" : "Healthy", word: true,
      note: dh.state !== "ok"
        ? `${dh.bad.concat(dh.warn).map(x => x.label).join(", ")} ${dh.bad.length + dh.warn.length > 1 ? "are" : "is"} ${dh.word}. Market ${rg.defensive ? "weak, so buys are half" : "healthy, so buys are full"} size.`
        : `${isNum(rg.breadth) ? rg.breadth.toFixed(0) + "% of stocks are above their 200-day average, so buys are " : "Buys are "}${rg.defensive ? "half" : "full"} size. Data fresh.`,
      go: "performance", sub: "system" },
  ];
}
function tileHtml(t) {
  return `<button class="tile ${t.s ? "s-" + t.s : ""}" data-go="${t.go}" data-sub="${t.sub}">
    <span class="tile-top"><span class="tile-ic">${t.icon}</span><span class="tile-lab">${esc(t.label)}</span><span class="tile-chev" aria-hidden="true">›</span></span>
    <span class="tile-val ${t.word ? "word" : ""}">${esc(t.val)}</span>
    <span class="tile-note">${esc(t.note)}</span></button>`;
}
function pageHome() {
  const buys = buySignals(), ready = readySetups(), alerts = homeAlerts().slice(0, 3), mbt = mbTop(3);
  const faded = recentTriggers().filter(a => !buys.some(b => b.sym === a.sym));
  const heads = headsUp(new Set([...buys.map(a => a.sym), ...homeAlerts().map(s => s.sym), ...mbTop(6).map(m => m.sym), ...SAVED]));
  let n = 0;
  return `
  ${welcomeCard()}<div class="home-asof">Prices to the close on ${esc(dayName(priceSession()))}</div>
  <div class="board">${bannerTiles().map(tileHtml).join("")}</div>
  ${step(++n, "Buy today", buys.length ? buys.length + " valid signal" + (buys.length > 1 ? "s" : "") + " with a sized plan" : "",
    buys.length ? `<div class="action-list">${buys.slice(0, 3).map(buyCard).join("")}</div>${buys.length > 3 ? `<div class="step-actions">${seeAll("watchlist", "buy", "See all " + buys.length)}</div>` : ""}`
      : `<div class="step-empty"><b>Nothing to buy today.</b> That's normal: the system averages 2–3 entries a month, with gaps of weeks.${faded.length ? ` <a href="#/watchlist/triggered">${faded.length} stock${faded.length > 1 ? "s" : ""} triggered this week</a> but opened too high or faded back.` : ""}</div>`)}
  ${step(++n, "Set price alerts", ready.length ? `the ${alerts.length} closest of ${ready.length} · sized for ${capWord()}` : "", alertsBlock(alerts, ready.length))}
  ${mbt.length ? step(++n, "Research these", "the highest multibagger scores, whole market", mbBlock(mbt)) : ""}
  ${heads.length ? step(++n, "Heads-up", "risk flags on stocks near a buy, saved, or high on the multibagger list", headsBlock(heads)) : ""}`;
}
/* First visit: what this is and the four steps, until dismissed (Guide has the rest). */
function welcomeCard() {
  if (store("gs.welcomed") === "1") return "";
  return `<section class="welcome" id="welcome"><div class="welcome-head"><h2 class="display">New here? Start with this.</h2><button class="icon-btn" data-welcome="close" aria-label="Hide this introduction">${I.close}</button></div>
    <p>Golden Stock checks ${num(ROWS.length)} NSE stocks every night, mostly small and mid caps. It finds the few setting up to rise, gives the exact price to buy at with a stop and a quantity, and keeps a public record of how its signals did.</p>
    <ol class="welcome-steps">
      <li><b>Find.</b> The <a href="#/screener/stocks">Screener</a> ranks stocks by conviction, and the whole market by multibagger score.</li>
      <li><b>Understand.</b> Tap any stock for what the company does, its scores, the AI's notes and the latest news.</li>
      <li><b>Act.</b> The <a href="#/watchlist/ready">Watchlist</a> gives alert prices. Set them in your broker's app and buy only on a close above.</li>
      <li><b>Track.</b> <a href="#/performance/overview">Performance</a> shows, on paper and in public, whether the system makes money.</li></ol>
    <div class="welcome-actions"><a class="btn sm primary" href="#/guide">Read the 2-minute guide</a><button class="btn sm" data-welcome="close">Got it</button></div></section>`;
}
function alertLine(s, forming) {
  if (!isNum(s.dist)) return `Alert <b class="num">${px(s.pivot)}</b>`;
  if (s.dist >= 0) return `Alert <b class="num">${px(s.pivot)}</b> · <span class="${s.dist <= 2 ? "pos" : ""}">${Math.abs(s.dist).toFixed(1)}% away</span>`;
  return `Alert <b class="num">${px(s.pivot)}</b> · <span class="warn">${forming ? "price is above it, but the uptrend isn't confirmed yet" : "price is above it: a close here on 1.5× normal volume makes it a buy"}</span>`;
}
function planLine(s) {
  const p = s.plan && !s.plan.skip ? sized(s.plan) : null;
  return p ? `Stop <span class="num">${px(p.stop)}</span> · <span class="num">${num(p.shares)}</span> shares · risk <span class="num">${inr(p.risk)}</span>`
    : `<span class="warn">No sized plan: the stop would be more than 12% away</span>`;
}
function alertsBlock(list, total) {
  if (!list.length) return `<div class="step-empty">No stock has a ready base right now. Bases take weeks to form; this list refills as they do.</div>`;
  return `<div class="slist">${list.map(s => stockCard(s.sym, { ctx: "alerts", line: alertLine(s), sub: planLine(s) })).join("")}</div>
    <div class="step-actions"><button class="btn sm" data-copy-alerts="home">${I.copy}Copy these alerts</button>${seeAll("watchlist", "ready", "See all " + total)}</div>`;
}
function headsBlock(list) {
  return `<div class="card list-card">${list.slice(0, 3).map(i => `<div class="hrow" data-sym="${esc(i.sym)}"><span class="hic ${i.kind === "risk" ? "risk" : ""}">!</span><div><span class="sym">${esc(i.sym)}</span><div class="act">${esc(i.text)}</div></div></div>`).join("")}</div>
    ${list.length > 3 ? `<div class="step-actions">${seeAll("research", "news", "See all " + list.length)}</div>` : ""}`;
}
function radarBlock(list) {
  return `<div class="card flush"><div class="alist">${list.map(r => {
    const inU = !!rowBy[r.sym];
    const best = Object.keys(r.signals || {}).map(radarOdds).filter(isNum).reduce((a, b) => Math.max(a, b), 0);
    return `<div class="arow" data-sym="${esc(r.sym)}" data-ctx="radar">
      <div class="cell-sym"><span class="sym">${esc(r.sym)}</span><span class="co">${esc((rowBy[r.sym] || {}).company || "")}</span></div>
      <div class="a-main">${Object.entries(r.signals || {}).map(([k, d]) => radarChip(k, d)).join(" ")} ${convChip(r.sym)}
        <div class="a-sub"><span class="${cls(r.ret_6m_pct)}">${pct(r.ret_6m_pct, 0)}</span> in 6 months${best ? ` · ${best.toFixed(1)}× the usual odds of tripling` : ""}</div></div>
      <div class="a-spark">${closesOf(r.sym).length ? spark(closesOf(r.sym), 84, 26) : ""}</div>
      <div class="a-score" data-tip="Relative strength percentile (100 = strongest).">${rsCell(r.rs_pct)}</div>
    </div>`; }).join("")}</div></div>
    <div class="step-actions"><button class="btn sm" data-go="screener" data-sub="multibaggers">The full radar</button>
      <span class="muted" style="font-size:12px">Ideas to research, not buy signals: even the best signal is followed by a triple about 1 time in 10.</span></div>`;
}

/* ================================================================= WATCHLIST
   A terminal: the list on the left, everything about the selected stock on
   the right. ↑ ↓ move through the list. On a phone a tap opens the stock. */
const WTABS = [["buy", "Buy now"], ["ready", "Base ready"], ["triggered", "Triggered"], ["forming", "Forming"], ["saved", "Saved"]];
const WHINT = {
  buy: "Valid signals with a sized plan. Buy at the next open, or skip it if the price has run more than 5% past the alert.",
  ready: "Stocks in an uptrend with a base ready, closest to their alert price first; vetoed names are left out. A close above the alert price on 1.5× normal volume makes it a buy.",
  triggered: "Signals from the last 7 days, including ones that opened too high or faded back.",
  forming: "A base is forming but the uptrend isn't confirmed yet. Watch only.",
  saved: "Stocks you saved with the star on their page. They stay in this browser only.",
};
function watchItems(tab) {
  if (tab === "buy") return buySignals().map(a => ({ sym: a.sym, a }));
  if (tab === "triggered") return recentTriggers().map(a => ({ sym: a.sym, a }));
  if (tab === "forming") return formingSetups().map(s => ({ sym: s.sym, s }));
  if (tab === "saved") return [...SAVED].map(sym => ({ sym, saved: true }));
  const d = s => isNum(s.dist) ? Math.abs(s.dist) : 99;
  return readySetups().slice().sort((x, y) => d(x) - d(y)).map(s => ({ sym: s.sym, s }));
}
function subtabs(list, cur, attr, counts) {
  return `<div class="subtabs" role="tablist">${list.map(([k, l]) => `<button role="tab" ${attr}="${k}" class="${cur === k ? "on" : ""}" aria-selected="${cur === k}">${esc(l)}${counts && counts[k] != null ? `<span class="count">${counts[k]}</span>` : ""}</button>`).join("")}</div>`;
}
function pageWatchlist() {
  const tab = WTABS.some(t => t[0] === S.watch.tab) ? S.watch.tab : "ready";
  S.watch.tab = tab;
  const items = watchItems(tab);
  S.ctx = items.map(i => i.sym);
  if (!items.some(i => i.sym === S.watch.sel)) S.watch.sel = items.length ? items[0].sym : null;
  AFTER.push(() => drawWatchDetail());
  const counts = Object.fromEntries(WTABS.map(([k]) => [k, watchItems(k).length]));
  return `${subtabs(WTABS, tab, "data-wtab", counts)}
  <div class="page-intro">${esc(WHINT[tab])}${tab === "buy" || tab === "ready" ? ` Quantities are for a ${capWord()} account (<a href="#/guide/account">change</a>).` : ""}${tab === "ready" && items.length ? ` <button class="btn sm" data-copy-alerts="watch" style="margin-left:6px">${I.copy}Copy all alerts</button>` : ""}</div>
  <div class="wl-grid">
    <div class="wl-list" id="wllist">${items.length ? `<div class="slist">${items.slice(0, S.watch.limit || 30).map(it => watchCard(tab, it)).join("")}</div>${items.length > (S.watch.limit || 30) ? `<div style="padding:12px 0"><button class="btn" id="wmore">Show ${Math.min(30, items.length - (S.watch.limit || 30))} more of ${items.length - (S.watch.limit || 30)}</button></div>` : ""}` : `<div class="empty">${tab === "buy" ? "<b>Nothing to buy today.</b> That's normal: the system averages 2–3 entries a month." : tab === "saved" ? "<b>Nothing saved yet.</b> Open any stock and tap the star next to its price to keep it here." : "Nothing here right now."}</div>`}</div>
    <div class="wl-detail" id="wldetail"></div>
  </div>`;
}
function statusChip(st, a) {
  if (a && st === "ACTIONABLE" && underStop(a)) return '<span class="chip sm risk" data-tip="The price closed under the plan\'s stop: the setup failed.">under its stop</span>';
  if (a && st === "ACTIONABLE" && stoppedSince(a)) return '<span class="chip sm risk" data-tip="The price fell to the plan\'s stop after the signal, so the setup failed. It is not a buy, even if the price has come back.">hit its stop</span>';
  if (a && st === "ACTIONABLE" && !buySignals().some(b => b.sym === a.sym)) return '<span class="chip sm ghost" data-tip="The signal is open, but the chart is not a confirmed breakout, so the plan does not buy it.">watch only</span>';
  return st === "ACTIONABLE" ? '<span class="chip sm buy" data-tip="Still a buy: it is in Buy now with a sized plan.">still valid</span>'
    : st === "RAN AWAY" ? '<span class="chip sm watch" data-tip="It opened more than 5% above the alert price, past the buy zone, so the plan skipped it.">opened too high</span>'
    : st === "VETOED" ? '<span class="chip sm risk">vetoed</span>'
    : '<span class="chip sm ghost" data-tip="The breakout fell back below the alert price.">faded</span>';
}
function watchCard(tab, it) {
  const o = { ctx: "watch", wsel: true, sel: it.sym === S.watch.sel };
  if (it.saved) { o.line = savedLine(it.sym); return stockCard(it.sym, o); }
  if (it.s) { o.line = alertLine(it.s, tab === "forming"); o.sub = tab === "forming" ? "Watch only until the uptrend is confirmed" : planLine(it.s); }
  else if (it.a) {
    const a = it.a;
    o.chips = statusChip(a.status, a);
    o.line = `${a.dokind === "ep" ? "Gap-up" : "Breakout"} on ${esc(dateLabel(a.d))} at <b class="num">${px(a.alert_px)}</b> · <span class="${cls(a.chg)}">${pct(a.chg)}</span> since`;
  }
  return stockCard(it.sym, o);
}
function savedLine(sym) {
  const a = buySignals().find(x => x.sym === sym);
  if (a) return `<span class="pos">Buy signal</span> · ${a.dokind === "ep" ? "gap-up" : "breakout"} on ${esc(dateLabel(a.d))}`;
  const st = setupBy[sym], r = rowBy[sym];
  if (st && st.status === "AWAITING TRIGGER") return alertLine(st, !r || r.tag !== "CONFIRMED");
  if (r) return `${esc(stageWord(r.tag))} · no base yet`;
  return MBS[sym] ? `Multibagger score ${Math.round(MBS[sym].score)} · outside the nightly scan` : "Outside the nightly scan";
}
function drawWatchDetail() {
  const box = $("#wldetail");
  if (!box || window.innerWidth <= 980) return;
  _detailCharts.forEach(c => { try { c.remove(); } catch (e) { } });
  _detailCharts.length = 0;
  const sym = S.watch.sel;
  if (!sym) { box.innerHTML = ""; return; }
  box.innerHTML = `<div class="card detail-card">${stockHead(sym)}${hasDetail(sym) ? stockTabs() + `<div class="stab-body">${stockTabBody(sym, "w")}</div>` : outsideDetail(sym)}</div>`;
  if (hasDetail(sym)) drawStockTab(sym, "w", _detailCharts);
}
/* ============================================================== STOCK DETAIL
   One scroll, most important first: what to do, the chart, why the score,
   the business, the news, the history. Used by the watchlist's right pane
   and by the full-screen sheet (prefix "w" or "s" keeps the chart ids apart). */
function hasDetail(sym) { return !!(rowBy[sym] || setupBy[sym] || ohlcOf(sym)); }
function stockHead(sym, nav) {
  const r = rowBy[sym] || {}, st = setupBy[sym], q = quoteOf(sym);
  const o = ohlcOf(sym) || [];
  const price = o.length ? o[o.length - 1][4] : q.price;
  const chg = o.length > 1 ? (o[o.length - 1][4] / o[o.length - 2][4] - 1) * 100 : q.chg;
  const lastDay = o.length ? o[o.length - 1][0] : null, stale = lastDay && lastDay < String(priceSession() || "").slice(0, 10);
  const chips = [r.tag ? stageChip(r.tag) : "", (r.trig || (st && st.status)) && ["VALIDATED", "AWAITING TRIGGER", "EP EVENT"].includes(r.trig || st.status) ? setupChip(r.trig || st.status) : "", r.veto ? '<span class="chip sm risk">Vetoed</span>' : "", survChips(sym)].filter(Boolean).join(" ");
  return `<div class="shead">
    <div class="shead-row">${nav && nav.back ? nav.back : ""}<h2 class="display">${esc(sym)}</h2>
      <span class="shead-px">${isNum(price) ? `<b>${px(price)}</b>` : ""}${isNum(chg) ? `<span class="${cls(chg)}">${movePct(chg)}</span>` : ""}${stale ? `<span class="faint stale-px" data-tip="No trade on the exchange since then.">last traded ${esc(dateLabel(lastDay))}</span>` : ""}</span>${saveBtn(sym)}</div>
    <div class="shead-co"><span class="shead-coname">${esc(coLine(sym))}</span>${chips ? `<span class="shead-chips">${chips}</span>` : ""}${nav && nav.right ? nav.right : ""}</div>
  </div>`;
}
/* the exit rules in words, not R multiples */
function exitWords(p) {
  return `The position is two halves. When the price reaches <b class="num">${px(p.partial)}</b> (a gain of 2.5 times what the trade risks), sell a third of the first half. Once a close reaches <b class="num">${px(p.be)}</b> (1.5 times the risk), move both stops up to the buy price. After that the first half sells on a close below the 50-day average, and the second half only on a weekly close below the 30-week average.`;
}
function todoBox(sym) {
  const r = rowBy[sym] || {}, st = setupBy[sym], d = detailOf(sym) || {};
  const a = buySignals().find(x => x.sym === sym), plan = sized(planOf(sym));
  const sp = st && st.plan && !st.plan.skip ? sized(st.plan) : null;
  const rr0 = (RD.rows || []).find(x => x.sym === sym);
  const cells = list => `<div class="plan-grid">${list.map(([k, v, c, s]) => `<div class="plan-cell"><div class="k">${k}</div><div class="v ${c || ""}">${v}</div>${s ? `<div class="s">${s}</div>` : ""}</div>`).join("")}</div>`;
  const tail = p => `<details class="more" style="margin-top:8px"><summary>Exit plan</summary><div class="muted" style="font-size:12.5px">${exitWords(p)}</div></details>`;
  if (r.veto) return `<div class="todo risk"><div class="todo-head"><span class="todo-tag">Avoid</span><span class="todo-text">Vetoed: ${esc((d.veto_reasons || []).map(vetoWords).join("; ") || "a governance or leverage red flag")}.</span></div></div>`;
  if (a && plan && !plan.skip) return `<div class="todo buy"><div class="todo-head"><span class="todo-tag">Buy signal</span><span class="todo-text">${a.dokind === "ep" ? "Gap-up" : "Breakout"} on ${esc(dateLabel(a.d))} at ${px(a.alert_px)}; now ${px(a.now_px)} <span class="${cls(a.chg)}">${pct(a.chg)}</span>.</span></div>
    ${cells([["Entry ≈", px(plan.entry)], ["Stop", px(plan.stop), "neg", isNum(plan.stop_pct) ? pct(-plan.stop_pct) : ""], ["Quantity", num(plan.shares)], ["Risk", inr(plan.risk), "", isNum(riskShare(plan)) ? riskShare(plan).toFixed(2) + "% of " + capWord() : ""]])}</div>`;
  if (st && st.status === "AWAITING TRIGGER") return `<div class="todo watch"><div class="todo-head"><span class="todo-tag">Set an alert</span><span class="todo-text">${isNum(st.dist) && st.dist < 0 ? `It closed above its alert price of <b>${px(st.pivot)}</b>, but on ${isNum(st.vr) ? st.vr.toFixed(1) + "×" : "less than"} normal volume, so it is not a buy yet. A close above it with at least <b>${volFmt(st.vneed)}</b> shares traded makes it one.` : `Buy only on a close above <b>${px(st.pivot)}</b> with at least <b>${volFmt(st.vneed)}</b> shares traded (today: ${isNum(st.vr) ? st.vr.toFixed(1) + "×" : "—"} normal volume).`}</span>${sp ? `<button class="btn sm" data-copy-one="${esc(sym)}" style="margin-left:auto">${I.copy}Copy alert</button>` : ""}</div>
    ${sp ? cells([["Alert price", px(st.pivot), "", "buy zone to " + px(st.zone_top)], ["Stop", px(sp.stop), "neg", Math.abs(sp.stop_pct).toFixed(1) + "% below the alert"], ["Quantity", num(sp.shares), "", inrShort(sp.value) + " position"], ["Risk", inr(sp.risk), "", (sp.risk / myCapital() * 100).toFixed(2) + "% of " + capWord()]]) + tail(sp) : `<div class="muted" style="font-size:12.5px">${esc(plainAI(st.plan && st.plan.why || "No sized plan: the stop would be wider than the 12% cap."))}</div>`}</div>`;
  if (rr0 && !r.sym) return `<div class="todo ai"><div class="todo-head"><span class="todo-tag">Research it</span><span class="todo-text">Flagged as a possible multibagger (${Object.keys(rr0.signals || {}).map(k => esc(RADAR_WORD[k] || k)).join(", ")}). ${MRS[sym] ? `An AI deep-dive read its filings: <b>AI rating ${esc(MRS[sym].conviction)} of 5</b> (${esc(MRS[sym].horizon || "")}), below.` : "Not a buy signal: read the business and the news below first."}</span></div></div>`;
  if (st && st.status) return `<div class="todo ghost"><div class="todo-head"><span class="todo-tag">Watch</span><span class="todo-text">${esc(SETUP_WORD[st.status] || st.status)}. Nothing to do until a fresh base forms.</span></div></div>`;
  return `<div class="todo ghost"><div class="todo-head"><span class="todo-tag">No setup</span><span class="todo-text">${esc(stageWord(r.tag))}. Nothing to do until a base forms; it will appear in the watchlist when one does.</span></div></div>`;
}
function factsCard(sym) {
  const r = rowBy[sym] || {}, d = detailOf(sym) || {}, st = setupBy[sym];
  const rows = [["Stage", esc(d.stage_name || stageWord(r.tag))], ["Trend checks", isNum(d.tt_checks) ? d.tt_checks + " of 8" : "—"],
    ["Base", st ? "live, pivot " + px(st.pivot) : d.vcp ? "live" : "none"], ["Daily range", st && isNum(st.atr_pct) ? st.atr_pct + "% (ATR)" : "—"]];
  return `<div class="card"><div class="card-head"><h3>The chart in words</h3></div><div class="facts">${rows.map(([k, v]) => `<div class="k">${k}</div><div>${v}</div>`).join("")}</div>
    ${(d.reasons || []).length ? `<div class="muted" style="font-size:12px;margin-top:10px">${d.reasons.map(esc).join(" · ")}</div>` : ""}</div>`;
}
/* The stock sheet opens on Overview and splits the rest into tabs, so nothing
   is more than one tap and about two screens away. It used to be one column
   of 26 sections, about nine phone screens (DESIGN.md §6.6). */
const STABS = [["overview", "Overview"], ["chart", "Chart"], ["scores", "Scores"], ["business", "Business"], ["news", "News & AI"]];
function stockTabs() {
  if (!STABS.some(t => t[0] === S.sheetTab)) S.sheetTab = "overview";
  return `<div class="stabs" role="tablist">${STABS.map(([k, l]) => `<button role="tab" data-stab="${k}" class="${S.sheetTab === k ? "on" : ""}" aria-selected="${S.sheetTab === k}">${l}</button>`).join("")}</div>`;
}
function stockTabBody(sym, p) {
  return ({ overview: tabOverview, chart: tabChart, scores: tabScores, business: tabBusiness, news: tabNews }[S.sheetTab] || tabOverview)(sym, p);
}
function briefBlock(sym, full) {
  const b = briefOf(sym);
  if (!b) return `<div class="brief"><span class="brief-lab">What it does</span><p class="muted" style="font-size:13px">No company description yet. It is read from screener.in, and new names fill in within a week.</p></div>`;
  return `<div class="brief"><span class="brief-lab">What it does</span><p class="${full ? "" : "clamp"}" ${full ? "" : `data-expand="1" title="Tap to read it all"`}>${esc(b)}</p>
    <span class="brief-src">Source: <a href="https://www.screener.in/company/${encodeURIComponent(sym)}/" target="_blank" rel="noopener">screener.in</a></span></div>`;
}
function scoreTiles(sym) {
  const r = rowBy[sym] || {}, m = MBS[sym], mr = MRS[sym], v = verdictBy[sym], pk = pickBy[sym], b = convBand(r.score, r.veto);
  const nIng = Object.keys(MBCFG).length;
  const kindOf = c => c === "buy" ? "" : c === "watch" ? "watch" : c === "risk" ? "risk" : "mid";
  const aiVal = mr && isNum(+mr.conviction) ? `<span class="v ai">${esc(mr.conviction)}/5</span><span class="w ai">AI rating</span>`
    : v ? `<span class="v ${v.verdict === "BUY" ? "buy" : v.verdict === "SKIP" ? "risk" : "watch"}">${esc(VERDICT_WORD[v.verdict] || v.verdict)}</span><span class="w muted">AI check</span>`
    : pk ? `<span class="v ai">Pick</span>` : `<span class="v faint">—</span>`;
  // one stock, one score (user, 2026-10-14): a scan stock is judged by
  // Conviction; the multibagger score belongs to the multibagger list
  return `<div class="stiles n3">
    <button class="stile" data-stab="scores"><span class="k">Conviction</span><span class="row"><span class="v ${b.cls}">${isNum(r.score) ? Math.round(r.score) : "—"}</span><span class="w ${b.cls}">${b.word}</span></span>${isNum(r.score) ? meter(r.score / 100, kindOf(b.cls)) : ""}<span class="s">${(detailOf(sym) || {}).dims_as_of || (detailOf(sym) || {}).scored_at ? "read " + esc(dateLabel((detailOf(sym) || {}).dims_as_of || (detailOf(sym) || {}).scored_at)) + " · " : ""}tap for the reasons</span></button>
    <div class="stile" data-tip="Relative strength: the 6- and 12-month return ranked against the whole universe. 98 means stronger than 98% of stocks."><span class="k">RS</span><span class="row"><span class="v">${isNum(r.rs) ? Math.round(r.rs) : "—"}</span><span class="w muted">of 100</span></span>${isNum(r.rs) ? meter(r.rs / 100, "info") : ""}<span class="s">${isNum(r.rs) ? (r.rs >= 99.5 ? "Among the very strongest stocks" : "Stronger than " + Math.round(r.rs) + "% of stocks") : "Not ranked"}</span></div>
    <button class="stile" data-stab="news"><span class="k">AI</span><span class="row">${aiVal}</span>${pk ? `<span class="chips"><span class="chip sm ai">Weekly pick · ${esc(dateLabel((D.ai_picks || {}).generated))}</span></span>` : ""}<span class="s">${mr ? "Rated " + esc(dateLabel(mr.date)) + (v ? " · AI check: " + esc(VERDICT_WORD[v.verdict] || v.verdict) : "") : !v && !pk ? "No AI research yet" : "Tap for the notes"}</span></button>
  </div>`;
}
function headsFor(sym) {
  const h = headsUp(new Set([sym]));
  if (!h.length) return `<div class="ok-line"><span class="dot ok"></span>No risk filings or exchange surveillance in the last 30 days.</div>`;
  return `<div class="card list-card">${h.map(i => `<div class="hrow" style="cursor:default"><span class="hic ${i.kind === "risk" ? "risk" : ""}">!</span><div class="act">${esc(i.text)}</div></div>`).join("")}</div>`;
}
/* Overview: who the company is, what to do, the scores, how the price has
   moved, what the AI says and the latest news. The chart lives in its own
   tab only (it used to appear on both, user-reported 2026-10-14). */
function priceFacts(sym) {
  const o = ohlcOf(sym) || [];
  if (o.length < 30) return "";
  const c = o.map(r => r[4]), last = c[c.length - 1];
  const back = n => c.length > n ? (last / c[c.length - 1 - n] - 1) * 100 : null;
  const hi = Math.max(...o.slice(-252).map(r => r[2]));
  const off = (last / hi - 1) * 100;
  const cells = [["1 month", back(21)], ["6 months", back(126)], ["1 year", back(252)]];
  return `<div class="pfacts">${cells.map(([k, v]) => `<div><span class="k">${k}</span><span class="v num ${cls(v)}">${isNum(v) ? pct(v, Math.abs(v) < 10 ? 1 : 0) : "—"}</span></div>`).join("")}
    <div><span class="k">Below 1-year high</span><span class="v num">${off >= -0.5 ? "at the high" : Math.abs(off).toFixed(Math.abs(off) < 10 ? 1 : 0) + "%"}</span></div></div>`;
}
function aiSays(sym) {
  const v = verdictBy[sym], pk = pickBy[sym], mr = MRS[sym], rows = [];
  if (v) rows.push([`AI check: ${VERDICT_WORD[v.verdict] || v.verdict}`, dateLabel(v.stamp), v.why, v.verdict === "BUY" ? "buy" : v.verdict === "SKIP" ? "risk" : "watch"]);
  if (pk) rows.push(["Weekly pick", dateLabel((D.ai_picks || {}).generated), pk.thesis, "ai"]);
  if (mr) rows.push([`AI rating ${mr.conviction}/5`, dateLabel(mr.date), mr.thesis, "ai"]);
  if (!rows.length) return "";
  return `<div class="card list-card"><div class="lc-head"><span class="blk-lab">What the AI says</span><button class="btn link" data-stab="news">Read it all →</button></div>
    ${rows.map(([k, d, t, c]) => `<button class="ai-row" data-stab="news"><span class="ai-k"><span class="chip sm ${c}">${esc(k)}</span><span class="faint">${esc(d)}</span></span><span class="ai-t">${esc(clip(plainAI(t), 160))}</span></button>`).join("")}</div>`;
}
function newsPeek(sym) {
  const items = newsItems(sym), real = items.filter(x => !x.routine);
  if (!items.length) return `<div class="ok-line"><span class="dot"></span>No news or filings matched this company in the last 30 days.</div>`;
  const head = `<div class="lc-head"><span class="blk-lab">Latest news</span><button class="btn link" data-stab="news">All ${items.length} →</button></div>`;
  if (!real.length) return `<div class="card list-card">${head}<div class="lc-body"><div class="muted" style="font-size:13px;padding:4px 0 8px">Only routine paperwork in the last 30 days (trading-window notices, certificates).</div></div></div>`;
  return `<div class="card list-card">${head}<div class="lc-body">${newsList(real.slice(0, 3))}</div></div>`;
}
function tabOverview(sym) {
  return `${briefBlock(sym)}${todoBox(sym)}${pennyCard(sym)}${scoreTiles(sym)}${priceFacts(sym)}${aiSays(sym)}${newsPeek(sym)}${headsFor(sym)}`;
}
function tabChart(sym, p) {
  const st = setupBy[sym], sp = st && st.plan && !st.plan.skip ? st.plan : null;
  return `<div><div class="chart-range">${["3M", "6M", "1Y"].map(k => `<button class="btn sm ${S.chartRange === k ? "primary" : ""}" data-range="${k}">${k}</button>`).join("")}
      <span class="muted" style="font-size:12px;margin-left:4px">50- and 150-day averages · dashed: alert, stop</span></div>
    <div class="chart-box" id="${p}-main"></div><div class="chart-box small" id="${p}-rs"></div>${chartWords(sym)}</div>
    ${sp ? fold("Exit plan", "how the position is sold", `<div class="memo">${exitWords(sp)}</div>`) : ""}`;
}
function tabScores(sym) {
  return `${scoreCard(sym)}${rowBy[sym] ? "" : mbCard(sym) || ""}`;
}
function tabBusiness(sym, p) {
  return `${briefBlock(sym, true)}${keyNumbers(sym)}${bizCharts(p)}
    <div class="link-row"><a class="btn sm" href="https://www.screener.in/company/${encodeURIComponent(sym)}/" target="_blank" rel="noopener">Screener.in ↗</a><a class="btn sm" href="https://www.nseindia.com/get-quotes/equity?symbol=${encodeURIComponent(sym)}" target="_blank" rel="noopener">NSE quote ↗</a></div>`;
}
/* News & AI: every section folds, with its one-line answer in the header;
   the news opens by default because it is what people come here for. */
function tabNews(sym) {
  const items = newsItems(sym), nm = newsMem[sym], d = (detailOf(sym) || {}).news || {};
  const v = verdictBy[sym], pk = pickBy[sym], mr = MRS[sym];
  const dl = (DEALS.rows90 || {})[sym] || [], dn = (DEALS.net90 || {})[sym];
  const nAlerts = (D.scorecard || []).filter(r => r.sym === sym).length;
  const tone = d.count ? `When last scored: ${num(d.stories)} ${d.stories === 1 ? "story" : "stories"} from ${num(d.count)} articles, ${toneWord(d.sentiment)} in tone.` : "";
  const parts = [];
  parts.push(fold("Latest news", items.length ? `${items.length} in the last 30 days` : "nothing matched in 30 days",
    (items.length ? newsList(items) : `<div class="muted" style="font-size:13px">No filings or headlines matched this company in the last 30 days. That is the reach of the archive, not proof that nothing was published.</div>`)
    + (tone ? `<div class="muted" style="font-size:12px;margin-top:8px">${esc(tone)}</div>` : ""), true));
  if (v) parts.push(fold("AI check", `${VERDICT_WORD[v.verdict] || v.verdict} · ${dateLabel(v.stamp)}`, aiCheckBody(v)));
  if (pk) parts.push(fold("Weekly pick", `${dateLabel((D.ai_picks || {}).generated)}${pk.conviction ? " · " + String(pk.conviction).toLowerCase() + " confidence" : ""}`, pickBody(pk)));
  if (mr) parts.push(fold("Company deep-dive", `AI rating ${mr.conviction}/5 · ${dateLabel(mr.date)}`, `<div style="margin-bottom:10px"><button class="btn sm" data-story="${esc(sym)}">Read the full note</button></div>${researchCard(sym)}`));
  if (!v && !pk && !mr) parts.push(`<div class="muted" style="font-size:13px">No AI research on ${esc(sym)} yet. The nightly AI check covers the top buy alerts, the weekly picks are 3–5 names, and the deep-dives cover the top multibagger candidates.</div>`);
  if (nm) parts.push(fold("Story memory, 90 days", `${nm.n_pos || 0} positive · ${nm.n_neg || 0} negative`, memoryBody(nm)));
  if (dl.length) parts.push(fold("Bulk and block deals", dn && isNum(dn.net) ? `net ${dn.net >= 0 ? "buying" : "selling"} ${inrShort(Math.abs(dn.net))} in 90 days` : `${dl.length} in 90 days`, dealsBody(dl)));
  parts.push(fold("Alert history", nAlerts ? nAlerts + " buy alert" + (nAlerts > 1 ? "s" : "") + " in the journal" : "never alerted", sheetHistory(sym)));
  return parts.join("");
}
/* a section that starts folded: the title and a one-line summary, open on click */
function fold(title, summary, body, open) {
  return `<details class="fold dsec"${open ? " open" : ""}><summary><span class="fold-t">${esc(title)}</span><span class="fold-s">${esc(summary)}</span></summary><div class="fold-b">${body}</div></details>`;
}
/* the chart in words, as one caption under the chart rather than a card that
   repeated the header chips and the to-do box */
function chartWords(sym) {
  const r = rowBy[sym] || {}, d = detailOf(sym) || {}, st = setupBy[sym];
  const bits = [r.tag ? stageWord(r.tag) : d.stage_name ? String(d.stage_name).replace("(advancing)", "(rising)") : "",
    isNum(d.tt_checks) && !convMoved(sym) ? d.tt_checks + " of 8 trend checks pass" : "",
    st ? "base ready, alert price " + px(st.pivot) : d.vcp ? "a base is forming" : "no base",
    st && isNum(st.atr_pct) ? "typical daily move " + st.atr_pct + "%" : ""].filter(Boolean);
  return bits.length ? `<div class="muted" style="font-size:12.5px;margin-top:8px">${bits.map(esc).join(" · ")}</div>` : "";
}
function keyNumbers(sym) {
  const r = rowBy[sym] || {};
  const cells = [["ROCE", isNum(r.roce) ? r.roce.toFixed(1) + "%" : null], ["P/E", isNum(r.pe) ? r.pe.toFixed(1) : null], ["Profit growth", isNum(r.pgttm) ? pct(r.pgttm, 0) : null],
    ["Market cap", isNum(r.mcap) ? "₹" + nf0.format(r.mcap) + " Cr" : null], ["Traded a day", isNum(r.turn) ? "₹" + r.turn.toFixed(1) + " Cr" : null], ["Type", r.arch ? esc(r.arch) : null]].filter(c => c[1] != null);
  return cells.length ? `<div class="card"><div class="card-head"><h3>Key numbers</h3><span class="hint">${r.fasof ? "results as read on " + esc(dateLabel(r.fasof)) + "; market cap and P/E at tonight's price" : "market cap and P/E at tonight's price"}</span></div><div class="grid grid-3" style="gap:10px">
      ${cells.map(([k, v]) => `<div class="plan-cell"><div class="k">${k}</div><div class="v" style="font-size:15px">${v}</div></div>`).join("")}</div></div>` : "";
}
function bizCharts(p) {
  return `<div class="mini-grid">
      <div class="card mini"><h4>Net profit <span>₹ Cr · quarterly</span></h4><div id="${p}-np"></div></div>
      <div class="card mini"><h4>Operating margin <span>% · quarterly</span></h4><div id="${p}-opm"></div></div>
      <div class="card mini"><h4>Borrowings <span>₹ Cr · yearly · falling means deleveraging</span></h4><div id="${p}-debt"></div></div>
      <div class="card mini"><h4>Who owns it <span>% held · quarterly</span></h4><div id="${p}-own"></div></div>
    </div>`;
}
function drawStockTab(sym, p, bucket) {
  const st = setupBy[sym], plan = planOf(sym), sp = st && st.plan && !st.plan.skip ? st.plan : null;
  // an old alert's stop is not a level anyone holds: only a live signal's
  const live = buySignals().some(a => a.sym === sym) || recentTriggers().some(a => a.sym === sym);
  const lines = { pivot: st ? st.pivot : null, stop: sp ? sp.stop : live && plan && !plan.skip ? plan.stop : null };
  if (S.sheetTab === "chart") drawCandles($("#" + p + "-main"), sym, Object.assign({ range: S.chartRange, bucket, rsBox: $("#" + p + "-rs") }, lines));
  if (S.sheetTab === "business") drawFundInto(sym, p);
}
function drawFundInto(sym, p) {
  const f = fundOf(sym);
  const put = (id, html) => { const el = $("#" + p + "-" + id); if (el) el.innerHTML = html; };
  if (!f) { ["np", "opm", "debt", "own"].forEach(id => put(id, `<div class="muted">No filings read for this stock.</div>`)); return; }
  const n1 = v => v.map(x => (x === "" || x == null) ? null : +x);
  put("np", (f.np || []).length ? bars(f.q_labels || [], n1(f.np)) : `<div class="muted">No quarterly data.</div>`);
  put("opm", (f.opm || []).length ? lines(f.q_labels || [], [{ l: "Operating margin", c: css("--info"), v: n1(f.opm) }]) : `<div class="muted">No margin data.</div>`);
  put("debt", (f.debt || []).length ? lines(f.bs_labels || [], [{ l: "Borrowings", c: css("--watch"), v: n1(f.debt) }], 90, " Cr") : `<div class="muted">No balance-sheet data.</div>`);
  put("own", (f.prom || []).length ? lines(f.sh_labels || [], [{ l: "Promoters", c: css("--info"), v: n1(f.prom || []) }, { l: "FII", c: css("--ai"), v: n1(f.fii || []) }, { l: "DII", c: css("--buy"), v: n1(f.dii || []) }]) : `<div class="muted">No shareholding data.</div>`);
}
function pennyRow(sym) { const P = lazy("penny") || D.penny; return P ? (P.rows || []).find(r => r.sym === sym) || null : null; }
function pennyCard(sym) {
  const r = pennyRow(sym); if (!r) return "";
  const m = MBS[sym], tier = PENNY_TIER(r), warn = (r.flags || []).map(pennyFlag);
  const head = tier === 2 ? `Failed the penny safety checks: ${esc(pennyFlag(String(r.vetowhy || "a red flag").split("; ")[0]))}.`
    : tier === 1 ? "On the penny list but not checked yet: screener.in had no readable company data for it, so the pledge, dilution and shell checks could not run. Treat it as unchecked."
    : "A penny stock that passed the safety checks: it trades enough to sell, is not under exchange surveillance, and its shares are not heavily pledged or diluted.";
  const mb = tier === 2 ? "" : m ? ` Multibagger score <b>${Math.round(m.score)}</b>, rank ${num(mbRank(sym))} of ${num(mbStats().all.length)}.` : " Too new or too thinly traded for the multibagger score.";
  return `<div class="todo ${tier === 2 ? "risk" : tier === 1 ? "watch" : "ghost"}"><div class="todo-head"><span class="todo-tag">Penny stock</span><span class="todo-text">${head}${mb} Keep it to 1% of your portfolio.</span></div>
    <div class="plan-grid"><div class="plan-cell"><div class="k">Traded a day</div><div class="v">${isNum(r.turn) ? "₹" + r.turn.toFixed(2) + " Cr" : "—"}</div></div>
      <div class="plan-cell"><div class="k">Most you could sell in a day</div><div class="v">${isNum(r.turn) ? inrShort(r.turn * 1e7 * 0.1) : "—"}</div></div>
      <div class="plan-cell"><div class="k">3 months</div><div class="v ${cls(r.run3m)}">${pct(r.run3m, 0)}</div></div>
      <div class="plan-cell"><div class="k">Warnings</div><div class="v" style="font-size:13px">${warn.length ? esc(warn.join("; ")) : "none"}</div></div></div></div>`;
}
function outsideDetail(sym) {
  const pc = pennyCard(sym), body = outsideDetail0(sym);
  if (!pc) return body;
  return /No data on this build/.test(body) ? pc + `<div class="dsec" style="display:flex;gap:10px;flex-wrap:wrap"><a class="btn sm" href="https://www.nseindia.com/get-quotes/equity?symbol=${encodeURIComponent(sym)}" target="_blank" rel="noopener">NSE quote ↗</a><a class="btn sm" href="https://www.screener.in/company/${encodeURIComponent(sym)}/" target="_blank" rel="noopener">Screener.in ↗</a><a class="btn sm" href="https://www.tradingview.com/chart/?symbol=NSE%3A${encodeURIComponent(sym)}" target="_blank" rel="noopener">Chart ↗</a></div>` : pc + body;
}
function outsideDetail0(sym) {
  const x = (RD.rows || []).find(r => r.sym === sym);
  if (!x && MBS[sym]) return `<div class="todo ai"><div class="todo-head"><span class="todo-tag">Research it</span><span class="todo-text">A multibagger candidate from the whole market, outside the nightly scan, so there's no chart or plan here yet.</span></div></div>
    <div class="dsec">${mbCard(sym)}</div>${MRS[sym] ? `<div class="dsec"><div class="dsec-title">Company deep-dive <button class="btn sm" data-story="${esc(sym)}" style="margin-left:8px;text-transform:none;letter-spacing:0">Read the full note</button></div>${researchCard(sym)}</div>` : ""}
    <div class="dsec" style="display:flex;gap:10px;flex-wrap:wrap"><a class="btn sm" href="https://www.screener.in/company/${encodeURIComponent(sym)}/" target="_blank" rel="noopener">Screener.in ↗</a><a class="btn sm" href="https://www.tradingview.com/chart/?symbol=NSE%3A${encodeURIComponent(sym)}" target="_blank" rel="noopener">Chart ↗</a></div>`;
  if (!x) return `<div class="empty" style="margin-top:14px">No data on this build for ${esc(sym)}.</div>`;
  return `<div class="todo ai"><div class="todo-head"><span class="todo-tag">Research it</span><span class="todo-text">A possible multibagger from the whole-market radar. It's outside the nightly scan, so there's no chart or buy plan here yet.</span></div>
      <div class="plan-grid"><div class="plan-cell"><div class="k">6 months</div><div class="v ${cls(x.ret_6m_pct)}">${pct(x.ret_6m_pct, 0)}</div></div><div class="plan-cell"><div class="k">12 months</div><div class="v ${cls(x.ret_12m_pct)}">${pct(x.ret_12m_pct, 0)}</div></div>
      <div class="plan-cell"><div class="k">From 52-week high</div><div class="v">${pct(x.off_52w_high_pct, 1)}</div></div><div class="plan-cell"><div class="k">Traded a day</div><div class="v">₹${num(x.traded_value_cr, 1)} Cr</div></div></div></div>
    <div class="dsec"><div class="dsec-title">Signals</div><div class="card">${Object.entries(x.signals || {}).map(([k, d]) => `<div class="lrow" style="cursor:default"><div>${radarChip(k, d)}<div class="meta">${esc(RADAR_TIP[k] || "")}</div></div><span class="muted num" style="font-size:12px">${esc(dateLabel(d))}</span></div>`).join("")}</div></div>
    ${MBS[sym] ? `<div class="dsec">${mbCard(sym)}</div>` : ""}
    ${MRS[sym] ? `<div class="dsec">${fold("Company deep-dive", "AI rating " + MRS[sym].conviction + "/5 · " + dateLabel(MRS[sym].date), `<div style="margin-bottom:10px"><button class="btn sm" data-story="${esc(sym)}">Read the full note</button></div>${researchCard(sym)}`)}</div>` : ""}
    <div class="dsec" style="display:flex;gap:10px;flex-wrap:wrap"><a class="btn sm" href="https://www.nseindia.com/get-quotes/equity?symbol=${encodeURIComponent(sym)}" target="_blank" rel="noopener">NSE quote ↗</a><a class="btn sm" href="https://www.screener.in/company/${encodeURIComponent(sym)}/" target="_blank" rel="noopener">Screener.in ↗</a><a class="btn sm" href="https://www.tradingview.com/chart/?symbol=NSE%3A${encodeURIComponent(sym)}" target="_blank" rel="noopener">Chart ↗</a></div>`;
}

/* the full-screen sheet: the same detail, opened from any list */
function openStock(sym, ctx, fromRoute) {
  if (!sym) return;
  sym = String(sym).toUpperCase();
  if (ctx) S.ctx = ctx;
  if (S.stock !== sym) S.sheetTab = "overview";
  S.stock = sym;
  if (!fromRoute) history.pushState(null, "", "#/stock/" + encodeURIComponent(sym));
  $("#scrim").classList.add("on");
  $("#sheet").classList.add("on");
  renderSheet();
  document.body.style.overflow = "hidden";
}
function closeSheet(silent) {
  const sh = $("#sheet");
  if (!sh.classList.contains("on")) return;
  sh.classList.remove("on");
  $("#scrim").classList.remove("on");
  document.body.style.overflow = "";
  S.stock = null;
  _sheetCharts.forEach(c => { try { c.remove(); } catch (e) { } });
  _sheetCharts.length = 0;
  if (!silent && /^#\/stock\//.test(location.hash)) history.back();
}
function stepStock(dlt) {
  const ctx = S.ctx || [], i = ctx.indexOf(S.stock);
  if (i < 0 || !ctx.length) return;
  const n = ctx[(i + dlt + ctx.length) % ctx.length];
  history.replaceState(null, "", "#/stock/" + encodeURIComponent(n));
  S.stock = n;
  renderSheet();
}
function renderSheet() {
  const sym = S.stock, ctx = S.ctx || [], idx = ctx.indexOf(sym);
  _sheetCharts.forEach(c => { try { c.remove(); } catch (e) { } });
  _sheetCharts.length = 0;
  const nav = {
    back: `<button class="icon-btn" id="shclose" aria-label="Close">${I.back}</button>`,
    right: idx >= 0 && ctx.length > 1 ? `<span class="sheet-nav"><button class="icon-btn" id="shprev" aria-label="Previous stock" data-tip="Previous (←)">${I.left}</button><button class="icon-btn" id="shnext" aria-label="Next stock" data-tip="Next (→)">${I.right}</button></span>` : "",
  };
  const has = hasDetail(sym);
  $("#sheet").innerHTML = `<div class="sheet-head">${stockHead(sym, nav)}${has ? stockTabs() : ""}</div>
    <div class="sheet-body" id="shbody"><div class="stab-body">${has ? stockTabBody(sym, "s") : briefBlock(sym) + outsideDetail(sym)}</div></div>`;
  if (has) drawStockTab(sym, "s", _sheetCharts);
}
/* =================================================================== EXPLORE */
const SCTABS = [["stocks", "All stocks"], ["multibaggers", "Multibaggers"], ["penny", "Penny"], ["themes", "Themes & market"]];
function pageScreener() {
  const tabs = SCTABS.filter(([k]) => k !== "penny" || lazy("penny") || D.penny);
  if (!tabs.some(t => t[0] === S.sc)) S.sc = "stocks";
  const body = { stocks: screenStocks, multibaggers: screenMultibaggers, penny: explorePenny, themes: screenThemes }[S.sc];
  return subtabs(tabs, S.sc, "data-sctab") + body();
}
function screenThemes() {
  return `<div class="page-intro">The market the system trades: small and mid caps, not only the NIFTY 50. Themes and industries are context; they change no trade.</div>
    <div style="margin-bottom:16px">${marketPulseCard()}</div>${researchThemes()}<div style="margin-top:16px">${fold("Universe map", "every watched stock as a square, strongest first", universeMap(ROWS))}</div>`;
}
/* ================================================================== RESEARCH */
/* ========================================================= MULTIBAGGER SCORE
   The rebuilt score (phase 2, PREREG_2026-09-29): only the factors that
   preceded Indian multibaggers in BOTH 2016-20 and 2021-26, each weighted by
   how much it raised the odds of tripling within a year. Drawn as four
   pillars plus a checklist: what the company has, and what it lacks. */
const FSHORT = { A1: "Growth", A2: "Operating leverage", A3: "Turnaround", A4: "Returns rising", A5: "Deleveraging", A6: "Capacity on stream",
  B1: "Cheap for its growth", B2: "Value (cash flow and book)", B3: "Small cap", C1: "Institutions arriving", C2: "Undiscovered", C3: "Institutions adding",
  C4: "Shareholders broadening", D1: "Promoter raising stake", D2: "Promoter holds 50%+", E1: "Delivery accumulation", E2: "Up-volume", E3: "Volume surge",
  F: "Price leader", Q1: "Quarterly surge", P: "Promoter buying" };
function fKey(name) { return name.startsWith("P ") ? "P" : name.startsWith("F ") ? "F" : name.slice(0, 2); }
function fShort(name) { return FSHORT[fKey(name)] || name; }
function mbTop(n) { return Object.entries(MBS).map(([sym, m]) => ({ sym, ...m })).sort((a, b) => b.score - a.score).slice(0, n); }
/* The multibagger score in words (user, 2026-10-14: "HFCL has 9/100, I don't
   know if it's right"). It is right: the score is the points of the
   ingredients present, out of 100 for all nine, and HFCL has one (price
   leader, 8.9 points). What was missing was the arithmetic and the scale. */
function mbStats() {
  if (mbStats._s) return mbStats._s;
  const all = Object.values(MBS).map(m => m.score).sort((a, b) => b - a);
  const total = Object.values(MBCFG).reduce((a, v) => a + v.weight, 0) || 1;
  return (mbStats._s = { all, total, max: all[0] || 0, top10: all[Math.floor(all.length * 0.1)] || 0, top25: all[Math.floor(all.length * 0.25)] || 0 });
}
function mbPoints(name) { return ((MBCFG[name] || {}).weight || 0) / mbStats().total * 100; }
function mbRank(sym) { const m = MBS[sym]; return m ? mbStats().all.findIndex(x => x <= m.score) + 1 : null; }
function mbExplain(sym) {
  const m = sym && MBS[sym], s = mbStats(), n = Object.keys(MBCFG).length;
  const how = `The score adds up the ingredients that came before past Indian multibaggers. Each is worth points by how much it raised the odds of tripling within a year; all ${n} together make 100.`;
  const scale = ` Across the ${num(s.all.length)} stocks that have any, the highest today is ${Math.round(s.max)} and the top 10% start at ${Math.round(s.top10)}.`;
  if (!m) return how + scale;
  const parts = (m.factors || []).map(f => `${fShort(f)} ${mbPoints(f).toFixed(1)}`).join(" + ");
  return how + ` ${sym} has ${m.factors.length}: ${parts} = ${Math.round(m.score)}, rank ${num(mbRank(sym))} of ${num(s.all.length)}.` + scale
    + " A low score is not a verdict on the company: it means the stock does not look like a typical multibagger. Larger, widely owned companies score low by design.";
}
function mbCard(sym, inFold) {
  const names = Object.keys(MBCFG);
  if (!names.length) return MBX.error ? `<div class="card"><div class="card-head"><h3>Multibagger score</h3><span class="chip sm risk">not computed</span></div>
    <div class="muted" style="font-size:13px">The nightly run could not compute it: ${esc(MBX.error)}</div></div>` : "";
  const m = MBS[sym], on = new Set((m || {}).factors || []);
  if (!m && !(RD.universe || []).includes(sym)) return `<div class="card"><div class="card-head"><h3>Multibagger score</h3><span class="chip sm ghost">not scored</span></div>
    <div class="muted" style="font-size:13px">Outside the ${num(MBX.universe)} liquid stocks the score covers (it needs a year of history and enough daily trading), so its ingredients were not checked.</div></div>`;
  const pil = {};
  names.forEach(n => { const v = MBCFG[n], p = v.pillar; pil[p] = pil[p] || { max: 0, got: 0 }; pil[p].max += v.weight; if (on.has(n)) pil[p].got += v.weight; });
  const order = ["Business inflection", "Room to re-rate", "Ownership", "Price and volume"].filter(p => pil[p]);
  const sc = m ? m.score : 0;
  return `<div class="card"><div class="card-head"><h3>${inFold ? "The proven ingredients" : "Multibagger score"}</h3><span class="chip sm" style="color:${scoreCol(sc)};border-color:${scoreCol(sc)}">${Math.round(sc)} / 100</span>${info(mbExplain(sym) + " Built only from factors that held in both 2016–20 and 2021–26. Tested as a 10-stock portfolio, the top 10% by this score made 27% a year over 2016–2026, against 17% for momentum alone and 14% for the market; promoter buying + momentum on its own made 32%. So use it to decide what to research, not what to buy.")}</div>
    <div class="mb-sum">${m ? `<b>${m.factors.length} of ${names.length}</b> ingredients · <b>${Math.round(sc)}</b> of 100 points · rank <b>${num(mbRank(sym))}</b> of ${num(mbStats().all.length)}. The top 10% start at ${Math.round(mbStats().top10)}.` : `None of the ${names.length} ingredients today, so no score.`}</div>
    <div class="sbars">${order.map(p => { const v = pil[p], pc = v.max ? v.got / v.max * 100 : 0, col = pc >= 50 ? "var(--buy)" : pc > 0 ? "var(--watch)" : "var(--faint)";
      return `<div class="sbar"><div class="top"><span>${esc(p)}</span><b style="color:${col}">${Math.round(pc)}%</b></div><div class="track"><i style="width:${pc}%;background:${col}"></i></div></div>`; }).join("")}</div>
    ${on.size ? `<div class="has-line"><span class="muted">Has:</span> ${[...on].map(n => `<span class="chip sm teal">${esc(fShort(n))}</span>`).join(" ")}</div>` : ""}
    <details class="more"><summary>All ${names.length} ingredients and what each is worth</summary><div class="flist">${names.sort((a, b) => MBCFG[b].weight - MBCFG[a].weight).map(n => { const hit = on.has(n);
      return `<div class="fitem ${hit ? "on" : ""}"><span class="fico">${hit ? "✓" : "·"}</span><div><div class="ft">${esc(fShort(n))} <span class="faint">${mbPoints(n).toFixed(1)} points · ${Math.exp(MBCFG[n].weight).toFixed(1)}× odds</span></div>${hit && m.evidence && m.evidence[n] ? `<div class="fn">${esc(m.evidence[n])}</div>` : ""}</div></div>`; }).join("")}</div></details>
    <div class="muted" style="font-size:11.5px;margin-top:10px">Scored ${esc(dateLabel(MBX.asof))} across ${num(MBX.universe)} liquid stocks. "Odds" is how much more often stocks with that ingredient tripled within a year than the average stock, in the weaker of the two halves tested.</div></div>`;
}
function ingredientsLine(m, n = 3) {
  const f = (m.factors || []).map(fShort);
  return f.slice(0, n).join(" · ") + (f.length > n ? ` · +${f.length - n} more` : "");
}
function mbBlock(list) {
  const mbBadge = m => `<div class="cvb teal"><b>${Math.round(m.score)}</b><span class="cvb-t">multibagger</span></div>`;
  return `<div class="slist">${list.map(m => { const scored = isNum((rowBy[m.sym] || {}).score);
    return stockCard(m.sym, { ctx: "mbtop", chips: (scored ? `<span class="chip sm teal">Multibagger ${Math.round(m.score)}</span>` : "") + convChip(m.sym), sub: esc(ingredientsLine(m)), right: scored ? null : mbBadge(m) }); }).join("")}</div>
    <div class="step-actions">${seeAll("screener", "multibaggers", "See all " + num(Object.keys(MBS).length))}<span class="muted" style="font-size:12px">Ideas to research, not buy signals.</span></div>`;
}
/* ============================================================ REPORT ANALYST
   What the weekly reading of each company's filings concluded
   (scripts/ai_multibagger.py, analyst/MULTIBAGGER_PROTOCOL.md): the concall
   and presentation read, guidance checked against delivery, broker and
   industry reports found, an SQGLP-style scorecard and a 1-5 conviction. */
const MR_LABEL = { size_runway: "Size and runway", business_quality: "Business quality", management: "Management",
  growth_visibility: "Growth visibility", longevity: "Longevity", valuation: "Valuation (room to re-rate)", red_flags: "Red flags (5 = none)" };
function convCol(c) { return c >= 4 ? "var(--buy)" : c >= 3 ? "var(--info)" : c >= 2 ? "var(--watch)" : "var(--risk)"; }
function convChip(sym) {
  const m = MRS[sym];
  if (!m || !isNum(+m.conviction)) return "";
  return `<span class="chip sm" style="color:${convCol(+m.conviction)};border-color:${convCol(+m.conviction)}" data-tip="${esc("AI rating from the weekly deep-dive, " + dateLabel(m.date) + ": " + clip(m.thesis, 220))}">AI rating ${esc(m.conviction)}/5</span>`;
}
function researchCard(sym) {
  const m = MRS[sym] || {}, sc = m.scores || {}, c = +m.conviction;
  const link = (u, t) => u && /^https?:/.test(u) ? `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(t)}</a>` : esc(t);
  return `<div class="card accent-ai">
    <div class="card-head"><h3>AI rating</h3><span class="chip" style="color:${convCol(c)};border-color:${convCol(c)};font-size:13px">${esc(m.conviction)} of 5</span>
      <span class="chip sm ghost">${esc(m.horizon || "")}</span>
      <span class="hint">read ${esc(dateLabel(m.date))}${m.concall ? " · " + link(m.transcript_url, m.concall + " concall") : ""}${m.ppt ? " · " + link(m.ppt_url, m.ppt + " presentation") : ""}</span></div>
    <div class="memo" style="margin-bottom:14px">${esc(m.thesis || "")}</div>
    <div class="grid grid-2" style="align-items:start;gap:20px">
      <div><div class="sbars">${Object.keys(MR_LABEL).filter(k => sc[k]).map(k => { const v = +sc[k].score, pctv = isNum(v) ? v / 5 * 100 : 0, col = isNum(v) ? (v >= 4 ? "var(--buy)" : v >= 3 ? "var(--info)" : v >= 2 ? "var(--watch)" : "var(--risk)") : "var(--faint)";
        return `<div class="sbar"><div class="top"><span>${esc(MR_LABEL[k])}</span><b style="color:${col}">${isNum(v) ? v + "/5" : "—"}</b></div><div class="track"><i style="width:${pctv}%;background:${col}"></i></div><div class="n">${esc(sc[k].why || "")}</div></div>`; }).join("")}</div></div>
      <div class="memo">
        ${(m.triggers || []).length ? `<h4>Growth triggers</h4><ul>${m.triggers.map(t => `<li><b>${esc(t.when || "")}</b> ${esc(t.what || "")} <span class="faint">(${esc(t.source || "")})</span></li>`).join("")}</ul>` : ""}
        ${m.guidance ? `<h4>Guidance</h4><p>${esc(m.guidance)}</p>` : ""}
        ${m.delivered_vs_guidance ? `<h4>Said versus done</h4><p>${esc(m.delivered_vs_guidance)}</p>` : ""}
        ${m.industry ? `<h4>Industry</h4><p>${esc(m.industry)}</p>` : ""}
      </div>
    </div>
    ${(m.analyst_views || []).length ? `<div class="dsec-title" style="margin-top:16px">Analyst reports</div><div class="table-wrap"><table class="t"><thead><tr><th>Broker</th><th>When</th><th>View</th><th>Target</th></tr></thead>
      <tbody>${m.analyst_views.map(a => `<tr style="cursor:default"><td>${link(a.url, a.broker || "")}</td><td class="num">${esc(a.date || "")}</td><td>${esc(a.view || "")}</td><td class="num">${esc(a.target || "")}</td></tr>`).join("")}</tbody></table></div>` : ""}
    <div class="grid grid-2" style="margin-top:14px;align-items:start;gap:20px"><div class="memo">${(m.risks || []).length ? `<h4>Risks</h4><ul>${m.risks.map(x => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}</div>
      <div class="memo">${m.change_my_mind ? `<h4>What would change the view</h4><p>${esc(m.change_my_mind)}</p>` : ""}</div></div>
    ${(m.sources || []).length ? `<details class="more" style="margin-top:8px"><summary>Sources (${m.sources.length})</summary><div class="memo"><ul>${m.sources.map(u => `<li>${link(u, u)}</li>`).join("")}</ul></div></details>` : ""}
    <div class="muted" style="font-size:11.5px;margin-top:8px">Research, not a trade instruction: entries, stops and sizes stay mechanical. Every read is logged and measured against what the stock does next.</div>
  </div>`;
}
function researchNewsAll() {
  const v = ["filings", "deals", "policy"].includes(S.newsView) ? S.newsView : "filings";
  const body = { filings: researchNews, deals: researchDeals, policy: researchPolicy }[v];
  return `<div class="toolbar"><div class="seg">${[["filings", "Filings & headlines"], ["deals", "Bulk & block deals"], ["policy", "Policy"]].map(([k, l]) => `<button data-newsview="${k}" class="${v === k ? "on" : ""}">${l}</button>`).join("")}</div></div>${body()}`;
}
const RTABS = [["deepdives", "Deep-dives"], ["checks", "Buy checks"], ["picks", "Weekly picks"], ["news", "News"]];
function pageResearch() {
  if (!RTABS.some(t => t[0] === S.research)) S.research = "deepdives";
  if (S.research === "deepdives" && S.story && MRS[S.story]) return storyPost(S.story);
  const body = { deepdives: pageStories, checks: researchAnalyst, picks: researchCommittee, news: researchNewsAll }[S.research];
  return `${subtabs(RTABS, S.research, "data-research")}
    ${body()}`;
}
/* =================================================================== STORIES
   The weekly AI deep-dives (scripts/ai_multibagger.py) as readable research
   notes on the multibagger candidates: the story, the founder, what could move
   it, what could go wrong, and how the price has done since it was written.
   Public by the user's choice (2026-10-09), so every post carries the
   disclaimer and the protocol forbids recommendation language. */
const STORY_NOTE = "A research note written by an AI from company filings, concall transcripts and public reports, and published automatically. It is not investment advice or a recommendation to buy or sell, and it can be wrong: check every fact before acting on it.";
function storyNow(sym) {
  const o = ohlcOf(sym) || [];
  return MBS[sym] && isNum(MBS[sym].close) ? MBS[sym].close : o.length ? o[o.length - 1][4] : (rowBy[sym] || {}).close;
}
function storyOf(sym) {
  const m = MRS[sym] || {}, now = storyNow(sym), p0 = +m.price;
  const words = [m.story, m.founder, m.thesis, m.industry, m.delivered_vs_guidance, ...(m.risks || [])].join(" ").split(/\s+/).length;
  // "since" starts with the first session after the note: it was written at the close before it
  return { sym, m, company: m.company || (rowBy[sym] || {}).company || sym, now, since: isNum(now) && p0 > 0 && String(priceSession() || "") >= String(m.date || "9") ? (now / p0 - 1) * 100 : null,
    headline: m.headline || m.company || (rowBy[sym] || {}).company || sym, mins: Math.max(2, Math.round(words / 200)) };
}
function storyKicker(st) {
  const m = st.m;
  return `<div class="kicker">AI deep-dive · ${esc(dateLabel(m.date))}${m.sector ? " · " + esc(m.sector) : ""}</div>`;
}
function storyStats(st) {
  const m = st.m, c = +m.conviction, mbNow = MBS[st.sym] ? MBS[st.sym].score : null;
  return `<span class="chip sm" style="color:${convCol(c)};border-color:${convCol(c)}" data-tip="How strongly the AI rates it as a multibagger candidate, 1 to 5">AI rating ${esc(m.conviction)}/5</span>
    ${m.horizon ? `<span class="chip sm ghost" data-tip="When the AI expects the story to play out, if it does.">${esc(m.horizon)}</span>` : ""}
    ${isNum(st.since) ? `<span class="num ${cls(st.since)}" data-tip="Price change since the note was written">${pct(st.since)} since</span>` : ""}
    ${isNum(mbNow) ? `<span class="muted" data-tip="The multibagger score today, out of 100">multibagger ${Math.round(mbNow)}</span>` : ""}
    <span class="faint">${st.mins} min read</span>`;
}
function pageStories() {
  const all = Object.keys(MRS).map(storyOf);
  if (!all.length) return `<div class="empty">No stories yet. Each week an AI reads the top multibagger candidates' concalls and reports, and writes each one up here.</div>`;
  const order = S.storyOrder || "new";
  all.sort(order === "conv" ? (a, b) => (+b.m.conviction || 0) - (+a.m.conviction || 0) || String(b.m.date).localeCompare(String(a.m.date))
    : (a, b) => String(b.m.date).localeCompare(String(a.m.date)) || (+b.m.conviction || 0) - (+a.m.conviction || 0));
  return `<div class="toolbar"><div class="seg">${[["new", "Newest"], ["conv", "Highest AI rating"]].map(([k, l]) => `<button data-storyorder="${k}" class="${order === k ? "on" : ""}">${l}</button>`).join("")}</div></div>
    <div class="page-intro">Notes on the companies the multibagger score ranks highest. Each week an AI reads their concalls, presentations and reports, and writes one up. ${info(STORY_NOTE)}</div>
    <div class="story-list">${all.map(st => `<article class="story-card" data-story="${esc(st.sym)}">
      ${storyKicker(st)}<h3>${esc(st.headline)}</h3>
      ${st.m.headline ? `<div class="story-co">${esc(st.company)} · ${esc(st.sym)}</div>` : `<div class="story-co">${esc(st.sym)}</div>`}
      <p class="dek">${esc(clip(st.m.thesis, 260))}</p>
      <div class="story-meta">${storyStats(st)}</div></article>`).join("")}</div>
    <div class="muted" style="font-size:12px;margin-top:14px">${esc(STORY_NOTE)}</div>`;
}
function storyPost(sym) {
  const st = storyOf(sym), m = st.m, sc = m.scores || {}, mb = MBS[sym];
  const link = (u, t) => u && /^https?:/.test(u) ? `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(t)}</a>` : esc(t);
  const paras = t => String(t || "").split(/\n\s*\n/).map(x => x.trim()).filter(Boolean).map(x => `<p>${esc(x)}</p>`).join("");
  const sec = (title, body) => body ? `<h2>${esc(title)}</h2>${body}` : "";
  const founder = m.founder ? paras(m.founder) : sc.management && sc.management.why ? `<p>${esc(sc.management.why)}</p><p class="faint">From the AI's management score (${esc(sc.management.score)}/5). Notes from the next weekly run on carry a fuller founder section.</p>` : "";
  return `<div class="post">
    <button class="btn sm" data-story="">${I.left}All deep-dives</button>
    ${storyKicker(st)}
    <h1>${esc(st.headline)}</h1>
    <div class="story-co">${m.headline ? esc(st.company) + " · " : ""}${esc(sym)}</div>
    <div class="post-facts">
      <div><div class="k">AI rating</div><div class="v" style="color:${convCol(+m.conviction)}">${esc(m.conviction)}/5</div><div class="s">${esc(m.horizon || "")}</div></div>
      <div><div class="k">Price</div><div class="v">${isNum(st.now) ? px(st.now) : "—"}</div><div class="s">${+m.price > 0 ? px(+m.price) + " when written" : "not recorded when written"}${isNum(st.since) ? ` · <span class="${cls(st.since)}">${pct(st.since)}</span>` : ""}</div></div>
      <div><div class="k">Multibagger score</div><div class="v">${mb ? Math.round(mb.score) : "—"}</div><div class="s">${isNum(+m.mb_score) && m.mb_score !== null ? Math.round(+m.mb_score) + " when written" : "today, out of 100"}</div></div>
      <div><div class="k">Read</div><div class="v">${st.mins} min</div><div class="s">${esc(dateLabel(m.date))}</div></div>
    </div>
    <div class="callout post-note">${esc(STORY_NOTE)}</div>
    <div class="post-body">
      ${m.story ? paras(m.story) : `<p class="lead">${esc(m.thesis || "")}</p>`}
      ${sec("Who runs it", founder)}
      ${sec("What could move it", (m.triggers || []).length ? `<ul>${m.triggers.map(t => `<li>${t.when ? `<b>${esc(t.when)}:</b> ` : ""}${esc(t.what || "")}${t.source ? ` <span class="faint">(${esc(t.source)})</span>` : ""}</li>`).join("")}</ul>` : "")}
      ${sec("What management promised, and what it delivered", (m.guidance ? `<p>${esc(m.guidance)}</p>` : "") + (m.delivered_vs_guidance ? `<p>${esc(m.delivered_vs_guidance)}</p>` : ""))}
      ${sec("The industry", m.industry ? `<p>${esc(m.industry)}</p>` : "")}
      ${sec("Why the system flagged it", mb ? `<ul class="checks">${mb.factors.map(n => `<li><b>${esc(fShort(n))}</b>${(mb.evidence || {})[n] ? ": " + esc(mb.evidence[n]) : ""}</li>`).join("")}</ul><p class="faint">The multibagger score today: ${Math.round(mb.score)} of 100, from the ingredients that preceded Indian multibaggers in both 2016–20 and 2021–26.</p>` : "")}
      ${sec("The AI's scorecard", Object.keys(MR_LABEL).some(k => sc[k]) ? `<div class="sbars">${Object.keys(MR_LABEL).filter(k => sc[k]).map(k => { const v = +sc[k].score, col = v >= 4 ? "var(--buy)" : v >= 3 ? "var(--info)" : v >= 2 ? "var(--watch)" : "var(--risk)";
        return `<div class="sbar"><div class="top"><span>${esc(MR_LABEL[k])}</span><b style="color:${col}">${isNum(v) ? v + "/5" : "—"}</b></div><div class="track"><i style="width:${isNum(v) ? v / 5 * 100 : 0}%;background:${col}"></i></div><div class="n" style="white-space:normal">${esc(sc[k].why || "")}</div></div>`; }).join("")}</div>` : "")}
      ${sec("What brokers say", (m.analyst_views || []).length ? `<ul>${m.analyst_views.map(a => `<li>${link(a.url, a.broker || "")}${a.date ? " (" + esc(a.date) + ")" : ""}: ${esc(a.view || "")}${a.target ? ", target " + esc(a.target) : ""}</li>`).join("")}</ul>` : "")}
      ${sec("What could go wrong", (m.risks || []).length ? `<ul>${m.risks.map(x => `<li>${esc(x)}</li>`).join("")}</ul>` : "")}
      ${sec("What would change the view", m.change_my_mind ? `<p>${esc(m.change_my_mind)}</p>` : "")}
      ${sec("Sources", `<ul class="sources">${m.transcript_url ? `<li>${link(m.transcript_url, (m.concall || "Latest") + " concall transcript (BSE)")}</li>` : ""}${m.ppt_url ? `<li>${link(m.ppt_url, (m.ppt || "Latest") + " investor presentation (BSE)")}</li>` : ""}${(m.sources || []).map(u => `<li>${link(u, u.replace(/^https?:\/\/(www\.)?/, "").slice(0, 90))}</li>`).join("")}</ul>`)}
    </div>
    <div class="callout post-note">${esc(STORY_NOTE)} Written by ${esc(m.model || "an AI model")} on ${esc(dateLabel(m.date))}.</div>
    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:14px"><button class="btn sm" data-sym="${esc(sym)}">Open the stock</button>
      <a class="btn sm" href="https://www.screener.in/company/${encodeURIComponent(sym)}/" target="_blank" rel="noopener">Screener.in ↗</a>
      <button class="btn sm" data-story="">${I.left}All deep-dives</button></div>
  </div>`;
}

/* =============================================================== PERFORMANCE
   Is the system working? Everything here runs by itself and asks nothing of
   you (user, 2026-09-28: "there is no action item for the user, why are we
   showing them"), so it lives on one page, away from the to-do list. */
const PTABS = [["overview", "Overview"], ["books", "Paper books"], ["gate", "Capital gate"], ["evidence", "Evidence"], ["log", "Signal log"], ["system", "System"]];
function pagePerformance() {
  if (!PTABS.some(t => t[0] === S.perf)) S.perf = "overview";
  const body = { overview: perfOverview, books: perfBooks, gate: recordGate, evidence: () => recordSignals() + `<div style="margin-top:22px">${fold("Backtests", "the rules run over 2020 to 2026 history", recordBacktest())}</div>`, log: recordLog, system: pageSystem }[S.perf];
  return `${subtabs(PTABS, S.perf, "data-perf")}
    ${S.perf === "system" ? "" : `<div class="page-intro">Everything here runs by itself on paper and needs nothing from you. It answers one question: is the system making money?</div>`}${body()}`;
}
function perfOverview() {
  const g = D.gate || {}, c = g.cohort || {}, req = g.required || {};
  const need = req.min_signals || 40, have = c.n_qualifying || 0;
  const es = (X.event_study || {}).by_status || [];
  const base = es.find(r => r.key === "AWAITING TRIGGER"), noBase = es.find(r => r.key === "NO VCP BASE");
  const B = books();
  return `<div class="grid grid-3" style="align-items:start">
    <div class="card"><div class="card-head"><h3>Capital gate</h3><span class="chip sm ${g.verdict === "PASS" ? "buy" : g.verdict === "FAIL" ? "risk" : "info"}">${esc(gateWord(g.verdict))}</span></div>
      <div class="big num">${num(have)}<span class="muted">/${num(need)}</span></div>${meter(have / need, "info")}
      <div class="muted" style="font-size:12.5px;margin-top:10px">No real money until ${num(need)} signals qualify${g.deadline ? ", by " + esc(dateLabel(g.deadline)) : ""}. <a href="#/performance/gate">The details</a></div>${isNum(c.expectancy_r) && isNum(req.expectancy_r) ? `<div class="muted" style="font-size:12.5px;margin-top:6px">So far the signals average ${c.expectancy_r >= 0 ? "a gain" : "a loss"} of <b class="${cls(c.expectancy_r)}">${Math.abs(c.expectancy_r * 100).toFixed(0)}%</b> of what each risked; the bar is a gain of ${(req.expectancy_r * 100).toFixed(0)}%.</div>` : ""}</div>
    <div class="card"><div class="card-head"><h3>Forward record</h3></div>
      ${base ? `<div class="big num ${cls(base.x40)}">${pct(base.x40)}</div><div class="muted" style="font-size:12.5px">How much alerts with a live base beat the market over 40 sessions; ${num(base.b40)}% of them did. Uptrend-only alerts: ${pct(noBase && noBase.x40)}. <a href="#/performance/evidence">The details</a></div>` : `<div class="muted">Not measured on this build.</div>`}</div>
    <div class="card"><div class="card-head"><h3>Paper books</h3><span class="right"><a href="#/performance/books">open</a></span></div>
      ${B.map(b => `<div class="lrow" data-book="${b.id}"><div><i class="bdot" style="background:var(${b.color})"></i><span class="sym">${esc(b.name)}</span><div class="meta">${b.started ? "since " + esc(dateLabel(b.started)) + (isNum(b.mid) ? " · market " + pct(b.mid) : "") : "starts " + esc(b.startsLabel)}</div></div><span class="num ${cls(b.ret)}">${b.started && isNum(b.ret) ? pct(b.ret) : "—"}</span></div>`).join("")}</div>
  </div>`;
}
function perfBooks() {
  const B = books();
  if (!B.some(b => b.id === S.book)) S.book = B[0].id;
  const live = B.filter(b => b.nav.length > 1);
  if (live.length) AFTER.push(() => drawBooks(live));
  const b = B.find(x => x.id === S.book);
  return `<div class="card flush"><div class="table-wrap"><table class="t" id="booktbl"><thead><tr><th>Book</th><th class="">Status</th><th class="r">Return</th><th class="r" data-tip="The MIDSMALL momentum ETF over the same dates: the bar each book is judged by.">ETF, same dates</th><th class="r">Holdings</th><th class="">Trend</th></tr></thead>
    <tbody>${B.map(x => `<tr data-book="${x.id}" class="${x.id === S.book ? "sel" : ""}">
      <td><div class="cell-sym"><span class="sym"><i class="bdot" style="background:var(${x.color})"></i>${esc(x.name)}</span><span class="co" style="max-width:420px">${esc(x.what)}</span></div></td>
      <td class="">${x.started ? `<span class="chip sm buy">live</span> <span class="muted" style="font-size:12px">since ${esc(dateLabel(x.started))}</span>` : `<span class="chip sm ghost">starts ${esc(x.startsLabel)}</span>`}</td>
      <td class="r num ${cls(x.ret)}">${x.started && isNum(x.ret) ? pct(x.ret) : "—"}</td>
      <td class="r num ${cls(x.mid)}">${isNum(x.mid) ? pct(x.mid) : "—"}</td>
      <td class="r num">${x.sleeve && x.sleeve.risk_on === false && !x.held ? `<span class="chip sm ghost" data-tip="The breadth exit is on: fewer than half of stocks are above their 200-day average, so this book holds cash until that recovers.">in cash</span>` : num(x.held) + (x.slots ? `<span class="faint">/${x.slots}</span>` : "")}</td>
      <td class="">${x.nav.length > 2 ? spark(x.nav.map(q => q[1]), 110, 26) : `<span class="faint">—</span>`}</td></tr>`).join("")}</tbody></table></div></div>
  ${live.length ? `<div class="card" style="margin-top:16px"><div class="card-head"><h3>Growth of ₹100</h3><span class="hint">each book from its own first day</span></div><div class="chart-box" id="bookchart" style="height:240px"></div></div>` : ""}
  <div class="toolbar" style="margin-top:22px"><div class="seg" style="flex-wrap:wrap">${B.map(x => `<button data-book="${x.id}" class="${x.id === S.book ? "on" : ""}"><i class="bdot" style="background:var(${x.color})"></i>${esc(x.name)}</button>`).join("")}</div></div>
  ${bookDetail(b)}`;
}

/* ==================================================================== events */
function setSheetTab(k) {
  S.sheetTab = k;
  if (S.stock && $("#sheet").classList.contains("on")) { renderSheet(); const b = $("#shbody"); if (b) b.scrollTop = 0; }
  else drawWatchDetail();
}
document.addEventListener("click", e => {
  const t = e.target;
  const st = t.closest("[data-stab]"); if (st) { setSheetTab(st.dataset.stab); return; }
  const sv = t.closest("[data-save]");
  if (sv) {
    const sym = sv.dataset.save, on = toggleSaved(sym);
    $$(`[data-save="${sym}"]`).forEach(b => { b.classList.toggle("on", on); b.setAttribute("aria-pressed", on); b.setAttribute("aria-label", on ? "Remove from saved stocks" : "Save this stock"); });
    toast(on ? `${sym} saved. Find it under Watchlist, Saved.` : `${sym} removed from saved stocks.`);
    if (S.page === "watchlist" && S.watch.tab === "saved" && !(S.stock && $("#sheet").classList.contains("on"))) renderPage();
    return;
  }
  const wc = t.closest("[data-welcome]");
  if (wc) { store("gs.welcomed", "1"); const w = $("#welcome"); if (w) w.remove(); return; }
  if (t.closest("#gcapset")) {
    const v = +String(($("#gcap") || {}).value || "").replace(/[^0-9]/g, "");
    if (v >= 10000) { store("gs.capital", String(v)); toast(`Plans are now sized for ${capWord()}.`); renderPage(); }
    else toast("Enter an amount of at least ₹10,000.");
    return;
  }
  if (t.closest("#gcapreset")) { try { localStorage.removeItem("gs.capital"); } catch (e) { } toast(`Plans are sized for ${capWord()} again.`); renderPage(); return; }
  const story = t.closest("[data-story]");
  if (story) { const s = story.dataset.story; location.hash = "#/research/deepdives" + (s ? "/" + encodeURIComponent(s) : ""); return; }
  const goEl = t.closest("[data-go]");
  if (goEl) {
    const id = goEl.dataset.go, sub = goEl.dataset.sub;
    if (id === "watchlist" && sub) { S.watch.tab = sub; S.watch.sel = null; }
    if (S.stock && $("#sheet").classList.contains("on")) closeSheet(true);
    go(id, sub);
    return;
  }
  if (t.closest("#railsearch") || t.closest("#searchbtn")) { openPalette(); return; }
  if (t.closest("#themebtn")) {
    const n = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = n; store("gs-theme", n); renderShell();
    if (S.stock) renderSheet(); else renderPage();
    return;
  }
  if (t.closest("#scrim") || t.closest("#shclose")) { closeSheet(); return; }
  if (t.closest("#shprev")) { stepStock(-1); return; }
  if (t.closest("#shnext")) { stepStock(1); return; }
  const ex = t.closest("[data-expand]"); if (ex) { ex.classList.toggle("clamp"); return; }
  const rg = t.closest("[data-range]");
  if (rg) { S.chartRange = rg.dataset.range; if (t.closest("#sheet")) renderSheet(); else drawWatchDetail(); return; }
  const pi = t.closest("[data-pi]"); if (pi) { palPick(+pi.dataset.pi); return; }
  if (t.closest("#pal") && !t.closest(".pal-box")) { closePalette(); return; }
  const ca = t.closest("[data-copy-alerts]");
  if (ca) {
    const list = (ca.dataset.copyAlerts === "home" ? homeAlerts().slice(0, 3) : watchItems("ready").map(i => i.s)).filter(s => s.pivot && s.plan && !s.plan.skip);
    copyText(alertText(list), `${list.length} alert${list.length === 1 ? "" : "s"} copied. Paste them into your broker's price alerts.`); return;
  }
  const c1 = t.closest("[data-copy-one]"); if (c1) { const s = setupBy[c1.dataset.copyOne]; if (s) copyText(alertText([s]), "Alert copied. Set it as a price alert in your broker's app."); return; }
  const wt = t.closest("[data-wtab]");
  if (wt) { S.watch.tab = S.sub = wt.dataset.wtab; S.watch.sel = null; S.watch.limit = 30; history.replaceState(null, "", "#/watchlist/" + S.watch.tab); renderPage(); return; }
  const ws = t.closest("[data-wsel]");
  if (ws) {
    const sym = ws.dataset.wsel;
    if (window.innerWidth <= 980) { openStock(sym, S.ctx); return; }
    S.watch.sel = sym;
    $$("#wllist .scard").forEach(r => r.classList.toggle("sel", r.dataset.wsel === sym));
    drawWatchDetail();
    return;
  }
  const sct = t.closest("[data-sctab]"); if (sct) { S.sc = S.sub = sct.dataset.sctab; history.replaceState(null, "", "#/screener/" + S.sc); renderPage(); return; }
  const bk = t.closest("[data-book]");
  if (bk) { S.book = bk.dataset.book; S.perf = "books"; history.replaceState(null, "", "#/performance/books"); renderPage(); return; }
  const pf = t.closest("[data-perf]"); if (pf) { S.perf = S.sub = pf.dataset.perf; history.replaceState(null, "", "#/performance/" + S.perf); renderPage(); return; }
  const so = t.closest("[data-storyorder]"); if (so) { S.storyOrder = so.dataset.storyorder; renderPage(); return; }
  const rs = t.closest("[data-research]"); if (rs) { S.research = S.sub = rs.dataset.research; S.story = null; history.replaceState(null, "", "#/research/" + S.research); renderPage(); return; }
  const nv = t.closest("[data-newsview]"); if (nv) { S.newsView = nv.dataset.newsview; renderPage(); return; }
  if (t.closest("#sfilter") || t.closest("#sdone")) { S.screener.open = !S.screener.open; renderPage(); return; }
  if (t.closest("#sreset")) { Object.assign(S.screener, { view: "all", ind: "", tier: "", hideVeto: false, limit: 150 }); renderPage(); return; }
  const uf = t.closest("[data-unfilter]");
  if (uf) { const k = uf.dataset.unfilter; if (k === "view") S.screener.view = "all"; if (k === "ind") S.screener.ind = ""; if (k === "tier") S.screener.tier = ""; if (k === "veto") S.screener.hideVeto = false; renderPage(); return; }
  const sview = t.closest("[data-sview]"); if (sview) { S.screener.view = sview.dataset.sview; S.screener.limit = 150; renderPage(); return; }
  const sort = t.closest("[data-sort]"); if (sort) { const k = sort.dataset.sort; if (S.screener.sort === k) S.screener.dir *= -1; else { S.screener.sort = k; S.screener.dir = ["sym", "tag", "tier", "ind"].includes(k) ? 1 : -1; } renderPage(); return; }
  const ms = t.closest("[data-mbsort]"); if (ms) { const k = ms.dataset.mbsort; if (S.mb.sort === k) S.mb.dir *= -1; else { S.mb.sort = k; S.mb.dir = -1; } renderPage(); return; }
  if (t.closest("#smore")) { S.screener.limit += 200; renderPage(); return; }
  if (t.closest("#wmore")) { S.watch.limit = (S.watch.limit || 30) + 30; renderPage(); return; }
  if (t.closest("#mbmore")) { S.mb.limit += 200; renderPage(); return; }
  const pa = t.closest("[data-parm]"); if (pa) { S.penny.arm = pa.dataset.parm; renderPage(); return; }
  const run = t.closest("[data-run]");
  if (run) {
    fetch("/api/run/" + run.dataset.run, { method: "POST" }).then(r => r.json()).then(j => { toast(j.error || ("Started " + j.started)); setTimeout(probeRunPanel, 600); }).catch(() => toast("Run panel unavailable"));
    return;
  }
  const symEl = t.closest("[data-sym]");
  if (symEl && !t.closest("a")) {
    const row = symEl.closest("[data-ctx]");
    const ctx = row ? $$("[data-ctx='" + row.dataset.ctx + "']").map(r => r.dataset.sym || r.dataset.wsel) : null;
    openStock(symEl.dataset.sym, ctx);
  }
});
function refocus(id) { const i = $("#" + id); if (i) { i.focus(); i.setSelectionRange(i.value.length, i.value.length); } }
document.addEventListener("input", e => {
  const t = e.target;
  if (t.id === "palq") { palSearch(t.value); return; }
  if (t.id === "sq") { S.screener.q = t.value; S.screener.limit = 150; debounce(() => { renderPage(); refocus("sq"); }, 180); return; }
  if (t.id === "mq") { S.mb.q = t.value; S.mb.limit = 150; debounce(() => { renderPage(); refocus("mq"); }, 180); return; }
  if (t.id === "pq") { S.penny.q = t.value; debounce(() => { renderPage(); refocus("pq"); }, 180); }
});
document.addEventListener("change", e => {
  const t = e.target;
  if (t.id === "sind") { S.screener.ind = t.value; renderPage(); }
  if (t.id === "stier") { S.screener.tier = t.value; renderPage(); }
  if (t.id === "sveto") { S.screener.hideVeto = t.checked; renderPage(); }
  if (t.id === "pveto") { S.penny.showVeto = t.checked; renderPage(); }
});
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
  if (S.page === "watchlist" && ["ArrowDown", "ArrowUp", "j", "k", "Enter"].includes(e.key)) {
    const list = S.ctx || [];
    if (!list.length) return;
    e.preventDefault();
    if (e.key === "Enter") { if (S.watch.sel) openStock(S.watch.sel, list); return; }
    const i = Math.max(0, list.indexOf(S.watch.sel));
    const nx = list[Math.max(0, Math.min(list.length - 1, i + ((e.key === "ArrowDown" || e.key === "j") ? 1 : -1)))];
    S.watch.sel = nx;
    $$("#wllist .scard").forEach(r => r.classList.toggle("sel", r.dataset.wsel === nx));
    const r = $(`#wllist .scard[data-wsel="${nx}"]`); if (r) r.scrollIntoView({ block: "nearest" });
    drawWatchDetail();
    return;
  }
  const n = parseInt(e.key, 10);
  if (n >= 1 && n <= PAGES.length && !e.ctrlKey && !e.metaKey && !e.altKey) go(PAGES[n - 1].id);
});
window.addEventListener("hashchange", onRoute);
window.addEventListener("popstate", () => { if (!/^#\/stock\//.test(location.hash)) closeSheet(true); });

/* ====================================================================== boot */
onRoute();
