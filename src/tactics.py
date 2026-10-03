"""Her taktika ayrica BUY/SELL/HOLD deyir. Saytda qisa adla gorsenir."""
import math

import pandas as pd

from src.indicators import atr


def px(x, sig: int = 4):
    """Qiymet format: boyukde 2, kicikde anlamli reqem."""
    if x is None:
        return "-"
    try:
        ax = abs(float(x))
    except Exception:
        return str(x)
    if ax == 0:
        return "0"
    if ax >= 100:
        return format(x, ".2f")
    if ax >= 1:
        return format(x, ".4f")
    d = max(0, sig - int(math.floor(math.log10(ax))) - 1)
    return format(x, "." + str(min(d, 8)) + "f")


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
        "detail": f"EMA{ema_fast} {px(ef)} vs EMA{ema_slow} {px(es)}",
    })
    tactics.append({
        "name": "TREND",
        "signal": "BUY" if price > ef else "SELL",
        "detail": f"Qiymet {px(price)} vs EMA{ema_fast} {px(ef)}",
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
                "detail": f"Discount zona ({pos * 100:.0f}%): {px(lo)}-{px(hi)}"}
    if pos > 0.6:
        return {"name": "P/D", "signal": "SELL",
                "detail": f"Premium zona ({pos * 100:.0f}%): {px(lo)}-{px(hi)}"}
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
                        "detail": f"Bullish FVG {px(hi_prev)}-{px(lo_i)} aktivdir"}
        elif hi_i < lo_prev:  # bearish FVG
            mitigated = bool((df["high"].iloc[i + 1:] > lo_prev).any())
            if not mitigated:
                return {"name": "FVG", "signal": "SELL",
                        "detail": f"Bearish FVG {px(hi_i)}-{px(lo_prev)} aktivdir"}
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


def amd(df, lookback: int = 30):
    """AMD (sade): range + kenar sweep + genis govde = manipulationdan distribution-a."""
    if len(df) < lookback + 2:
        return {"name": "AMD", "signal": "HOLD", "detail": "Data azdir"}
    win = df.iloc[-(lookback + 1):-1]
    rng_hi = float(win["high"].max())
    rng_lo = float(win["low"].min())
    o = float(df["open"].iloc[-1])
    c = float(df["close"].iloc[-1])
    hi = float(df["high"].iloc[-1])
    lo = float(df["low"].iloc[-1])
    atr_v = float(df["atr"].iloc[-1]) or 1.0
    body = abs(c - o)
    if lo < rng_lo and c > rng_lo and c > o and body > 1.5 * atr_v:
        return {"name": "AMD", "signal": "BUY",
                "detail": f"Low sweep {px(rng_lo)} + genis govde (bear trap)"}
    if hi > rng_hi and c < rng_hi and o > c and body > 1.5 * atr_v:
        return {"name": "AMD", "signal": "SELL",
                "detail": f"High sweep {px(rng_hi)} + genis govde (bull trap)"}
    return {"name": "AMD", "signal": "HOLD", "detail": f"Range {px(rng_lo)}-{px(rng_hi)}"}


def poc(df, lookback: int = 100, buckets: int = 50):
    """Volume-at-price (sade): POC + value area 70%. Ustunde qebul = BUY."""
    win = df.tail(lookback)
    hi = float(win["high"].max())
    lo = float(win["low"].min())
    if hi <= lo:
        return {"name": "POC", "signal": "HOLD", "detail": "Data azdir"}
    width = (hi - lo) / buckets
    vols = [0.0] * buckets
    for _, r in win.iterrows():
        v = float(r["volume"])
        a = max(0, min(buckets - 1, int((float(r["low"]) - lo) / width)))
        b = max(0, min(buckets - 1, int((float(r["high"]) - lo) / width)))
        if b < a:
            a, b = b, a
        share = v / max(b - a + 1, 1)
        for k in range(a, b + 1):
            vols[k] += share
    poc_i = max(range(buckets), key=lambda k: vols[k])
    poc_price = lo + (poc_i + 0.5) * width
    order = sorted(range(buckets), key=lambda k: vols[k], reverse=True)
    total = sum(vols) or 1.0
    acc, va = 0.0, []
    for k in order:
        acc += vols[k]
        va.append(k)
        if acc >= 0.7 * total:
            break
    vah = lo + (max(va) + 1) * width
    val = lo + min(va) * width
    price = float(df["close"].iloc[-1])
    if price > vah:
        return {"name": "POC", "signal": "BUY",
                "detail": f"VAH {px(vah)} ustunde qebul (POC {px(poc_price)})"}
    if price < val:
        return {"name": "POC", "signal": "SELL",
                "detail": f"VAL {px(val)} altinda redd (POC {px(poc_price)})"}
    return {"name": "POC", "signal": "HOLD",
            "detail": f"Value area icinde {px(val)}-{px(vah)}"}


