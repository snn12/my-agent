"""FastAPI web server: statik sayt + /api (Bybit + siqnal)."""
import os
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import config
from src.bybit import fetch_tickers, fetch_kline, fetch_oi, fetch_funding
from src.indicators import add_indicators
from src.strategy import analyze
from src.tactics import tactics_breakdown, extra_tactics, precise_levels
from src.news import get_news

app = FastAPI(title="my-agent trading")

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/tickers")
def tickers(limit: int = Query(default=1000, le=1000), q: str = ""):
    items = fetch_tickers(limit=limit)
    if q:
        ql = q.strip().upper().replace("/", "")
        items = [t for t in items if ql in t["bybit"].upper()]
    return {"count": len(items), "items": items}


@app.get("/api/signal")
def signal(symbol: str = "BTCUSDT", timeframe: str = "1h", limit: int = 200):
    sym = symbol.replace("/", "").upper()
    df = fetch_kline(sym, timeframe, limit)
    if df is None or len(df) < 60:
        raise HTTPException(status_code=404, detail=f"{sym} üçün kifayət data yoxdur (söhbət siyahıda olmaya bilər)")
    df = add_indicators(df, config.EMA_FAST, config.EMA_SLOW,
                        config.RSI_PERIOD, config.ATR_PERIOD)
    res = analyze(df, config.EMA_FAST, config.EMA_SLOW)
    res["tactics"] = tactics_breakdown(df, config.EMA_FAST, config.EMA_SLOW)
    try:
        oi = fetch_oi(sym, timeframe, 30)
    except Exception:
        oi = None
    try:
        funding = fetch_funding(sym, 10)
    except Exception:
        funding = None
    res["tactics"] += extra_tactics(df, config.EMA_FAST, config.EMA_SLOW, oi, funding)
    res["symbol"] = sym
    res["display"] = sym[:-4] + "/USDT" if sym.endswith("USDT") else sym
    res["timeframe"] = timeframe
    from datetime import datetime, timezone
    now_utc = datetime.now(timezone.utc)
    h = now_utc.hour + now_utc.minute / 60.0
    res["session"] = {"in_overlap": 12.0 <= h < 17.0, "utc": now_utc.strftime("%H:%M")}
    # TP/SL seviyeleri: giris = son baglanis, ATR + son 50 bar min/max
    try:
        entry = float(df["close"].iloc[-1])
        atr_v = float(df["atr"].iloc[-1])
        win = df.tail(50)
        sh = float(win["high"].max())
        slw = float(win["low"].min())
        prec = 5 if entry < 1 else (3 if entry < 100 else 2)
        lv = {
            "entry": round(entry, prec),
            "atr": round(atr_v, prec),
            "swing_high_50": round(sh, prec),
            "swing_low_50": round(slw, prec),
            "long": {
                "sl": round(entry - 1.5 * atr_v, prec),
                "tp1": round(entry + 1.0 * atr_v, prec),
                "tp2": round(entry + 2.0 * atr_v, prec),
            },
            "short": {
                "sl": round(entry + 1.5 * atr_v, prec),
                "tp1": round(entry - 1.0 * atr_v, prec),
                "tp2": round(entry - 2.0 * atr_v, prec),
            },
        }
        try:
            pl = precise_levels(df, entry, atr_v, prec)
            lv["swing_high"] = pl["swing_high"]
            lv["swing_low"] = pl["swing_low"]
            lv["long"].update(pl["long"])
            lv["short"].update(pl["short"])
        except Exception:
            pass
        try:
            d2 = df.copy()
            d2["ym"] = d2["datetime"].dt.strftime("%Y-%m")
            months = list(dict.fromkeys(d2["ym"]))
            if len(months) >= 2:
                pm = d2[d2["ym"] == months[-2]]
                lv["prev_month_high"] = round(float(pm["high"].max()), prec)
                lv["prev_month_low"] = round(float(pm["low"].min()), prec)
            else:
                hdf = fetch_kline(sym, "1h", 1000)
                hdf["ym"] = hdf["datetime"].dt.strftime("%Y-%m")
                hm = list(dict.fromkeys(hdf["ym"]))
                if len(hm) >= 2:
                    pm = hdf[hdf["ym"] == hm[-2]]
                    lv["prev_month_high"] = round(float(pm["high"].max()), prec)
                    lv["prev_month_low"] = round(float(pm["low"].min()), prec)
        except Exception:
            pass
        res["levels"] = lv
    except Exception:
        res["levels"] = None
    return res


@app.get("/api/backtest")
def backtest(symbol: str = "BTCUSDT", timeframe: str = "1h", limit: int = 400,
             sl_mult: float = 1.5, tp_mult: float = 3.0, max_hold: int = 50):
    """Her taktika: tarixde siqnal verdiyi yerde gir, SL/TP ile cix. OI/FUND tarixce olmadigindan yoxdur."""
    sym = symbol.replace("/", "").upper()
    results, n = run_backtest(sym, timeframe, min(limit, 1000), sl_mult, tp_mult, max_hold)
    return {"symbol": sym, "timeframe": timeframe, "bars": n,
            "note": "OI/FUND tarixce seriyasi olmadigindan backtestde yoxdur",
            "results": results}


_COMBO_CACHE: dict = {}
_COMBO_TTL = 6 * 3600


