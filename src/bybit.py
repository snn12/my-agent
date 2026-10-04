"""Bybit public API — key lazim deyil."""
import time

import requests

BASE = "https://api.bybit.com"

TF_TO_BYBIT = {
    "15m": "15",
    "1h": "60",
    "4h": "240",
    "1D": "D",
}

TF_TO_OI = {
    "15m": "15min",
    "1h": "1h",
    "4h": "4h",
    "1D": "D",
}


def to_bybit(symbol: str) -> str:
    """BTC/USDT -> BTCUSDT"""
    return symbol.replace("/", "").upper()


def _get(url, params, tries: int = 4):
    """10006 rate-limitde gozle + tekrar."""
    last = None
    for i in range(tries):
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        if data.get("retCode") == 10006:
            last = data
            time.sleep(2 * (i + 1))
            continue
        return data
    raise RuntimeError(f"Bybit limit xetasi: {last}")


def to_display(bybit_symbol: str) -> str:
    s = bybit_symbol.upper()
    if s.endswith("USDT"):
        return s[:-4] + "/USDT"
    return s


def fetch_tickers(category: str = "linear", limit: int = 1000):
    """Butun USDT lineer tickerler. Dovriyyeye gore siralanir."""
    url = f"{BASE}/v5/market/tickers"
    out = []
    cursor = ""
    while len(out) < limit:
        params = {"category": category, "limit": 1000}
        if cursor:
            params["cursor"] = cursor
        data = _get(url, params)
        if data.get("retCode") != 0:
            raise RuntimeError(f"Bybit xetasi: {data}")
        page = data["result"]["list"]
        # Yalniz USDT ile bitenler
        page = [t for t in page if t["symbol"].endswith("USDT")]
        out.extend(page)
        cursor = data["result"].get("nextPageCursor", "")
        if not cursor or not page:
            break
    # Dovriyyeye gore sirala, ilk `limit`
    out.sort(key=lambda t: float(t.get("turnover24h", 0) or 0), reverse=True)
    norm = []
    for t in out[:limit]:
        try:
            price = float(t["lastPrice"])
        except Exception:
            continue
        norm.append({
            "symbol": to_display(t["symbol"]),
            "bybit": t["symbol"],
            "price": price,
            "change24h": float(t.get("price24hPcnt", 0) or 0) * 100,
            "volume24h": float(t.get("volume24h", 0) or 0),
            "turnover24h": float(t.get("turnover24h", 0) or 0),
        })
    return norm


def fetch_kline(symbol: str, timeframe: str = "1h", limit: int = 200, category: str = "linear"):
    """Kline -> OHLCV DataFrame (kohneden yeniye)."""
    import pandas as pd
    interval = TF_TO_BYBIT.get(timeframe, "60")
    url = f"{BASE}/v5/market/kline"
    params = {"category": category, "symbol": to_bybit(symbol),
              "interval": interval, "limit": min(limit, 1000)}
    data = _get(url, params)
    if data.get("retCode") != 0:
        raise RuntimeError(f"Bybit kline xetasi: {data}")
    rows = data["result"]["list"]
    rows = list(reversed(rows))  # Bybit yenini evvel verir
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume", "turnover"])
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    df["ts"] = df["ts"].astype(int)
    df["datetime"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df[["ts", "open", "high", "low", "close", "volume", "datetime"]]


def fetch_oi(symbol: str, timeframe: str = "1h", limit: int = 30):
    """Open Interest (kohne -> yeni). Derivativler ucun."""
    url = f"{BASE}/v5/market/open-interest"
    params = {"category": "linear", "symbol": to_bybit(symbol),
              "intervalTime": TF_TO_OI.get(timeframe, "1h"),
              "limit": min(limit, 200)}
    data = _get(url, params)
    if data.get("retCode") != 0:
        raise RuntimeError(f"Bybit OI xetasi: {data}")
    rows = list(reversed(data["result"]["list"]))
    return [float(x["openInterest"]) for x in rows]


def fetch_funding(symbol: str, limit: int = 10):
    """Son funding rateler (kohne -> yeni). Musbet = longlar odeyir."""
    url = f"{BASE}/v5/market/funding/history"
    params = {"category": "linear", "symbol": to_bybit(symbol), "limit": min(limit, 200)}
    data = _get(url, params)
    if data.get("retCode") != 0:
        raise RuntimeError(f"Bybit funding xetasi: {data}")
    rows = list(reversed(data["result"]["list"]))
    return [float(x["fundingRate"]) for x in rows]
