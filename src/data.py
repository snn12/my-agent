"""Birjadan OHLCV çəkmə. Hələlik yalnız public data, API key lazım deyil."""
import ccxt
import pandas as pd


def get_exchange(name: str = "binance"):
    cls = getattr(ccxt, name)
    ex = cls({"enableRateLimit": True})
    return ex


def fetch_ohlcv(symbol: str, timeframe: str = "1h", limit: int = 200,
                exchange_name: str = "binance") -> pd.DataFrame:
    ex = get_exchange(exchange_name)
    raw = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(raw, columns=["ts", "open", "high", "low", "close", "volume"])
    df["datetime"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df
