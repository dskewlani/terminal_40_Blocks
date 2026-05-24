"""
utils/mcx_data.py — ProTrader Terminal v2.0
MCX-specific data: commodity prices, contract specs, seasonal patterns,
margin requirements, India-specific commodity fundamentals.
Block 7 (MCX Auto-Trading), Block 18 (Market Intelligence).
"""

import datetime
import random
from typing import Optional
from loguru import logger


# ─── MCX Contract Specifications ─────────────────────────────────────────────

MCX_CONTRACTS = {
    "GOLD": {
        "lot_size": 1,       # kg (mini: 100g)
        "unit": "10g",
        "tick_size": 1.0,
        "margin_pct": 4.0,
        "segment": "Bullion",
        "trading_hours": "09:00–23:30",
        "expiry_cycle": "monthly",
        "exchange_code": "MCX",
        "related": ["GOLDM", "GOLDPETAL"],
    },
    "GOLDM": {
        "lot_size": 10,      # grams (mini gold)
        "unit": "10g",
        "tick_size": 1.0,
        "margin_pct": 4.0,
        "segment": "Bullion",
        "trading_hours": "09:00–23:30",
        "expiry_cycle": "monthly",
    },
    "SILVER": {
        "lot_size": 30,      # kg
        "unit": "1kg",
        "tick_size": 1.0,
        "margin_pct": 5.0,
        "segment": "Bullion",
        "trading_hours": "09:00–23:30",
        "expiry_cycle": "monthly",
        "related": ["SILVERM", "SILVERMIC"],
    },
    "SILVERM": {
        "lot_size": 5,       # kg (mini)
        "unit": "1kg",
        "tick_size": 1.0,
        "margin_pct": 5.0,
        "segment": "Bullion",
        "trading_hours": "09:00–23:30",
    },
    "CRUDEOIL": {
        "lot_size": 100,     # barrels
        "unit": "1 barrel",
        "tick_size": 1.0,
        "margin_pct": 3.5,
        "segment": "Energy",
        "trading_hours": "09:00–23:30",
        "related": ["CRUDEOILM"],
    },
    "CRUDEOILM": {
        "lot_size": 10,
        "unit": "1 barrel",
        "tick_size": 1.0,
        "margin_pct": 3.5,
        "segment": "Energy",
        "trading_hours": "09:00–23:30",
    },
    "NATURALGAS": {
        "lot_size": 1250,    # mmBtu
        "unit": "1 mmBtu",
        "tick_size": 0.10,
        "margin_pct": 7.0,
        "segment": "Energy",
        "trading_hours": "09:00–23:30",
    },
    "COPPER": {
        "lot_size": 2500,    # kg (2.5 MT)
        "unit": "1 kg",
        "tick_size": 0.05,
        "margin_pct": 3.5,
        "segment": "Base Metals",
        "trading_hours": "09:00–23:30",
    },
    "ZINC": {
        "lot_size": 5000,    # kg (5 MT)
        "unit": "1 kg",
        "tick_size": 0.05,
        "margin_pct": 3.5,
        "segment": "Base Metals",
        "trading_hours": "09:00–23:30",
    },
    "NICKEL": {
        "lot_size": 1500,    # kg (1.5 MT)
        "unit": "1 kg",
        "tick_size": 0.10,
        "margin_pct": 4.0,
        "segment": "Base Metals",
        "trading_hours": "09:00–23:30",
    },
    "LEAD": {
        "lot_size": 5000,
        "unit": "1 kg",
        "tick_size": 0.05,
        "margin_pct": 3.5,
        "segment": "Base Metals",
        "trading_hours": "09:00–23:30",
    },
    "ALUMINIUM": {
        "lot_size": 5000,
        "unit": "1 kg",
        "tick_size": 0.05,
        "margin_pct": 3.5,
        "segment": "Base Metals",
        "trading_hours": "09:00–23:30",
    },
    "COTTON": {
        "lot_size": 25,      # bales (1 bale = 170kg)
        "unit": "1 bale",
        "tick_size": 10.0,
        "margin_pct": 5.0,
        "segment": "Agri",
        "trading_hours": "09:00–21:00",
    },
    "MENTHAOIL": {
        "lot_size": 360,     # kg
        "unit": "1 kg",
        "tick_size": 0.10,
        "margin_pct": 5.0,
        "segment": "Agri",
        "trading_hours": "09:00–17:30",
    },
}

