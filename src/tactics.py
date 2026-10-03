"""Her taktika ayrica BUY/SELL/HOLD deyir. Saytda qisa adla gorsenir."""


def tactics_breakdown(df, ema_fast: int = 20, ema_slow: int = 50):
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    price = float(last["close"])
    ef = float(last[f"ema{ema_fast}"])
    es = float(last[f"ema{ema_slow}"])
    rsi_v = float(last["rsi"])
    hist = float(last["macd_hist"])
    prev_hist = float(prev["macd_hist"])

    tactics = []

    tactics.append({
        "name": "EMA",
        "signal": "BUY" if ef > es else ("SELL" if ef < es else "HOLD"),
        "detail": f"EMA{ema_fast} {ef:.2f} vs EMA{ema_slow} {es:.2f}",
    })
    tactics.append({
        "name": "TREND",
        "signal": "BUY" if price > ef else "SELL",
        "detail": f"Qiymet {price:.2f} vs EMA{ema_fast} {ef:.2f}",
    })

    if rsi_v < 30:
        rs, rd = "BUY", f"RSI {rsi_v:.1f} asiri satilib"
    elif rsi_v > 70:
        rs, rd = "SELL", f"RSI {rsi_v:.1f} asiri alinib"
    elif rsi_v > 55:
        rs, rd = "BUY", f"RSI {rsi_v:.1f} momentum guclu"
    elif rsi_v < 45:
        rs, rd = "SELL", f"RSI {rsi_v:.1f} momentum zeif"
    else:
        rs, rd = "HOLD", f"RSI {rsi_v:.1f} neytral"
    tactics.append({"name": "RSI", "signal": rs, "detail": rd})

    if prev_hist <= 0 < hist:
        ms, md = "BUY", "MACD yuxari kesisme"
    elif prev_hist >= 0 > hist:
        ms, md = "SELL", "MACD asagi kesisme"
    elif hist > 0:
        ms, md = "BUY", "MACD histogram musbet"
    else:
        ms, md = "SELL", "MACD histogram menfi"
    tactics.append({"name": "MACD", "signal": ms, "detail": md})

    return tactics


def premium_discount(df, lookback: int = 50):
    """Qiymet range-in hanisindadir: discount (<40%) = BUY zonasi, premium (>60%) = SELL zonasi."""
    win = df.tail(lookback)
    hi = float(win["high"].max())
    lo = float(win["low"].min())
    price = float(df["close"].iloc[-1])
    pos = (price - lo) / (hi - lo) if hi > lo else 0.5
    if pos < 0.4:
        return {"name": "P/D", "signal": "BUY",
                "detail": f"Discount zona ({pos * 100:.0f}%): {lo:.2f}-{hi:.2f}"}
    if pos > 0.6:
        return {"name": "P/D", "signal": "SELL",
                "detail": f"Premium zona ({pos * 100:.0f}%): {lo:.2f}-{hi:.2f}"}
    return {"name": "P/D", "signal": "HOLD",
            "detail": f"Ekvilibrium ({pos * 100:.0f}%)"}


def fvg(df, lookback: int = 10):
    """Son FVG: bullish (low[i] > high[i-2]) ve ya bearish. Mitigasiya olunmusa HOLD."""
    n = len(df)
    for i in range(n - 2, max(n - 2 - lookback, 2), -1):
        lo_i = float(df["low"].iloc[i])
        hi_prev = float(df["high"].iloc[i - 2])
        hi_i = float(df["high"].iloc[i])
        lo_prev = float(df["low"].iloc[i - 2])
        if lo_i > hi_prev:  # bullish FVG: [hi_prev, lo_i]
            mitigated = bool((df["low"].iloc[i + 1:] < hi_prev).any())
            if not mitigated:
                return {"name": "FVG", "signal": "BUY",
                        "detail": f"Bullish FVG {hi_prev:.2f}-{lo_i:.2f} aktivdir"}
        elif hi_i < lo_prev:  # bearish FVG
            mitigated = bool((df["high"].iloc[i + 1:] > lo_prev).any())
            if not mitigated:
                return {"name": "FVG", "signal": "SELL",
                        "detail": f"Bearish FVG {hi_i:.2f}-{lo_prev:.2f} aktivdir"}
    return {"name": "FVG", "signal": "HOLD", "detail": "Aktiv FVG yoxdur"}


