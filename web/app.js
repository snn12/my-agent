// Sadə SPA: siyahı + coin səhifəsi. Hər 2 dəqiqədən bir yenilənir.
const S = { items: [], prev: {}, tf: "1h", route: location.hash || "#/", filter: null, scan: null };
const $ = (id) => document.getElementById(id);
const fmt = (n) => n >= 1000 ? n.toLocaleString("en-US", {maximumFractionDigits: 2}) : String(Math.round(n * 10000) / 10000);

function dirCls(sym, price) {
  const p = S.prev[sym];
  if (p === undefined) return "";
  if (price > p) return "up";
  if (price < p) return "down";
  return "";
}

async function loadTickers() {
  const r = await fetch("/api/tickers?limit=1000");
  const j = await r.json();
  // evvelki qiymetleri yadda saxla (reng ucun)
  const prev = {};
  for (const t of j.items) prev[t.bybit] = t.price;
  if (S.items.length) {
    for (const t of S.items) S.prev[t.bybit] = S.prev[t.bybit] ?? t.price;
    for (const t of j.items) { if (S.items.find(x => x.bybit === t.bybit)) S.prev[t.bybit] = S.items.find(x => x.bybit === t.bybit).price; }
  }
  S.items = j.items;
  render();
  autoScan();
  // novbeti polling ucun cari qiymetler prev olur
  setTimeout(() => { for (const t of S.items) S.prev[t.bybit] = t.price; }, 1000);
}

function coinCard(t) {
  const cls = dirCls(t.bybit, t.price);
  const fs = t._fs || (S.filter && S.filter.map[t.bybit]) || (S.scan && S.scan.map[t.bybit]);
  const fline = fs ? `<div class="meta"><b>${fs.nb}/${fs.n} BUY · ${fs.ns}/${fs.n} SELL</b> — ${fs.signal} ${fs.conf}%</div>` : "";
  return `<div class="coin">
    <h3><a href="#/coin/${t.bybit}" style="color:#fff">${t.symbol}</a></h3>
    <div class="p ${cls}">${fmt(t.price)}</div>
    <div class="meta">24s: <span class="${t.change24h >= 0 ? "up" : "down"}">${t.change24h.toFixed(2)}%</span></div>
    ${fline}
    <div style="margin-top:8px;display:flex;gap:6px">
      <button class="morebtn" data-more="${t.bybit}">More: taktikalar</button>
      <a href="#/coin/${t.bybit}"><button class="morebtn">Aç →</button></a>
    </div>
    <div class="reasons" id="mini-${t.bybit}" hidden></div>
  </div>`;
}

function render() {
  const q = $("search").value.trim().toUpperCase().replace("/", "");
  let items = S.items;
  if (S.route === "#/top") items = items.slice(0, 50);
  if (S.filter) items = items.filter(t => S.filter.list.includes(t.bybit));
  if (q) items = items.filter(t => t.bybit.includes(q));
  // 3 bolme: SELL / BUY / NEYTRAL + gozleyenler
  const sell = [], buy = [], ney = [], wait = [];
  for (const t of items) {
    const fs = (S.filter && S.filter.map[t.bybit]) || (S.scan && S.scan.map[t.bybit]);
    t._fs = fs || null;
    if (!fs) { wait.push(t); continue; }
    if (fs.signal === "SHORT") sell.push(t);
    else if (fs.signal === "LONG") buy.push(t);
    else ney.push(t);
  }
  sell.sort((a, b) => b._fs.ns - a._fs.ns || b._fs.conf - a._fs.conf);
  buy.sort((a, b) => b._fs.nb - a._fs.nb || b._fs.conf - a._fs.conf);
  ney.sort((a, b) => ((b._fs.n - b._fs.nb - b._fs.ns) - (a._fs.n - a._fs.nb - a._fs.ns)));
  $("count").textContent = items.length + " cutluk";
  $("listTitle").textContent = S.route === "#/top" ? "Top 50" : "Cutlukler";
  $("gridSell").innerHTML = sell.map(coinCard).join("");
  $("gridBuy").innerHTML = buy.map(coinCard).join("");
  $("gridNey").innerHTML = ney.map(coinCard).join("");
  $("gridWait").innerHTML = wait.slice(0, 200).map(coinCard).join("");
  $("cSell").textContent = sell.length ? `(${sell.length})` : "";
  $("cBuy").textContent = buy.length ? `(${buy.length})` : "";
  $("cNey").textContent = ney.length ? `(${ney.length})` : "";
  $("cWait").textContent = wait.length ? `(${wait.length})` : "";
  $("secWait").style.display = wait.length ? "" : "none";
  // marquee: ad + qiymet, yavas (css 170s). Reng: once canli istiqamet, yoxdursa 24s deyisimi.
  const mitems = S.items.slice(0, 80).map(t => {
    const c = dirCls(t.bybit, t.price) || (t.change24h >= 0 ? "up" : "down");
    return `<span>${t.symbol} <b class="${c}">${fmt(t.price)}</b></span>`;
  }).join("");
  $("marquee").innerHTML = mitems + mitems;
  document.querySelectorAll("[data-more]").forEach(b => b.onclick = async (e) => {
    e.stopPropagation();
    const box = $("mini-" + b.dataset.more);
    if (!box.hidden) { box.hidden = true; return; }
    box.textContent = "yuklenir..."; box.hidden = false;
    const s = await (await fetch(`/api/signal?symbol=${b.dataset.more}&timeframe=${S.tf}`)).json();
    const n = s.tactics.length || 1;
    const nb = s.tactics.filter(t => t.signal === "BUY").length;
    const ns = s.tactics.filter(t => t.signal === "SELL").length;
    box.innerHTML = `<b>${nb}/${n} BUY · ${ns}/${n} SELL</b><br>` +
      s.tactics.map(t => `${t.name}: <b>${t.signal}</b> (${t.detail})`).join("<br>") +
      `<br>Umumi: <b>${s.signal}</b> ${s.confidence}%`;
  });
}