def swing_points(df, k: int = 5, lookback: int = 100):
    """Fraktal swingler: k bar sag-sol max/min. (index, qiymet) siyahilari."""
    win = df.tail(lookback).reset_index(drop=True)
    h = win["high"].to_numpy()
    ll = win["low"].to_numpy()
    n = len(win)
    highs, lows = [], []
    for i in range(k, n - k):
        if h[i] == h[i - k:i + k + 1].max():
            highs.append(float(h[i]))
        if ll[i] == ll[i - k:i + k + 1].min():
            lows.append(float(ll[i]))
    return highs, lows


def precise_levels(df, entry: float, atr_v: float, prec: int):
    """Swing + Fib + 2R esasli deqiq TP/SL."""
    buf = 0.25 * atr_v
    highs, lows = swing_points(df)
    above = sorted([x for x in highs if x > entry])
    below = sorted([x for x in lows if x < entry], reverse=True)
    sw_hi = above[0] if above else None
    sw_lo = below[0] if below else None

    long_sl = round((sw_lo - buf) if sw_lo else entry - 1.5 * atr_v, prec)
    short_sl = round((sw_hi + buf) if sw_hi else entry + 1.5 * atr_v, prec)

    # Fib genislenme: son ayagi tap (asagidan yuxari ve ya tersi)
    fib_up, fib_dn = {}, {}
    if sw_lo and sw_hi:
        leg = sw_hi - sw_lo
        fib_up = {"0.618": sw_hi + 0.618 * leg, "1.0": sw_hi + leg, "1.618": sw_hi + 1.618 * leg}
        fib_dn = {"0.618": sw_lo - 0.618 * leg, "1.0": sw_lo - leg, "1.618": sw_lo - 1.618 * leg}

    r_long = entry - long_sl
    r_short = short_sl - entry
    out = {
        "swing_high": round(sw_hi, prec) if sw_hi else None,
        "swing_low": round(sw_lo, prec) if sw_lo else None,
        "long": {"sl": long_sl,
                 "tp_swing": round(sw_hi, prec) if sw_hi else None,
                 "tp_fib1618": round(fib_up.get("1.618"), prec) if fib_up else None,
                 "tp_2R": round(entry + 2 * r_long, prec) if r_long > 0 else None},
        "short": {"sl": short_sl,
                  "tp_swing": round(sw_lo, prec) if sw_lo else None,
                  "tp_fib1618": round(fib_dn.get("1.618"), prec) if fib_dn else None,
                  "tp_2R": round(entry - 2 * r_short, prec) if r_short > 0 else None},
    }
    return out


def oi_tactic(df, oi: list):
    """Qiymet + OI: yeni pul vs baglanis. 24 barliq pencere."""
    if len(oi) < 25 or len(df) < 25:
        return {"name": "OI", "signal": "HOLD", "detail": "OI datasi azdir"}
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


def turtle(df, lookback: int = 20):
    """Turtle Soup: evvelki max/min sweep + geri baglanis = fade."""
    if len(df) < lookback + 2:
        return {"name": "TURTLE", "signal": "HOLD", "detail": "Data azdir"}
    prev_hi = float(df["high"].iloc[-lookback - 1:-1].max())
    prev_lo = float(df["low"].iloc[-lookback - 1:-1].min())
    hi, lo, cl = float(df["high"].iloc[-1]), float(df["low"].iloc[-1]), float(df["close"].iloc[-1])
    if hi > prev_hi and cl < prev_hi:
        return {"name": "TURTLE", "signal": "SELL",
                "detail": f"High sweep {px(prev_hi)} + geri donus"}
    if lo < prev_lo and cl > prev_lo:
        return {"name": "TURTLE", "signal": "BUY",
                "detail": f"Low sweep {px(prev_lo)} + geri donus"}
    return {"name": "TURTLE", "signal": "HOLD", "detail": "Sweep yoxdur"}


