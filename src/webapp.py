"""FastAPI web server: statik sayt + /api (Bybit + siqnal)."""
import os
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import config
from src.bybit import fetch_tickers, fetch_kline
from src.indicators import add_indicators
from src.strategy import analyze
from src.tactics import tactics_breakdown

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
    res["symbol"] = sym
    res["display"] = sym[:-4] + "/USDT" if sym.endswith("USDT") else sym
    res["timeframe"] = timeframe
    return res


@app.get("/")
def index():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))


if os.path.isdir(WEB_DIR):
    app.mount("/web", StaticFiles(directory=WEB_DIR), name="web")