@app.get("/api/combo")
def combo(symbol: str = "BTCUSDT", timeframe: str = "1h", limit: int = 400):
    """En yaxsilarin birliyi: backtestde musbet netR verenlerin cekili sesi."""
    import time
    sym = symbol.replace("/", "").upper()
    key = (sym, timeframe)
    now = time.time()
    hit = _COMBO_CACHE.get(key)
    if hit and now - hit["ts"] < _COMBO_TTL:
        weights = hit["weights"]
    else:
        results, _ = run_backtest(sym, timeframe, min(limit, 1000))
        weights = {r["name"]: r["netR"] for r in results if r["netR"] > 0 and r["trades"] >= 5}
        _COMBO_CACHE[key] = {"ts": now, "weights": weights}
    cur = signal(symbol=sym, timeframe=timeframe, limit=200)
    b = s_ = 0.0
    parts = []
    for t in cur.get("tactics", []):
        w = weights.get(t["name"], 0.0)
        if w <= 0:
            continue
        if t["signal"] == "BUY":
            b += w
        elif t["signal"] == "SELL":
            s_ += w
        parts.append({"name": t["name"], "signal": t["signal"], "weight": round(w, 1)})
    verdict = "NEYTRAL"
    if b > s_ * 1.2:
        verdict = "LONG"
    elif s_ > b * 1.2:
        verdict = "SHORT"
    return {"symbol": sym, "timeframe": timeframe, "verdict": verdict,
            "buyScore": round(b, 1), "sellScore": round(s_, 1),
            "used": sorted(parts, key=lambda x: x["weight"], reverse=True),
            "cached": bool(hit and now - hit["ts"] < _COMBO_TTL)}


def run_backtest(sym, timeframe, limit, sl_mult=1.5, tp_mult=3.0, max_hold=50):
    df = fetch_kline(sym, timeframe, limit)
    df = add_indicators(df, config.EMA_FAST, config.EMA_SLOW,
                        config.RSI_PERIOD, config.ATR_PERIOD)
    opens = df["open"].to_numpy()
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    atrs = df["atr"].to_numpy()
    n = len(df)
    stats: dict = {}
    for i in range(60, n - 1):
        sub = df.iloc[:i + 1]
        try:
            sigs = tactics_breakdown(sub, config.EMA_FAST, config.EMA_SLOW) + \
                extra_tactics(sub, config.EMA_FAST, config.EMA_SLOW)
        except Exception:
            continue
        atr_v = float(atrs[i])
        if not atr_v or atr_v != atr_v:
            continue
        entry = float(opens[i + 1])
        for s in sigs:
            if s["signal"] not in ("BUY", "SELL"):
                continue
            d = 1 if s["signal"] == "BUY" else -1
            sl = entry - d * sl_mult * atr_v
            tp = entry + d * tp_mult * atr_v
            risk = abs(entry - sl)
            r = 0.0
            for j in range(i + 1, min(i + 1 + max_hold, n)):
                if d == 1:
                    hit_sl = lows[j] <= sl
                    hit_tp = highs[j] >= tp
                else:
                    hit_sl = highs[j] >= sl
                    hit_tp = lows[j] <= tp
                if hit_sl and hit_tp:
                    r = -1.0
                    break
                if hit_sl:
                    r = -1.0
                    break
                if hit_tp:
                    r = tp_mult / sl_mult
                    break
            else:
                jj = min(i + max_hold, n - 1)
                r = ((closes[jj] - entry) * d) / risk if risk else 0.0
            st = stats.setdefault(s["name"], {"trades": 0, "wins": 0, "gw": 0.0, "gl": 0.0})
            st["trades"] += 1
            if r > 0:
                st["wins"] += 1
                st["gw"] += r
            else:
                st["gl"] += -r
    out = []
    for name, st in stats.items():
        t = st["trades"]
        out.append({
            "name": name,
            "trades": t,
            "winrate": round(st["wins"] / t * 100, 1) if t else 0,
            "netR": round(st["gw"] - st["gl"], 1),
            "profitFactor": round(st["gw"] / st["gl"], 2) if st["gl"] > 0 else None,
        })
    out.sort(key=lambda x: x["netR"], reverse=True)
    return out, n


@app.get("/api/klines")
def klines(symbol: str = "BTCUSDT", timeframe: str = "1h", limit: int = 200):
    """Qrafik ucun: OHLC + EMA/BB/VWAP. NaN -> null."""
    import math
    sym = symbol.replace("/", "").upper()
    df = fetch_kline(sym, timeframe, min(limit, 500))
    if df is None or len(df) < 30:
        raise HTTPException(status_code=404, detail=f"{sym} üçün data yoxdur")
    df = add_indicators(df, config.EMA_FAST, config.EMA_SLOW,
                        config.RSI_PERIOD, config.ATR_PERIOD)
    rows = []
    for _, r in df.iterrows():
        def clean(v):
            try:
                f = float(v)
                return f if f == f else None
            except Exception:
                return None
        rows.append({"t": int(r["ts"]), "o": float(r["open"]), "h": float(r["high"]),
                     "l": float(r["low"]), "c": float(r["close"]), "v": float(r["volume"]),
                     "ema20": clean(r.get("ema20")), "ema50": clean(r.get("ema50")),
                     "bbu": clean(r.get("bb_upper")), "bbl": clean(r.get("bb_lower")),
                     "vwap": clean(r.get("vwap"))})
    return {"symbol": sym, "timeframe": timeframe, "rows": rows}


@app.get("/api/news")
def news(limit: int = 40):
    items = get_news(min(limit, 60))
    return {"count": len(items), "items": items}


@app.get("/")
def index():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))


if os.path.isdir(WEB_DIR):
    app.mount("/web", StaticFiles(directory=WEB_DIR), name="web")
