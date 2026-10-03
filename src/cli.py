"""Terminal girisi: python -m src.cli --symbol BTC/USDT --timeframe 1h"""
import argparse
import json
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import config
from src.data import fetch_ohlcv
from src.indicators import add_indicators
from src.strategy import analyze


def run_one(symbol: str, timeframe: str, limit: int) -> dict:
    df = fetch_ohlcv(symbol, timeframe, limit, config.EXCHANGE)
    df = add_indicators(df, config.EMA_FAST, config.EMA_SLOW,
                        config.RSI_PERIOD, config.ATR_PERIOD)
    res = analyze(df, config.EMA_FAST, config.EMA_SLOW)
    res.update({"symbol": symbol, "timeframe": timeframe, "exchange": config.EXCHANGE})
    return res


def main():
    p = argparse.ArgumentParser(description="Kripto siqnal/analiz")
    p.add_argument("--symbol", default=",".join(config.SYMBOLS),
                   help="Vergüllə: BTC/USDT,ETH/USDT")
    p.add_argument("--timeframe", default=config.TIMEFRAME)
    p.add_argument("--limit", type=int, default=config.LIMIT)
    p.add_argument("--json", action="store_true", help="JSON çıxış")
    a = p.parse_args()

    symbols = [s.strip() for s in a.symbol.split(",") if s.strip()]
    results = [run_one(s, a.timeframe, a.limit) for s in symbols]

    if a.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    for r in results:
        print(f"\n=== {r['symbol']} {r['timeframe']} @ {r['price']} ===")
        print(f"Siqnal: {r['signal']} | Skor: {r['score']} | Inam: {r['confidence']}%")
        print(f"RSI: {r['rsi']} | ATR: {r['atr']} ({r['atr_pct']}%) | Stop mesafe (~1.5xATR): {r['suggested_stop_dist']}")
        print("Sebebler:")
        for line in r["reasons"]:
            print(f"  - {line}")


if __name__ == "__main__":
    main()
