"""
utils/nse_data.py — ProTrader Terminal v2.0
NSE-specific data: corporate actions, F&O ban, derivatives expiry,
market breadth, Nifty constituent data, and index data.
Blocks 12, 18, 19, 28, 32.
"""

import os, time, datetime, random
from typing import Optional, List, Dict
import requests
from loguru import logger

_NSE_BASE = "https://www.nseindia.com/api"
_NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "X-Requested-With": "XMLHttpRequest",
}
_session = None
_session_ts = 0


def _get_session() -> requests.Session:
    """NSE session with cookie warm-up."""
    global _session, _session_ts
    now = time.time()
    if _session and now - _session_ts < 300:
        return _session
    s = requests.Session()
    s.headers.update(_NSE_HEADERS)
    try:
        s.get("https://www.nseindia.com", timeout=8)
        _session = s
        _session_ts = now
    except Exception as e:
        logger.warning(f"NSE session warm-up failed: {e}")
    return s


def nse_get(endpoint: str, params: dict = None, retries: int = 3) -> Optional[dict]:
    """Robust NSE API fetcher with retries."""
    url = f"{_NSE_BASE}/{endpoint}"
    s = _get_session()
    for attempt in range(retries):
        try:
            r = s.get(url, params=params, timeout=12)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 401:
                # Session expired — re-warm
                global _session_ts
                _session_ts = 0
                _get_session()
        except Exception as e:
            logger.warning(f"NSE GET {endpoint} attempt {attempt+1}: {e}")
            time.sleep(1.5 ** attempt)
    return None


# ─── Market Breadth (Block 18/32) ─────────────────────────────────────────────

def get_market_breadth() -> dict:
    """Advances / Declines / Unchanged from NSE."""
    data = nse_get("equity-stockIndices", {"index": "SECURITIES%20IN%20F%26O"})
    if data and "data" in data:
        advances = sum(1 for s in data["data"] if float(s.get("pChange", 0) or 0) > 0)
        declines = sum(1 for s in data["data"] if float(s.get("pChange", 0) or 0) < 0)
        unchanged = sum(1 for s in data["data"] if float(s.get("pChange", 0) or 0) == 0)
        total = advances + declines + unchanged
        return {
            "advances": advances, "declines": declines, "unchanged": unchanged,
            "total": total,
            "ad_ratio": round(advances / max(declines, 1), 2),
            "breadth": "BULLISH" if advances > declines * 1.5 else (
                "BEARISH" if declines > advances * 1.5 else "NEUTRAL"
            )
        }
    return {"advances": 320, "declines": 180, "unchanged": 50,
            "total": 550, "ad_ratio": 1.78, "breadth": "BULLISH"}


def get_nifty50_heatmap() -> list:
    """Nifty 50 stock performance for heatmap."""
    data = nse_get("equity-stockIndices", {"index": "NIFTY%2050"})
    if data and "data" in data:
        return [
            {
                "symbol": s.get("symbol", ""),
                "ltp": float(s.get("lastPrice", 0) or 0),
                "change_pct": float(s.get("pChange", 0) or 0),
                "volume": int(s.get("totalTradedVolume", 0) or 0),
            }
            for s in data["data"] if s.get("symbol") and s.get("symbol") != "NIFTY 50"
        ]
    # Demo
    symbols = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","WIPRO","SBIN","AXISBANK",
               "BHARTIARTL","ITC","LT","KOTAKBANK","HINDUNILVR","BAJFINANCE","SUNPHARMA",
               "HCLTECH","ONGC","MARUTI","TITAN","NESTLEIND","POWERGRID","NTPC","ULTRACEMCO",
               "TATAMOTORS","M&M","ADANIPORTS","BAJAJFINSV","GRASIM","TECHM","DRREDDY",
               "DIVISLAB","CIPLA","EICHERMOT","COALINDIA","BPCL","HINDALCO","JSWSTEEL",
               "TATACONSUM","APOLLOHOSP","BRITANNIA","INDUSINDBK","SBILIFE","HDFCLIFE",
               "NIFTY50","BANKNIFTY","FINNIFTY","MIDCPNIFTY","TITAN","NESTLEIND","WIPRO"]
    return [
        {"symbol": s, "ltp": 1000+random.uniform(0,4000),
         "change_pct": random.uniform(-3.5, 3.5), "volume": random.randint(100000, 10000000)}
        for s in symbols[:50]
    ]


