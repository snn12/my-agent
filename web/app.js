// Sadə SPA: siyahı + coin səhifəsi. Hər 2 dəqiqədən bir yenilənir.
const S = { items: [], prev: {}, tf: "1h", route: location.hash || "#/" };
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
  // novbeti polling ucun cari qiymetler prev olur
  setTimeout(() => { for (const t of S.items) S.prev[t.bybit] = t.price; }, 1000);
}

function coinCard(t) {
  const cls = dirCls(t.bybit, t.price);
  return `<div class="coin">
    <h3><a href="#/coin/${t.bybit}" style="color:#fff">${t.symbol}</a></h3>
    <div class="p ${cls}">${fmt(t.price)}</div>
    <div class="meta">24s: <span class="${t.change24h >= 0 ? "up" : "down"}">${t.change24h.toFixed(2)}%</span></div>
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
  if (q) items = items.filter(t => t.bybit.includes(q));
  $("count").textContent = items.length + " cutluk";
  $("listTitle").textContent = S.route === "#/top" ? "Top 50" : "Cutlukler";
  $("grid").innerHTML = items.slice(0, 300).map(coinCard).join("");
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
  $("listView").hidden = true; $("aboutView").hidden = true; $("tacticsView").hidden = true; $("coinView").hidden = false;
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
      $("levels").innerHTML =
        `Giris: <b>${fmt(L.entry)}</b> (ATR ${L.atr})<br>` +
        `<span class="up">LONG</span> → SL <b class="down">${fmt(L.long.sl)}</b> · TP1 <b class="up">${fmt(L.long.tp1)}</b> · TP2 <b class="up">${fmt(L.long.tp2)}</b><br>` +
        `<span class="down">SHORT</span> → SL <b class="down">${fmt(L.short.sl)}</b> · TP1 <b class="up">${fmt(L.short.tp1)}</b> · TP2 <b class="up">${fmt(L.short.tp2)}</b><br>` +
        `<span class="muted">Son 50 bar: max ${fmt(L.swing_high_50)} / min ${fmt(L.swing_low_50)}</span>`;
    } else { $("levels").textContent = "hesablanmadi"; }
  } catch (e) { $("coinPrice").textContent = "xeta: " + e; }
}

function setCoinTitle(symbol, tf, price, cls) {
  if (price === undefined) {
    $("coinTitle").textContent = symbol + " / " + tf;
  } else {
    $("coinTitle").innerHTML = `${symbol} / ${tf} — <span class="${cls || ""}">${fmt(price)}</span>`;
  }
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

function router() {
  S.route = location.hash || "#/";
  $("aboutView").hidden = true; $("coinView").hidden = true;
  $("tacticsView").hidden = true; $("listView").hidden = false;
  if (S.route.startsWith("#/coin/")) openCoin(S.route.split("/")[2]);
  else if (S.route === "#/about") { $("listView").hidden = true; $("aboutView").hidden = false; }
  else if (S.route === "#/tactics") { $("listView").hidden = true; $("tacticsView").hidden = false; renderTactics(); }
  else render();
}

$("burger").onclick = () => $("side").classList.add("open");
$("closeSide").onclick = () => $("side").classList.remove("open");
$("back").onclick = () => location.hash = "#/";
$("search").oninput = render;
document.querySelectorAll("[data-tf]").forEach(b => b.onclick = () => {
  document.querySelectorAll("[data-tf]").forEach(x => x.classList.remove("on"));
  b.classList.add("on"); S.tf = b.dataset.tf; router();
});
window.addEventListener("hashchange", router);
loadTickers(); setInterval(loadTickers, 120000); // her 2 deq
router();