# ─── Base Prices (demo seeding) ───────────────────────────────────────────────

_DEMO_BASE_PRICES = {
    "GOLD": 72000, "GOLDM": 72000, "SILVER": 86000, "SILVERM": 86000,
    "CRUDEOIL": 6800, "CRUDEOILM": 6800, "NATURALGAS": 230,
    "COPPER": 780, "ZINC": 220, "NICKEL": 1650, "LEAD": 185,
    "ALUMINIUM": 210, "COTTON": 57000, "MENTHAOIL": 940,
}


def get_mcx_contract_info(symbol: str) -> dict:
    """Return MCX contract specifications for a symbol."""
    return MCX_CONTRACTS.get(symbol.upper(), {
        "lot_size": 1, "unit": "unit", "tick_size": 1.0,
        "margin_pct": 5.0, "segment": "Unknown",
        "trading_hours": "09:00–23:30",
    })


def calculate_mcx_margin(symbol: str, qty: int, price: float) -> float:
    """Calculate approximate MCX margin requirement."""
    info = get_mcx_contract_info(symbol)
    lot_size = info.get("lot_size", 1)
    margin_pct = info.get("margin_pct", 5.0)
    contract_value = price * lot_size * qty
    return round(contract_value * margin_pct / 100, 2)


def calculate_mcx_pnl(symbol: str, entry: float, exit_price: float,
                       qty: int, side: str = "BUY") -> dict:
    """Calculate MCX P&L including lot size multiplier."""
    info = get_mcx_contract_info(symbol)
    lot_size = info.get("lot_size", 1)
    price_diff = exit_price - entry
    if side == "SELL":
        price_diff = -price_diff
    gross_pnl = price_diff * lot_size * qty
    # MCX charges: brokerage + CTT + exchange + GST
    turnover = (entry + exit_price) * lot_size * qty
    brokerage = min(20 * qty, turnover * 0.0002)   # ₹20/lot or 0.02%
    ctt = exit_price * lot_size * qty * 0.00001     # CTT on sell side
    exchange = turnover * 0.0000295
    gst = (brokerage + exchange) * 0.18
    total_charges = round(brokerage + ctt + exchange + gst, 2)
    return {
        "gross_pnl": round(gross_pnl, 2),
        "total_charges": total_charges,
        "net_pnl": round(gross_pnl - total_charges, 2),
        "contract_value": round(entry * lot_size * qty, 2),
        "lot_size": lot_size,
    }


# ─── MCX Correlation with Global Markets ─────────────────────────────────────

GLOBAL_CORRELATIONS = {
    "GOLD":       {"COMEX_Gold": 0.97, "DXY": -0.72, "US10Y": -0.45, "INRUSD": 0.65},
    "SILVER":     {"COMEX_Silver": 0.96, "DXY": -0.68, "Gold": 0.78},
    "CRUDEOIL":   {"Brent": 0.98, "WTI": 0.95, "DXY": -0.55, "INRUSD": 0.40},
    "NATURALGAS": {"NYMEX_NG": 0.94, "Weather_Index": 0.60},
    "COPPER":     {"LME_Copper": 0.95, "China_PMI": 0.72, "USD": -0.65},
    "ZINC":       {"LME_Zinc": 0.94, "China_Demand": 0.65},
    "ALUMINIUM":  {"LME_Aluminium": 0.93},
}


def get_global_correlation_hint(symbol: str) -> str:
    """Block 18: Return key global driver for MCX commodity."""
    corr = GLOBAL_CORRELATIONS.get(symbol.upper(), {})
    if not corr:
        return "No correlation data available"
    top_driver = max(corr, key=lambda k: abs(corr[k]))
    return (f"Highest correlation: **{top_driver}** ({corr[top_driver]:+.2f}). "
            f"Watch {top_driver} for directional cues.")


# ─── Seasonal Patterns ────────────────────────────────────────────────────────