# ─── F&O Data (Block 12/13/19) ────────────────────────────────────────────────

def get_fo_ban_list() -> list:
    """Stocks in F&O ban period."""
    data = nse_get("fo-underlyings-scrip-wise-ban-list")
    if data and "data" in data:
        return data["data"]
    return []  # demo: no ban


def get_expiry_dates(symbol: str = "NIFTY") -> list:
    """Get all F&O expiry dates for a symbol."""
    data = nse_get("option-chain-indices", {"symbol": symbol})
    if data and "records" in data:
        return data["records"].get("expiryDates", [])
    # Demo: weekly + monthly
    today = datetime.date.today()
    expiries = []
    d = today
    for _ in range(8):
        days_to_thursday = (3 - d.weekday()) % 7
        thursday = d + datetime.timedelta(days=days_to_thursday)
        if thursday not in expiries:
            expiries.append(str(thursday))
        d = thursday + datetime.timedelta(days=1)
    return expiries[:6]


def get_derivatives_quotes(symbol: str, expiry: str) -> list:
    """Futures + options quotes for a symbol and expiry."""
    data = nse_get("quote-derivative", {"symbol": symbol})
    if data and "stocks" in data:
        return [s for s in data["stocks"] if expiry in s.get("metadata", {}).get("expiry", "")]
    return []


# ─── Corporate Actions (Block 12/28) ──────────────────────────────────────────

def get_corporate_actions(symbol: str = "", days_ahead: int = 30) -> list:
    """Dividends, splits, bonus, rights — upcoming in next N days."""
    endpoint = "corporates-corporateActions"
    params = {"index": "equities", "from_date": str(datetime.date.today()),
               "to_date": str(datetime.date.today() + datetime.timedelta(days=days_ahead)),
               "symbol": symbol}
    data = nse_get(endpoint, params)
    if data and "data" in data:
        return data["data"]
    # Demo
    return [
        {"symbol": "INFY", "purpose": "Interim Dividend - Rs 21/-",
         "exDate": str(datetime.date.today() + datetime.timedelta(days=3))},
        {"symbol": "TCS", "purpose": "Final Dividend - Rs 28/-",
         "exDate": str(datetime.date.today() + datetime.timedelta(days=7))},
        {"symbol": "RELIANCE", "purpose": "Annual General Meeting",
         "exDate": str(datetime.date.today() + datetime.timedelta(days=14))},
    ]


def get_upcoming_ipos() -> list:
    """Upcoming / ongoing IPOs."""
    data = nse_get("ipos")
    if data and "data" in data:
        return data["data"]
    return [
        {"companyName": "Demo IPO Ltd", "issueSize": "₹2500 Cr",
         "openDate": str(datetime.date.today() + datetime.timedelta(days=2)),
         "closeDate": str(datetime.date.today() + datetime.timedelta(days=4)),
         "price": "₹180-190", "lotSize": 78}
    ]


# ─── VIX & Fear-Greed (Block 18) ──────────────────────────────────────────────

def get_india_vix() -> float:
    """India VIX from NSE."""
    data = nse_get("equity-stockIndices", {"index": "INDIA%20VIX"})
    if data and "data" in data:
        for s in data["data"]:
            if s.get("symbol") == "INDIA VIX":
                return float(s.get("lastPrice", 15) or 15)
    return round(14 + random.uniform(-2, 4), 2)  # demo


def vix_to_daily_move(vix: float) -> float:
    """Convert annual VIX to expected daily move %."""
    return round(vix / 16, 2)