def engulf(df):
    """Son baglanmis sam + sweep: bullish engulfing + low sweep = BUY (tersi SELL)."""
    if len(df) < 3:
        return {"name": "ENGULF", "signal": "HOLD", "detail": "Data azdir"}
    o1, c1 = float(df["open"].iloc[-2]), float(df["close"].iloc[-2])
    o0, c0 = float(df["open"].iloc[-1]), float(df["close"].iloc[-1])
    bull_eng = c0 > o0 and c1 < o1 and c0 >= o1 and o0 <= c1
    bear_eng = c0 < o0 and c1 > o1 and c0 <= o1 and o0 >= c1
    sweep_low = float(df["low"].iloc[-1]) < float(df["low"].iloc[-2])
    sweep_high = float(df["high"].iloc[-1]) > float(df["high"].iloc[-2])
    if bull_eng and sweep_low:
        return {"name": "ENGULF", "signal": "BUY", "detail": "Bullish engulfing + low sweep"}
    if bear_eng and sweep_high:
        return {"name": "ENGULF", "signal": "SELL", "detail": "Bearish engulfing + high sweep"}
    if bull_eng or bear_eng:
        return {"name": "ENGULF", "signal": "HOLD", "detail": "Engulfing var, sweep yoxdur"}
    return {"name": "ENGULF", "signal": "HOLD", "detail": "Engulfing yoxdur"}


def retest(df, ema_fast: int = 20, ema_slow: int = 50, lookback: int = 20):
    """EMA zonasina toxunus sayi: trend istiqametinde 2+ retest = giris hazirligi."""
    tail = df.tail(lookback)
    ef = tail[f"ema{ema_fast}"]
    es = tail[f"ema{ema_slow}"]
    lo = ef.where(ef < es, es)
    hi = ef.where(ef >= es, es)
    touches = int(((tail["close"] >= lo) & (tail["close"] <= hi)).sum())
    up = float(df[f"ema{ema_fast}"].iloc[-1]) > float(df[f"ema{ema_slow}"].iloc[-1])
    if touches >= 2:
        return {"name": "RETEST", "signal": "BUY" if up else "SELL",
                "detail": f"EMA zonasi {touches} retest ({'3cu giris zonasi' if touches >= 2 else ''})"}
    return {"name": "RETEST", "signal": "HOLD", "detail": f"Cemi {touches} retest"}


def oi_tactic(df, oi: list):
    """Qiymet + OI: yeni pul vs baglanis. 24 barliq pencere."""
    if len(oi) < 25 or len(df) < 25:
        return {"name": "OI", "signal": "HOLD", "detail": "OI datası azdir"}
    po = (oi[-1] - oi[-25]) / oi[-25] * 100 if oi[-25] else 0.0
    c0, c1 = float(df["close"].iloc[-1]), float(df["close"].iloc[-25])
    pp = (c0 - c1) / c1 * 100 if c1 else 0.0
    if pp > 0 and po > 0:
        return {"name": "OI", "signal": "BUY", "detail": f"Qiymet +{pp:.1f}%, OI +{po:.1f}%: yeni longlar"}
    if pp < 0 and po > 0:
        return {"name": "OI", "signal": "SELL", "detail": f"Qiymet {pp:.1f}%, OI +{po:.1f}%: yeni shortlar"}
    if pp > 0:
        return {"name": "OI", "signal": "HOLD", "detail": "Short cover: hereket zeif ola biler"}
    return {"name": "OI", "signal": "HOLD", "detail": "Longlar baglanir: hereket zeif ola biler"}


def extra_tactics(df, ema_fast: int = 20, ema_slow: int = 50, oi=None):
    out = [
        premium_discount(df),
        fvg(df),
        engulf(df),
        retest(df, ema_fast, ema_slow),
    ]
    if oi:
        try:
            out.append(oi_tactic(df, oi))
        except Exception:
            pass
    return out
