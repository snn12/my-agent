"""Skorinq strategiyası: +bull, -bear. Sadə və izah edilə bilən."""
import pandas as pd


def analyze(df: pd.DataFrame, ema_fast: int = 20, ema_slow: int = 50) -> dict:
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    price = float(last["close"])
    reasons: list[str] = []
    score = 0

    ef = float(last[f"ema{ema_fast}"])
    es = float(last[f"ema{ema_slow}"])
    if ef > es:
        score += 1
        reasons.append(f"EMA{ema_fast} ({ef:.2f}) > EMA{ema_slow} ({es:.2f}) — trend yuxarı")
    elif ef < es:
        score -= 1
        reasons.append(f"EMA{ema_fast} ({ef:.2f}) < EMA{ema_slow} ({es:.2f}) — trend aşağı")

    if price > ef:
        score += 1
        reasons.append(f"Qiymət ({price:.2f}) EMA{ema_fast} üstündə")
    else:
        score -= 1
        reasons.append(f"Qiymət ({price:.2f}) EMA{ema_fast} altında")

    rsi_v = float(last["rsi"])
    if rsi_v < 30:
        score += 1
        reasons.append(f"RSI {rsi_v:.1f} — həddindən artıq satılıb (bounce ehtimalı)")
    elif rsi_v > 70:
        score -= 1
        reasons.append(f"RSI {rsi_v:.1f} — həddindən artıq alınıb (korreksiya riski)")
    elif rsi_v > 55:
        score += 1
        reasons.append(f"RSI {rsi_v:.1f} — momentum güclü")
    elif rsi_v < 45:
        score -= 1
        reasons.append(f"RSI {rsi_v:.1f} — momentum zəif")
    else:
        reasons.append(f"RSI {rsi_v:.1f} — neytral zona")

    hist = float(last["macd_hist"])
    prev_hist = float(prev["macd_hist"])
    if hist > 0:
        score += 1
        reasons.append("MACD histogram müsbət")
    else:
        score -= 1
        reasons.append("MACD histogram mənfi")
    if prev_hist <= 0 < hist:
        score += 1
        reasons.append("MACD yuxarı kəsişmə (bullish cross)")
    elif prev_hist >= 0 > hist:
        score -= 1
        reasons.append("MACD aşağı kəsişmə (bearish cross)")

    atr_v = float(last["atr"])
    atr_pct = (atr_v / price * 100) if price else 0.0

    vol = float(last["volume"])
    vol_sma = float(last.get("vol_sma20", float("nan")))
    if vol_sma == vol_sma and vol > vol_sma * 1.2:
        reasons.append("Həcm orta həcmdən yüksəkdir — hərəkət təsdiqlənir")

    if score >= 2:
        signal = "LONG"
    elif score <= -2:
        signal = "SHORT"
    else:
        signal = "NEYTRAL"

    confidence = min(abs(score) / 6.0, 1.0)
    stop_dist = atr_v * 1.5

    return {
        "signal": signal,
        "score": score,
        "confidence": round(confidence * 100, 1),
        "price": price,
        "rsi": round(rsi_v, 1),
        "atr": round(atr_v, 4),
        "atr_pct": round(atr_pct, 2),
        "suggested_stop_dist": round(stop_dist, 4),
        "reasons": reasons,
    }