def rsi_div(df, lookback: int = 30, k: int = 3):
    """RSI divergensiya: qiymet HH + RSI LH = SELL (tersi BUY)."""
    win = df.tail(lookback).reset_index(drop=True)
    n = len(win)
    if n < 2 * k + 3:
        return {"name": "RSI-D", "signal": "HOLD", "detail": "Data azdir"}
    highs, lows = [], []
    for i in range(k, n - k):
        if float(win["high"].iloc[i]) == float(win["high"].iloc[i - k:i + k + 1].max()):
            highs.append(i)
        if float(win["low"].iloc[i]) == float(win["low"].iloc[i - k:i + k + 1].min()):
            lows.append(i)
    if len(highs) >= 2:
        a, b = highs[-2], highs[-1]
        if float(win["high"].iloc[b]) > float(win["high"].iloc[a]) and \
           float(win["rsi"].iloc[b]) < float(win["rsi"].iloc[a]):
            return {"name": "RSI-D", "signal": "SELL", "detail": "Bearish divergensiya (HH + RSI LH)"}
    if len(lows) >= 2:
        a, b = lows[-2], lows[-1]
        if float(win["low"].iloc[b]) < float(win["low"].iloc[a]) and \
           float(win["rsi"].iloc[b]) > float(win["rsi"].iloc[a]):
            return {"name": "RSI-D", "signal": "BUY", "detail": "Bullish divergensiya (LL + RSI HL)"}
    return {"name": "RSI-D", "signal": "HOLD", "detail": "Divergensiya yoxdur"}


def ema_cross(df, ema_fast: int = 20, ema_slow: int = 50, lookback: int = 5):
    """Teze kesisme (son N bar): yuxari = BUY, asagi = SELL."""
    d = df[f"ema{ema_fast}"] - df[f"ema{ema_slow}"]
    for i in range(len(df) - 1, max(len(df) - 1 - lookback, 0), -1):
        if d.iloc[i - 1] <= 0 < d.iloc[i]:
            return {"name": "X-EMA", "signal": "BUY", "detail": "Teze bullish kesisme"}
        if d.iloc[i - 1] >= 0 > d.iloc[i]:
            return {"name": "X-EMA", "signal": "SELL", "detail": "Teze bearish kesisme"}
    return {"name": "X-EMA", "signal": "HOLD", "detail": "Teze kesisme yoxdur"}


def boll(df):
    """Bollinger: kenardan kenara + squeeze."""
    if len(df) < 25 or df["bb_width"].iloc[-1] != df["bb_width"].iloc[-1]:
        return {"name": "BOLL", "signal": "HOLD", "detail": "Data azdir"}
    pctb = float(df["bb_pctb"].iloc[-1])
    w = df["bb_width"].tail(20)
    if float(w.iloc[-1]) <= float(w.min()):
        return {"name": "BOLL", "signal": "HOLD", "detail": "Squeeze: partlayis gozlenilir"}
    if pctb > 1.0:
        return {"name": "BOLL", "signal": "SELL", "detail": f"%B {px(pctb)}: hedden artiq yuxari"}
    if pctb < 0.0:
        return {"name": "BOLL", "signal": "BUY", "detail": f"%B {px(pctb)}: hedden artiq asagi"}
    return {"name": "BOLL", "signal": "HOLD", "detail": f"%B {px(pctb)} kanalda"}


def vwap_t(df):
    """Gunluk VWAP: ustu BUY, alti SELL."""
    v = df["vwap"].iloc[-1]
    if v != v or v is None:
        return {"name": "VWAP", "signal": "HOLD", "detail": "Data azdir"}
    price = float(df["close"].iloc[-1])
    if price > float(v):
        return {"name": "VWAP", "signal": "BUY", "detail": f"Qiymet VWAP {px(float(v))} ustunde"}
    return {"name": "VWAP", "signal": "SELL", "detail": f"Qiymet VWAP {px(float(v))} altinda"}


