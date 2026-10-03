"""EMA / RSI / MACD / ATR — saf pandas ilə, əlavə TA kitabxanasız."""
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    out = 100 - (100 / (1 + rs))
    return out.fillna(50.0)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def add_indicators(df: pd.DataFrame, ema_fast: int = 20, ema_slow: int = 50,
                   rsi_period: int = 14, atr_period: int = 14) -> pd.DataFrame:
    out = df.copy()
    out[f"ema{ema_fast}"] = ema(out["close"], ema_fast)
    out[f"ema{ema_slow}"] = ema(out["close"], ema_slow)
    out["rsi"] = rsi(out["close"], rsi_period)
    m, s, h = macd(out["close"])
    out["macd"], out["macd_signal"], out["macd_hist"] = m, s, h
    out["atr"] = atr(out, atr_period)
    out["vol_sma20"] = out["volume"].rolling(20).mean()
    return out