async function openCoin(bybit) {
  $("listView").hidden = true; $("aboutView").hidden = true; $("tacticsView").hidden = true; $("journalView").hidden = true; $("coinView").hidden = false;
  const t = S.items.find(x => x.bybit === bybit);
  setCoinTitle(t ? t.symbol : bybit, S.tf);
  $("coinInfo").textContent = (t ? t.symbol : bybit) + " — Bybit linear (USDT) cutluyu. Dovriye: " +
    (t ? fmt(t.turnover24h) + " USDT" : "-");
  renderCtx(bybit);
  $("coinPrice").textContent = "yuklenir..."; $("coinSignal").textContent = "";
  $("tactics").innerHTML = ""; $("coinReasons").hidden = true;
  $("levels").textContent = "yuklenir...";
  try {
    const s = await (await fetch(`/api/signal?symbol=${bybit}&timeframe=${S.tf}`)).json();
    const cls = dirCls(bybit, s.price);
    setCoinTitle(t ? t.symbol : bybit, S.tf, s.price, cls);
    $("coinPrice").textContent = fmt(s.price);
    $("coinPrice").className = cls;
    $("coinChg").textContent = `RSI ${s.rsi} | ATR ${s.atr} | stop ~${s.suggested_stop_dist}`;
    const n = s.tactics.length || 1;
    const nb = s.tactics.filter(t => t.signal === "BUY").length;
    const ns = s.tactics.filter(t => t.signal === "SELL").length;
    const nh = s.tactics.filter(t => t.signal !== "BUY" && t.signal !== "SELL").length;
    $("tacSummary").innerHTML =
      `<span class="up">${nb}/${n} BUY</span> · <span class="down">${ns}/${n} SELL</span> · <span class="muted">${nh}/${n} HOLD</span>`;
    const bcls = s.signal === "LONG" ? "b-long" : (s.signal === "SHORT" ? "b-short" : "b-neytral");
    $("coinSignal").innerHTML = `<span class="badge ${bcls}">${s.signal}</span> skor ${s.score} | inam ${s.confidence}%`;
    $("tactics").innerHTML = s.tactics.map(x => {
      const c = x.signal === "BUY" ? "b-buy" : (x.signal === "SELL" ? "b-sell" : "b-hold");
      return `<div class="tac"><b>${x.name}</b><span class="badge ${c}">${x.signal}</span><div class="muted">${x.detail}</div></div>`;
    }).join("");
    const btn = document.createElement("button");
    btn.className = "morebtn"; btn.textContent = "More: tam sebebler";
    btn.onclick = () => { const r = $("coinReasons"); r.hidden = !r.hidden; r.innerHTML = s.reasons.map(x => "- " + x).join("<br>"); };
    $("coinSignal").appendChild(document.createElement("br")); $("coinSignal").appendChild(btn);
    if (s.levels) {
      const L = s.levels;
      const f2 = (v) => (v === null || v === undefined) ? "-" : fmt(v);
      $("levels").innerHTML =
        `Giris: <b>${fmt(L.entry)}</b> (ATR ${L.atr})<br>` +
        `<span class="up">LONG</span> → SL <b class="down">${fmt(L.long.sl)}</b> · TP ATR <b class="up">${fmt(L.long.tp1)}/${fmt(L.long.tp2)}</b><br>` +
        `&nbsp;&nbsp;TP swing <b class="up">${f2(L.long.tp_swing)}</b> · TP fib1.618 <b class="up">${f2(L.long.tp_fib1618)}</b> · TP 2R <b class="up">${f2(L.long.tp_2R)}</b><br>` +
        `<span class="down">SHORT</span> → SL <b class="down">${fmt(L.short.sl)}</b> · TP ATR <b class="up">${fmt(L.short.tp1)}/${fmt(L.short.tp2)}</b><br>` +
        `&nbsp;&nbsp;TP swing <b class="up">${f2(L.short.tp_swing)}</b> · TP fib1.618 <b class="up">${f2(L.short.tp_fib1618)}</b> · TP 2R <b class="up">${f2(L.short.tp_2R)}</b><br>` +
        `<span class="muted">Swing: ${f2(L.swing_low)} / ${f2(L.swing_high)} · Son 50 bar: max ${fmt(L.swing_high_50)} / min ${fmt(L.swing_low_50)}</span>` +
        (L.prev_month_high !== undefined
          ? `<br><span class="muted">Evvelki ay: max ${fmt(L.prev_month_high)} / min ${fmt(L.prev_month_low)}</span>` : "");
      renderRisk(L);
    } else { $("levels").textContent = "hesablanmadi"; }
    if (s.session) {
      $("coinChg").textContent += ` | Sessiya ${s.session.utc} UTC: ${s.session.in_overlap ? "aktiv (London/NY)" : "passiv"}`;
    }
  } catch (e) { $("coinPrice").textContent = "xeta: " + e; }
}

