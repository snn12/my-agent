"""Mərkəzi konfiq. .env varsa oxuyur, yoxdursa default işləyir."""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def _get(name: str, default: str) -> str:
    return os.getenv(name, default)


EXCHANGE = _get("EXCHANGE", "binance")
SYMBOLS = [s.strip() for s in _get("SYMBOLS", "BTC/USDT").split(",") if s.strip()]
TIMEFRAME = _get("TIMEFRAME", "1h")
LIMIT = int(_get("LIMIT", "200"))

EMA_FAST = int(_get("EMA_FAST", "20"))
EMA_SLOW = int(_get("EMA_SLOW", "50"))
RSI_PERIOD = int(_get("RSI_PERIOD", "14"))
ATR_PERIOD = int(_get("ATR_PERIOD", "14"))

DRY_RUN = _get("DRY_RUN", "true").lower() in ("1", "true", "yes")
