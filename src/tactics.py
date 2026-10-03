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
