"""Kripto RSS xəbərlər + coin teqi. Pulsuz, key-siz."""
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

FEEDS = [
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Cointelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt", "https://decrypt.co/feed"),
]

# coin -> acar sozler
COIN_KEYS = {
    "BTCUSDT": ["bitcoin", "btc"],
    "ETHUSDT": ["ethereum", "eth", "ether"],
    "SOLUSDT": ["solana", "sol"],
    "XRPUSDT": ["xrp", "ripple"],
    "DOGEUSDT": ["doge", "dogecoin"],
    "BNBUSDT": ["bnb", "binance"],
    "ADAUSDT": ["ada", "cardano"],
    "HYPEUSDT": ["hype", "hyperliquid"],
    "LINKUSDT": ["link", "chainlink"],
    "AVAXUSDT": ["avax", "avalanche"],
    "TONUSDT": ["toncoin", "ton"],
    "TRXUSDT": ["trx", "tron"],
    "DOTUSDT": ["dot", "polkadot"],
    "MATICUSDT": ["matic", "polygon"],
    "ARBUSDT": ["arbitrum", "arb"],
    "OPUSDT": ["optimism", "op "],
    "NEARUSDT": ["near protocol", "near"],
    "ATOMUSDT": ["atom", "cosmos"],
    "LTCUSDT": ["litecoin", "ltc"],
    "UNIUSDT": ["uniswap", "uni"],
    "AAVEUSDT": ["aave"],
    "TAOUSDT": ["bittensor", "tao"],
    "SUIUSDT": ["sui "],
    "APTUSDT": ["aptos", "apt "],
    "FETUSDT": ["fetch.ai", "fetch", "asi "],
    "RNDRUSDT": ["render", "rndr"],
    "INJUSDT": ["injective", "inj"],
    "SEIUSDT": ["sei "],
    "JUPUSDT": ["jupiter", "jup"],
    "ONDOUSDT": ["ondo"],
    "PEPEUSDT": ["pepe"],
    "SHIBUSDT": ["shib", "shiba"],
    "WIFUSDT": ["dogwifhat", "wif"],
    "BONKUSDT": ["bonk"],
    "FLOKIUSDT": ["floki"],
}

MACRO_KEYS = ["fed", "rate cut", "rate hike", "cpi", "inflation", "sec", "etf",
              "trump", "regulation", "interest rate", "payroll", "fomc", "powell",
              "treasury", "dollar", "recession"]


def tag(text: str):
    t = " " + text.lower() + " "
    coins = []
    for c, keys in COIN_KEYS.items():
        for k in keys:
            kk = k.strip()
            if len(kk) <= 4:
                if re.search(r"\b" + re.escape(kk) + r"\b", t):
                    coins.append(c)
                    break
            elif kk in t:
                coins.append(c)
                break
    macro = any(k in t for k in MACRO_KEYS)
    if not coins and macro:
        return ["BTCUSDT"], "market"
    if not coins:
        return [], "general"
    return coins, "coin"


def fetch_news(limit: int = 40):
    items = []
    for source, url in FEEDS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                root = ET.fromstring(r.read())
            for it in root.iter("item"):
                title = (it.findtext("title") or "").strip()
                link = (it.findtext("link") or "").strip()
                pub = (it.findtext("pubDate") or "").strip()
                if not title:
                    continue
                try:
                    ts = parsedate_to_datetime(pub).isoformat()
                except Exception:
                    ts = pub
                coins, kind = tag(title)
                items.append({"title": title, "link": link, "source": source,
                              "time": ts, "coins": coins, "kind": kind})
        except Exception:
            continue
    items.sort(key=lambda x: x["time"], reverse=True)
    return items[:limit]


_CACHE = {"ts": 0, "data": []}


def get_news(limit: int = 40):
    if time.time() - _CACHE["ts"] < 600 and _CACHE["data"]:
        return _CACHE["data"][:limit]
    data = fetch_news(60)
    _CACHE["ts"] = time.time()
    _CACHE["data"] = data
    return data[:limit]