function setCoinTitle(symbol, tf, price, cls) {
  if (price === undefined) {
    $("coinTitle").textContent = symbol + " / " + tf;
  } else {
    $("coinTitle").innerHTML = `${symbol} / ${tf} — <span class="${cls || ""}">${fmt(price)}</span>`;
  }
}

function renderRisk(L) {
  const draw = () => {
    const bal = parseFloat($("rkBal").value) || 0;
    const pct = parseFloat($("rkPct").value) || 0;
    const risk = bal * pct / 100;
    const dL = Math.abs(L.entry - L.long.sl), dS = Math.abs(L.entry - L.short.sl);
    const sizeL = dL ? risk / dL : 0, sizeS = dS ? risk / dS : 0;
    $("rkOut").innerHTML =
      `Risk: <b>${fmt(risk)} USDT</b> (${pct}%)<br>` +
      `LONG ölçü: <b>${sizeL.toFixed(5)}</b> coin (~${fmt(sizeL * L.entry)} USDT) · ` +
      `SHORT ölçü: <b>${sizeS.toFixed(5)}</b> coin (~${fmt(sizeS * L.entry)} USDT)`;
  };
  $("rkBal").oninput = draw; $("rkPct").oninput = draw;
  draw();
}

function renderCtx(sym) {
  const k = "ctx-" + sym;
  $("ctxBox").value = localStorage.getItem(k) || "";
  $("saveCtx").onclick = () => { localStorage.setItem(k, $("ctxBox").value); alert("Saxlanildi. Sonra AI bu konteksti istifade edecek."); };
}