SEASONAL_PATTERNS = {
    "GOLD": {
        1: 0.8, 2: -0.2, 3: -0.5, 4: -0.3, 5: 0.2, 6: 0.5,
        7: 0.9, 8: 1.2, 9: 1.5, 10: 0.8, 11: 0.3, 12: 0.6
    },   # Strong in Sep-Oct (Dhanteras demand)
    "SILVER": {
        1: 0.5, 2: -0.3, 3: -0.4, 4: -0.2, 5: 0.1, 6: 0.8,
        7: 1.0, 8: 1.5, 9: 1.8, 10: 1.0, 11: 0.5, 12: 0.3
    },
    "CRUDEOIL": {
        1: -0.5, 2: 0.3, 3: 0.8, 4: 1.0, 5: 0.5, 6: 0.2,
        7: -0.3, 8: -0.5, 9: -0.2, 10: 0.5, 11: -0.3, 12: -0.8
    },  # Strong Apr-May (driving season start)
    "NATURALGAS": {
        1: -1.0, 2: -0.8, 3: -1.5, 4: -0.5, 5: 0.2, 6: 0.5,
        7: 0.8, 8: 0.9, 9: 0.5, 10: 1.5, 11: 2.0, 12: 0.5
    },  # Strong Nov-Jan (winter heating)
}


def get_seasonal_bias(symbol: str, month: int = None) -> dict:
    """Block 7/18: Historical seasonal bias for MCX commodity."""
    month = month or datetime.date.today().month
    pattern = SEASONAL_PATTERNS.get(symbol.upper(), {})
    bias = pattern.get(month, 0)
    return {
        "symbol": symbol,
        "month": month,
        "seasonal_bias": bias,
        "direction": "BULLISH" if bias > 0.3 else ("BEARISH" if bias < -0.3 else "NEUTRAL"),
        "strength": abs(bias),
        "note": _seasonal_note(symbol, month)
    }


def _seasonal_note(symbol: str, month: int) -> str:
    notes = {
        ("GOLD", 9): "Navratri & Dhanteras buying season — typically bullish",
        ("GOLD", 10): "Peak festive demand — Dhanteras / Diwali",
        ("NATURALGAS", 11): "Winter demand builds — heating season begins",
        ("CRUDEOIL", 4): "Driving season demand pickup in US/Europe",
        ("SILVER", 8): "Monsoon retreat — industrial demand picks up",
    }
    return notes.get((symbol.upper(), month), "No specific seasonal note")


# ─── MCX Trading Session Check ────────────────────────────────────────────────

def is_mcx_session_active(symbol: str = None) -> tuple:
    """Block 7: Check if MCX is currently open."""
    now = datetime.datetime.now()
    h, m = now.hour, now.minute
    t = h * 60 + m
    open_time = 9 * 60       # 09:00
    close_time = 23 * 60 + 30  # 23:30

    # Agri products close earlier
    if symbol and symbol.upper() in ("COTTON", "MENTHAOIL"):
        close_time = 21 * 60  # 21:00

    if t < open_time:
        opens_in = open_time - t
        return False, f"MCX opens in {opens_in // 60}h {opens_in % 60}m (09:00 IST)"
    if t > close_time:
        return False, "MCX closed for today (closes 23:30 IST)"
    remaining = close_time - t
    return True, f"MCX active — {remaining // 60}h {remaining % 60}m remaining"


# ─── MCX Price Feed (demo) ────────────────────────────────────────────────────

def get_mcx_demo_prices() -> dict:
    """Demo MCX prices for testing when Angel One is not connected."""
    import numpy as np
    prices = {}
    for symbol, base in _DEMO_BASE_PRICES.items():
        np.random.seed(hash(symbol) % 65535)
        drift = np.random.normal(0, 0.005)
        prices[symbol] = round(base * (1 + drift), 2)
    return prices


def get_mcx_expiry_calendar() -> list:
    """MCX upcoming contract expiries."""
    today = datetime.date.today()
    expiries = []
    for i in range(1, 5):  # next 4 months
        month_date = datetime.date(today.year + (today.month + i - 1) // 12,
                                   (today.month + i - 1) % 12 + 1, 1)
        # MCX expiry: last Thursday of delivery month or specific date
        last_day = (month_date.replace(month=month_date.month % 12 + 1, day=1)
                    - datetime.timedelta(days=1))
        # Find last Thursday
        while last_day.weekday() != 3:  # 3 = Thursday
            last_day -= datetime.timedelta(days=1)
        for sym in ["GOLD", "SILVER", "CRUDEOIL", "COPPER"]:
            expiries.append({
                "symbol": sym,
                "expiry": str(last_day),
                "month": month_date.strftime("%b %Y"),
                "dte": (last_day - today).days,
            })
    return sorted(expiries, key=lambda x: x["dte"])
