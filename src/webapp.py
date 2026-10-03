"""FastAPI web server: statik sayt + /api (Bybit + siqnal)."""
import os
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import config
from src.bybit import fetch_tickers, fetch_kline, fetch_oi
from src.indicators import add_indicators
from src.strategy import analyze
from src.tactics import tactics_breakdown, extra_tactics

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
    df = add_indicators(df, config.EMA_FAST, config.EMA_SLOW,
                        config.RSI_PERIOD, config.ATR_PERIOD)
    res = analyze(df, config.EMA_FAST, config.EMA_SLOW)
    res["tactics"] = tactics_breakdown(df, config.EMA_FAST, config.EMA_SLOW)
    try:
        oi = fetch_oi(sym, timeframe, 30)
    except Exception:
        oi = None
    res["tactics"] += extra_tactics(df, config.EMA_FAST, config.EMA_SLOW, oi)
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
        # Evvelki ayin max/min-i (hedef xetleri). Esas df-de tam ay yoxdursa 1h-dan 1000 bar cek.
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


@app.get("/")
def index():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))


if os.path.isdir(WEB_DIR):
    app.mount("/web", StaticFiles(directory=WEB_DIR), name="web")