const DEFAULT_TACTICS = [
  {name: "EMA", desc: "EMA20 vs EMA50: yuxaridirsa BUY, asagidirsa SELL"},
  {name: "TREND", desc: "Qiymet EMA20 ustundeyse BUY, altindadirsa SELL"},
  {name: "RSI", desc: "<30 BUY, >70 SELL, >55 BUY, <45 SELL, eks halda HOLD"},
  {name: "MACD", desc: "Histogram musbetse BUY, menfidirse SELL, kesisme guclu siqnal"},
  {name: "P/D", desc: "Son 50 bar range: <40% discount = BUY zonasi, >60% premium = SELL zonasi"},
  {name: "FVG", desc: "Son 10 barda mitigasiya olunmamis gap: bullish = BUY, bearish = SELL"},
  {name: "ENGULF", desc: "Engulfing + sweep: bullish engulf + low sweep = BUY (tersi SELL)"},
  {name: "TURTLE", desc: "Evvelki max/min sweep + geri baglanis = eksine giris (fade)"},
  {name: "RETEST", desc: "EMA zonasina 2+ toxunus: trend istiqametinde giris hazirligi"},
  {name: "AMD", desc: "Range + kenar sweep + genis govde = trap istiqametinin eksine"},
  {name: "POC", desc: "En cox volumlu seviye: VAH ustu BUY, VAL alti SELL"},
  {name: "OI", desc: "Qiymet + OI birlikde qalxirsa yeni longlar = BUY (tersi SELL)"},
];

function renderTactics() {
  const custom = JSON.parse(localStorage.getItem("custom-tactics") || "[]");
  const all = DEFAULT_TACTICS.concat(custom);
  $("tacticsList").innerHTML = all.map(t =>
    `<div class="coin"><h3>${t.name}</h3><div class="meta">${t.desc}</div></div>`).join("");
  $("tacAdd").onclick = () => {
    const n = $("tacName").value.trim().toUpperCase().slice(0, 12);
    const d = $("tacDesc").value.trim();
    if (!n || !d) return;
    custom.push({name: n, desc: d});
    localStorage.setItem("custom-tactics", JSON.stringify(custom));
    $("tacName").value = ""; $("tacDesc").value = "";
    renderTactics();
  };
}

function getTrades() { return JSON.parse(localStorage.getItem("trades") || "[]"); }
function saveTrades(a) { localStorage.setItem("trades", JSON.stringify(a)); }

function renderJournal() {
  const arr = getTrades();
  const closed = arr.filter(t => t.exit !== "" && t.exit !== null);
  let w = 0, pnl = 0;
  for (const t of closed) {
    const p = (parseFloat(t.exit) - parseFloat(t.entry)) * parseFloat(t.size) * (t.side === "LONG" ? 1 : -1);
    t._pnl = p; pnl += p;
    if (p > 0) w++;
  }
  const wr = closed.length ? (w / closed.length * 100).toFixed(1) : "-";
  $("jStats").innerHTML = closed.length
    ? `Treyd: <b>${closed.length}</b> · Winrate: <b>${wr}%</b> · Net: <b class="${pnl >= 0 ? "up" : "down"}">${pnl.toFixed(2)} USDT</b>`
    : "Hələ treyd yoxdur.";
  // TILT: son 3 bagli zererdirse ve ya son 60 deqiqede 5+ treyd
  const warns = [];
  const last3 = closed.slice(-3);
  if (last3.length === 3 && last3.every(t => t._pnl <= 0)) warns.push("⚠️ TILT WARNING: son 3 treyd zərərlidir — fasilə ver!");
  const now = Date.now(), recent = arr.filter(t => now - t.ts < 3600000).length;
  if (recent >= 5) warns.push(`⚠️ Overtrade: son 1 saatda ${recent} treyd — yavaşla!`);
  $("tiltBox").innerHTML = warns.map(x => `<div class="card"><b class="down">${x}</b></div>`).join("");
  $("jList").innerHTML = arr.length ? arr.slice().reverse().map((t, i) =>
    `<p>• ${t.sym} ${t.side} ${t.entry}→${t.exit || "?"} <span class="${(t._pnl ?? 0) >= 0 ? "up" : "down"}">${t._pnl !== undefined ? t._pnl.toFixed(2) : ""}</span> ${t.note || ""} <button class="morebtn" data-del="${arr.length - 1 - i}">sil</button></p>`
  ).join("") : `<p class="muted">Boşdur.</p>`;
  document.querySelectorAll("[data-del]").forEach(b => b.onclick = () => {
    const a = getTrades(); a.splice(+b.dataset.del, 1); saveTrades(a); renderJournal();
  });
  $("jAdd").onclick = () => {
    const a = getTrades();
    a.push({ sym: $("jSym").value.trim().toUpperCase() || "BTCUSDT", side: $("jSide").value,
      entry: $("jEntry").value, exit: $("jExit").value, size: parseFloat($("jSize").value) || 0,
      note: $("jNote").value.trim(), ts: Date.now() });
    saveTrades(a); $("jEntry").value = ""; $("jExit").value = ""; $("jNote").value = "";
    renderJournal();
  };
}