def fear_greed_index(vix: float, adv_dec: float = 1.0, pcr: float = 1.0) -> dict:
    """
    Block 18: Composite Fear-Greed Index (0=Extreme Fear, 100=Extreme Greed).
    Inputs: VIX, Advance-Decline ratio, Put-Call Ratio.
    """
    # VIX component (inverted — high VIX = fear)
    vix_score = max(0, min(100, 100 - (vix - 10) * 4))

    # A/D component
    ad_score = max(0, min(100, adv_dec * 50))

    # PCR component (PCR > 1.2 = bearish = fear)
    pcr_score = max(0, min(100, (2 - pcr) * 50))

    composite = round((vix_score * 0.5 + ad_score * 0.3 + pcr_score * 0.2), 1)

    if composite >= 75:
        label = "EXTREME GREED"
        emoji = "😤"
        action = "Consider reducing longs / adding hedges"
    elif composite >= 55:
        label = "GREED"
        emoji = "🤑"
        action = "Normal trading — stay disciplined"
    elif composite >= 45:
        label = "NEUTRAL"
        emoji = "😐"
        action = "Market balanced — follow signals"
    elif composite >= 25:
        label = "FEAR"
        emoji = "😰"
        action = "Look for value buys / reduce size"
    else:
        label = "EXTREME FEAR"
        emoji = "😱"
        action = "Avoid new positions / strong hedges"

    return {
        "score": composite,
        "label": label,
        "emoji": emoji,
        "action": action,
        "components": {
            "vix_score": round(vix_score, 1),
            "ad_score": round(ad_score, 1),
            "pcr_score": round(pcr_score, 1),
        }
    }


# ─── Nifty Levels (Block 12) ──────────────────────────────────────────────────

def get_index_levels() -> dict:
    """Key Nifty/BankNifty levels: spot, futures, OI data."""
    indices = ["NIFTY 50", "NIFTY BANK", "NIFTY FIN SERVICE"]
    result = {}
    for idx in indices:
        data = nse_get("equity-stockIndices", {"index": idx.replace(" ", "%20")})
        if data and "data" in data:
            for s in data["data"]:
                if s.get("symbol") == idx:
                    result[idx] = {
                        "ltp": float(s.get("lastPrice", 0) or 0),
                        "change": float(s.get("change", 0) or 0),
                        "pchange": float(s.get("pChange", 0) or 0),
                        "high": float(s.get("dayHigh", 0) or 0),
                        "low": float(s.get("dayLow", 0) or 0),
                        "open": float(s.get("open", 0) or 0),
                        "prev_close": float(s.get("previousClose", 0) or 0),
                    }
        if idx not in result:
            base = {"NIFTY 50": 25000, "NIFTY BANK": 55000, "NIFTY FIN SERVICE": 23000}.get(idx, 10000)
            result[idx] = {
                "ltp": base + random.uniform(-100, 100),
                "change": random.uniform(-150, 150),
                "pchange": random.uniform(-0.5, 0.5),
                "high": base + random.uniform(50, 200),
                "low": base - random.uniform(50, 200),
                "open": base + random.uniform(-50, 50),
                "prev_close": base,
            }
    return result


# ─── SGX Nifty / Gift Nifty (Block 12) ───────────────────────────────────────

def get_sgx_nifty() -> dict:
    """GIFT Nifty data for pre-market gap estimation."""
    # Official NSE GIFT Nifty endpoint
    data = nse_get("exchange-index-live-data", {"sector": "GIFT"})
    if data:
        return data
    # Demo
    nifty_spot = 25000 + random.uniform(-100, 100)
    sgx = nifty_spot + random.uniform(-80, 80)
    return {
        "sgx_nifty": round(sgx, 2),
        "nifty_spot": round(nifty_spot, 2),
        "premium_discount": round(sgx - nifty_spot, 2),
        "expected_gap_pct": round((sgx - nifty_spot) / nifty_spot * 100, 2)
    }