def stoch_t(df, k: int = 14, d: int = 3):
    """Stochastic: asagida yuxari kesisme BUY, yuxarida asagi kesisme SELL."""
    lo = df["low"].rolling(k).min()
    hi = df["high"].rolling(k).max()
    kk = 100 * (df["close"] - lo) / (hi - lo).replace(0, float("nan"))
    dd = kk.rolling(d).mean()
    k0, k1 = float(kk.iloc[-1]), float(kk.iloc[-2])
    d0 = float(dd.iloc[-1])
    if k1 <= d0 and k0 > d0 and k0 < 30:
        return {"name": "STOCH", "signal": "BUY", "detail": f"%K {k0:.1f} yuxari kesdi (asagi zona)"}
    if k1 >= d0 and k0 < d0 and k0 > 70:
        return {"name": "STOCH", "signal": "SELL", "detail": f"%K {k0:.1f} asagi kesdi (yuxari zona)"}
    if k0 < 20:
        return {"name": "STOCH", "signal": "BUY", "detail": f"%K {k0:.1f} hedden artiq satilib"}
    if k0 > 80:
        return {"name": "STOCH", "signal": "SELL", "detail": f"%K {k0:.1f} hedden artiq alinib"}
    return {"name": "STOCH", "signal": "HOLD", "detail": f"%K {k0:.1f} ortada"}


def adx_t(df, period: int = 14):
    """ADX: 25+ gucunde +DI>-DI BUY, eksine SELL."""
    up = df["high"].diff()
    dn = -df["low"].diff()
    plus_dm = up.where((up > dn) & (up > 0), 0.0)
    minus_dm = dn.where((dn > up) & (dn > 0), 0.0)
    prev_close = df["close"].shift(1)
    tr = pd.concat([(df["high"] - df["low"]),
                    (df["high"] - prev_close).abs(),
                    (df["low"] - prev_close).abs()], axis=1).max(axis=1)
    atr_s = tr.ewm(alpha=1 / period, adjust=False).mean().replace(0, float("nan"))
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr_s
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr_s
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, float("nan"))
    adx_v = float(dx.ewm(alpha=1 / period, adjust=False).mean().iloc[-1])
    p, m = float(plus_di.iloc[-1]), float(minus_di.iloc[-1])
    if adx_v != adx_v:
        return {"name": "ADX", "signal": "HOLD", "detail": "Data azdir"}
    if adx_v > 25 and p > m:
        return {"name": "ADX", "signal": "BUY", "detail": f"ADX {adx_v:.1f} guclu trend yuxari"}
    if adx_v > 25 and m > p:
        return {"name": "ADX", "signal": "SELL", "detail": f"ADX {adx_v:.1f} guclu trend asagi"}
    return {"name": "ADX", "signal": "HOLD", "detail": f"ADX {adx_v:.1f} zeif (trendsiz)"}


def cci_t(df, period: int = 20):
    """CCI momentum: +100 ustu BUY, -100 alti SELL."""
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    sma = tp.rolling(period).mean()
    md = (tp - sma).abs().rolling(period).mean().replace(0, float("nan"))
    cci_v = float(((tp - sma) / (0.015 * md)).iloc[-1])
    if cci_v != cci_v:
        return {"name": "CCI", "signal": "HOLD", "detail": "Data azdir"}
    if cci_v > 100:
        return {"name": "CCI", "signal": "BUY", "detail": f"CCI {cci_v:.0f} guclu momentum"}
    if cci_v < -100:
        return {"name": "CCI", "signal": "SELL", "detail": f"CCI {cci_v:.0f} guclu tezyiq"}
    return {"name": "CCI", "signal": "HOLD", "detail": f"CCI {cci_v:.0f} neytral"}


def donch_t(df, period: int = 20):
    """Donchian qirilma: 20-bar max ustu BUY, min alti SELL."""
    if len(df) < period + 1:
        return {"name": "DONCH", "signal": "HOLD", "detail": "Data azdir"}
    hi = float(df["high"].iloc[-(period + 1):-1].max())
    lo = float(df["low"].iloc[-(period + 1):-1].min())
    price = float(df["close"].iloc[-1])
    if price >= hi:
        return {"name": "DONCH", "signal": "BUY", "detail": f"20-bar max {px(hi)} qirildi"}
    if price <= lo:
        return {"name": "DONCH", "signal": "SELL", "detail": f"20-bar min {px(lo)} qirildi"}
    return {"name": "DONCH", "signal": "HOLD", "detail": f"Kanal {px(lo)}-{px(hi)} icinde"}


def pivot_t(df):
    """Gunluk pivot: qiymet PP ustu BUY, alti SELL."""
    d2 = df.copy()
    d2["day"] = d2["datetime"].dt.strftime("%Y-%m-%d")
    days = list(dict.fromkeys(d2["day"]))
    if len(days) < 2:
        return {"name": "PIVOT", "signal": "HOLD", "detail": "Data azdir"}
    prev = d2[d2["day"] == days[-2]]
    pp = (float(prev["high"].max()) + float(prev["low"].min()) + float(prev["close"].iloc[-1])) / 3.0
    price = float(df["close"].iloc[-1])
    if abs(price - pp) / pp < 0.002:
        return {"name": "PIVOT", "signal": "HOLD", "detail": f"PP {px(pp)} ustunde mucadile"}
    if price > pp:
        return {"name": "PIVOT", "signal": "BUY", "detail": f"Qiymet PP {px(pp)} ustunde"}
    return {"name": "PIVOT", "signal": "SELL", "detail": f"Qiymet PP {px(pp)} altinda"}