function router() {
  S.route = location.hash || "#/";
  $("aboutView").hidden = true; $("coinView").hidden = true;
  $("tacticsView").hidden = true; $("journalView").hidden = true; $("listView").hidden = false;
  if (S.route.startsWith("#/coin/")) openCoin(S.route.split("/")[2]);
  else if (S.route === "#/about") { $("listView").hidden = true; $("aboutView").hidden = false; }
  else if (S.route === "#/tactics") { $("listView").hidden = true; $("tacticsView").hidden = false; renderTactics(); }
  else if (S.route === "#/journal") { $("listView").hidden = true; $("journalView").hidden = false; renderJournal(); }
  else render();
}

$("burger").onclick = () => $("side").classList.add("open");
$("closeSide").onclick = () => $("side").classList.remove("open");
$("back").onclick = () => location.hash = "#/";
$("search").oninput = render;
$("fGo").onclick = applyTacticFilter;
$("fClear").onclick = () => { S.filter = null; $("fStatus").textContent = ""; render(); };

async function scanCoins(cands, statusPrefix) {
  if (!S.scan) S.scan = { map: {} };
  const CHUNK = 5;
  let done = 0;
  for (let i = 0; i < cands.length; i += CHUNK) {
    const chunk = cands.slice(i, i + CHUNK);
    const res = await Promise.all(chunk.map(t =>
      fetch(`/api/signal?symbol=${t.bybit}&timeframe=${S.tf}`).then(r => r.json()).catch(() => null)));
    res.forEach((s, k) => {
      done++;
      if (!s || !s.tactics) return;
      const n = s.tactics.length || 1;
      const nb = s.tactics.filter(x => x.signal === "BUY").length;
      const ns = s.tactics.filter(x => x.signal === "SELL").length;
      S.scan.map[cands[i + k].bybit] = { nb, ns, n, signal: s.signal, conf: s.confidence };
    });
    $("fStatus").textContent = `${statusPrefix}: ${done}/${cands.length} (${S.tf})...`;
    render();
  }
  return S.scan.map;
}

function autoScan() {
  if (S.scan || !S.items.length) return; // bir defe
  S.scan = { map: {} };
  scanCoins(S.items.slice(0, 50), "Avto-skan").then(() => {
    $("fStatus").textContent = `Avto-skan bitdi: top 50 (${S.tf}). Daraltmaq üçün Filterlə.`;
  });
}

async function applyTacticFilter() {
  const minBuy = +$("fBuy").value, minSell = +$("fSell").value;
  const sig = $("fSig").value, top = +$("fTop").value;
  const cands = S.items.slice(0, top);
  if (top >= 500) $("fStatus").textContent = `Top ${top}: bir nece deqiqe cheke biler, gozle...`;
  $("fGo").disabled = true;
  await scanCoins(cands, "Yoxlanilir");
  $("fGo").disabled = false;
  const list = cands.filter(t => {
    const m = S.scan.map[t.bybit];
    if (!m) return false;
    return m.nb >= minBuy && m.ns >= minSell && (!sig || m.signal === sig);
  }).map(t => t.bybit);
  S.filter = { minBuy, minSell, sig, top, list, map: S.scan.map };
  $("fStatus").textContent = `Netice: ${list.length} cutluk (min ${minBuy} BUY, min ${minSell} SELL${sig ? ", " + sig : ""}, top ${top}, ${S.tf})`;
  render();
}
document.querySelectorAll("[data-tf]").forEach(b => b.onclick = () => {
  document.querySelectorAll("[data-tf]").forEach(x => x.classList.remove("on"));
  b.classList.add("on"); S.tf = b.dataset.tf;
  S.scan = null; S.filter = null; $("fStatus").textContent = "";
  router(); autoScan();
});
window.addEventListener("hashchange", router);
for (const id of ["fBuy", "fSell"]) {
  const el = $(id), cur = el.value;
  el.innerHTML = "";
  for (let i = 0; i <= 12; i++) {
    const o = document.createElement("option");
    o.value = String(i); o.textContent = String(i);
    el.appendChild(o);
  }
  el.value = cur;
}
loadTickers(); setInterval(loadTickers, 120000); // her 2 deq
router();
