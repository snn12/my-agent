# my-agent — Kripto Siqnal/Analiz Botu (MVP)

Bu səhifə (söhbət) botun özü deyil — botu burada kodlayırıq.
Kod bu `my-agent` reposunda Python layihəsi kimi saxlanılır.

## Hələlik nə edir (mərhələ 1)
- Binance-dən public OHLCV çəkir (API key lazım deyil)
- EMA / RSI / MACD / ATR hesablayır
- `LONG / SHORT / NEYTRAL` siqnal + inam faizi + səbəb verir

## Sonra nə olacaq (mərhələ 2, hələ aktiv deyil)
- `src/exchange_trade.py` stub hazırdır
- Real order yalnız `sənin YES təsdiqin` ilə açılacaq (`--confirm yes` olmadan order getmir)
- Hələlik default `dry-run` rejimdir

## Quraşdırma

1. Python 3.11+ quraşdır: https://www.python.org/downloads/
   və ya PowerShell-də: `winget install -e --id Python.Python.3.12`
2. Terminalda bu qovluqda:
```powershell
pip install -r requirements.txt
copy .env.example .env
python -m src.cli --symbol BTC/USDT --timeframe 1h
```

## Nümunə
```powershell
python -m src.cli --symbol BTC/USDT,ETH/USDT --timeframe 1h --limit 200
python -m src.cli --symbol BTC/USDT --timeframe 15m --json
```

## Fayllar
- `config.py` — simvol, timeframe, indikator parametrləri (.env-dən oxuyur)
- `src/data.py` — birjadan data çəkmə (ccxt)
- `src/indicators.py` — EMA/RSI/MACD/ATR (saf pandas, əlavə TA lib yoxdur)
- `src/strategy.py` — skorinq ilə siqnal
- `src/cli.py` — terminal interfeysi
- `src/exchange_trade.py` — gələcək order modulu (təsdiqli, dry-run)