def supertrend_t(df, period: int = 10, mult: float = 3.0):
    """Supertrend: yasil xett alti BUY, qirmizi ustu SELL."""
    hl2 = ((df["high"] + df["low"]) / 2.0).to_numpy()
    atr_s = atr(df, period).to_numpy()
    n = len(df)
    up = hl2 - mult * atr_s
    lo = hl2 + mult * atr_s
    direction = [1] * n
    st = [0.0] * n
    for i in range(1, n):
        if hl2[i] > lo[i - 1]:
            direction[i] = 1
        elif hl2[i] < up[i - 1]:
            direction[i] = -1
        else:
            direction[i] = direction[i - 1]
            if direction[i] == 1 and up[i] < up[i - 1]:
                up[i] = up[i - 1]
            if direction[i] == -1 and lo[i] > lo[i - 1]:
                lo[i] = lo[i - 1]
        st[i] = up[i] if direction[i] == 1 else lo[i]
    if direction[-1] == 1:
        return {"name": "SUPER", "signal": "BUY", "detail": f"Supertrend {px(st[-1])} alti"}
    return {"name": "SUPER", "signal": "SELL", "detail": f"Supertrend {px(st[-1])} ustu"}


def orb_t(df, open_minutes: int = 60):
    """Opening Range Breakout: gunun ilk saatliq diapazon qirilma."""
    d2 = df.copy()
    d2["day"] = d2["datetime"].dt.strftime("%Y-%m-%d")
    today = d2["day"].iloc[-1]
    td = d2[d2["day"] == today]
    start = td["datetime"].iloc[0]
    opening = td[td["datetime"] <= start + pd.to_timedelta(open_minutes, unit="m")]
    if len(opening) < 1 or len(td) <= len(opening):
        return {"name": "ORB", "signal": "HOLD", "detail": "Opening range hele qurulur"}
    orh = float(opening["high"].max())
    orl = float(opening["low"].min())
    price = float(df["close"].iloc[-1])
    if price > orh:
        return {"name": "ORB", "signal": "BUY", "detail": f"OR {px(orl)}-{px(orh)} yuxari qirildi"}
    if price < orl:
        return {"name": "ORB", "signal": "SELL", "detail": f"OR {px(orl)}-{px(orh)} asagi qirildi"}
    return {"name": "ORB", "signal": "HOLD", "detail": f"OR {px(orl)}-{px(orh)} icinde"}


def fund_t(rates):
    """Funding ekstremleri (contrarian): cox musbet = SELL, cox menfi = BUY."""
    if not rates:
        return {"name": "FUND", "signal": "HOLD", "detail": "Funding datasi yoxdur"}
    avg = sum(rates[-3:]) / min(3, len(rates))
    if avg > 0.0005:
        return {"name": "FUND", "signal": "SELL",
                "detail": f"Funding +{avg * 100:.3f}%: longlar sixdir"}
    if avg < -0.0005:
        return {"name": "FUND", "signal": "BUY",
                "detail": f"Funding {avg * 100:.3f}%: shortlar sixdir"}
    return {"name": "FUND", "signal": "HOLD", "detail": f"Funding neytral ({avg * 100:.4f}%)"}


def extra_tactics(df, ema_fast: int = 20, ema_slow: int = 50, oi=None, funding=None):
    out = [
        premium_discount(df),
        fvg(df),
        engulf(df),
        turtle(df),
        amd(df),
        poc(df),
        rsi_div(df),
        ema_cross(df, ema_fast, ema_slow),
        boll(df),
        vwap_t(df),
        stoch_t(df),
        adx_t(df),
        cci_t(df),
        donch_t(df),
        pivot_t(df),
        supertrend_t(df),
        orb_t(df),
        retest(df, ema_fast, ema_slow),
    ]
    if oi:
        try:
            out.append(oi_tactic(df, oi))
        except Exception:
            pass
    try:
        out.append(fund_t(funding))
    except Exception:
        pass
    return out
