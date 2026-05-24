"""
utils/risk.py — ProTrader Terminal v2.0
Risk management engine: position sizing, drawdown controls,
portfolio-level risk, Greeks, correlation, stress testing.
Blocks 4, 14, 17, 30, 31.
"""

import math
import numpy as np
import pandas as pd
from typing import List, Optional, Dict, Tuple


# ─── Position Sizing ──────────────────────────────────────────────────────────

def fixed_fractional_size(capital: float, risk_pct: float,
                            sl_distance: float, price: float) -> int:
    """Fixed-fractional position sizing (Block 14)."""
    if sl_distance <= 0 or price <= 0:
        return 0
    risk_amount = capital * (risk_pct / 100)
    qty = int(risk_amount / sl_distance)
    max_qty = int(capital * 0.15 / price)  # max 15% per trade
    return max(0, min(qty, max_qty))


def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """Full Kelly % of capital to bet (Block 14/31)."""
    if avg_loss == 0:
        return 0.0
    b = abs(avg_win / avg_loss)  # win-to-loss ratio
    p = win_rate / 100
    q = 1 - p
    kelly = (b * p - q) / b
    return max(0.0, round(kelly, 4))


def half_kelly(win_rate: float, avg_win: float, avg_loss: float) -> float:
    return kelly_criterion(win_rate, avg_win, avg_loss) * 0.5


def volatility_sized_qty(capital: float, atr: float, price: float,
                           risk_pct: float = 1.0, atr_mult: float = 2.0) -> int:
    """ATR-volatility adjusted position sizing (Block 4/14)."""
    if atr <= 0 or price <= 0:
        return 0
    sl_distance = atr * atr_mult
    return fixed_fractional_size(capital, risk_pct, sl_distance, price)


def adaptive_size_on_streak(base_qty: int, consecutive_losses: int,
                              consecutive_wins: int,
                              loss_reduction: float = 0.5,
                              win_cap: float = 1.25) -> int:
    """
    Block 14/21: Reduce size on loss streaks, cap on win streaks.
    Prevents revenge trading and overconfidence.
    """
    if consecutive_losses >= 3:
        factor = loss_reduction ** (consecutive_losses - 2)
        return max(1, int(base_qty * factor))
    if consecutive_wins >= 5:
        return int(base_qty * min(win_cap, 1.0 + (consecutive_wins - 4) * 0.05))
    return base_qty


def daily_loss_limit_check(current_pnl: float, daily_limit: float) -> Tuple[bool, str]:
    """Block 14/30: Hard stop when daily loss limit hit."""
    if current_pnl <= -abs(daily_limit):
        return False, f"🛑 Daily loss limit ₹{abs(daily_limit):,.0f} reached. All trading PAUSED."
    remaining = abs(daily_limit) + current_pnl
    pct_used = (abs(daily_limit) - remaining) / abs(daily_limit) * 100
    if pct_used >= 80:
        return True, f"⚠️ {pct_used:.0f}% of daily loss limit used. Reduce position sizes."
    return True, "OK"


def max_trades_per_day_check(trades_today: int, max_trades: int) -> Tuple[bool, str]:
    if trades_today >= max_trades:
        return False, f"🛑 Max {max_trades} trades/day limit reached."
    return True, f"{trades_today}/{max_trades} trades taken today"


# ─── Trade-Level Risk ─────────────────────────────────────────────────────────

def risk_reward_ratio(entry: float, sl: float, target: float, side: str = "BUY") -> float:
    """Calculate risk:reward ratio."""
    if side == "BUY":
        risk = entry - sl
        reward = target - entry
    else:
        risk = sl - entry
        reward = entry - target
    if risk <= 0:
        return 0.0
    return round(reward / risk, 2)


def breakeven_price(entry: float, charges: float, qty: int, side: str = "BUY") -> float:
    """Price at which position breaks even after charges."""
    charge_per_unit = charges / qty if qty > 0 else 0
    if side == "BUY":
        return entry + charge_per_unit
    return entry - charge_per_unit


def trailing_sl_price(entry: float, current_price: float, atr: float,
                       side: str = "BUY", trail_mult: float = 1.5) -> float:
    """Block 10: Trailing stop-loss based on ATR."""
    trail_distance = atr * trail_mult
    if side == "BUY":
        ideal_sl = current_price - trail_distance
        return max(ideal_sl, entry)  # never trail below entry
    else:
        ideal_sl = current_price + trail_distance
        return min(ideal_sl, entry)  # never trail above entry


def scale_out_plan(entry: float, atr: float, qty: int, side: str = "BUY") -> list:
    """
    Block 10: Scale-out plan at multiple targets.
    Returns list of (target_price, qty_to_exit) tuples.
    """
    plans = []
    targets = [
        (entry + atr * 1.5 if side == "BUY" else entry - atr * 1.5, max(1, qty // 3), "T1 — 33%"),
        (entry + atr * 2.5 if side == "BUY" else entry - atr * 2.5, max(1, qty // 3), "T2 — 33%"),
        (entry + atr * 4.0 if side == "BUY" else entry - atr * 4.0, qty - (qty // 3) * 2, "T3 — Runner"),
    ]
    for price, exit_qty, label in targets:
        if exit_qty > 0:
            plans.append({"target": round(price, 2), "qty": exit_qty, "label": label})
    return plans


# ─── Portfolio-Level Risk ─────────────────────────────────────────────────────

def portfolio_var(positions: List[dict], confidence: float = 0.95,
                   days: int = 1) -> float:
    """
    Block 17/30: Portfolio Value at Risk using historical simulation.
    Returns expected loss at given confidence level.
    """
    if not positions:
        return 0.0
    # Simulate 1-day returns per position
    total_exposure = sum(p.get("qty", 0) * p.get("cmp", 0) for p in positions)
    if total_exposure == 0:
        return 0.0
    # Use 1% daily volatility assumption (demo)
    daily_vol = 0.01
    z = 1.645 if confidence == 0.95 else 2.326  # 99%
    return round(total_exposure * daily_vol * z * math.sqrt(days), 2)


def portfolio_beta(positions: List[dict], nifty_beta: dict = None) -> float:
    """
    Block 30: Weighted portfolio beta.
    nifty_beta: dict of {symbol: beta_value}
    """
    if not positions:
        return 1.0
    nifty_beta = nifty_beta or {}
    total_exposure = sum(p.get("qty", 0) * p.get("cmp", 0) for p in positions)
    if total_exposure == 0:
        return 1.0
    weighted_beta = sum(
        p.get("qty", 0) * p.get("cmp", 0) * nifty_beta.get(p.get("symbol", ""), 1.0)
        for p in positions
    )
    return round(weighted_beta / total_exposure, 3)


def portfolio_correlation(symbols: List[str], returns: Dict[str, pd.Series]) -> pd.DataFrame:
    """Block 30/33: Pairwise correlation matrix from return series."""
    if len(symbols) < 2:
        return pd.DataFrame()
    df = pd.DataFrame({s: returns.get(s, pd.Series()) for s in symbols})
    return df.corr().round(3)


def concentration_risk(positions: List[dict]) -> dict:
    """Block 30: Check if any single position is >20% of portfolio."""
    if not positions:
        return {"issues": [], "max_concentration": 0}
    total = sum(p.get("qty", 0) * p.get("cmp", 0) for p in positions)
    if total == 0:
        return {"issues": [], "max_concentration": 0}
    issues = []
    max_conc = 0
    for p in positions:
        exposure = p.get("qty", 0) * p.get("cmp", 0)
        pct = exposure / total * 100
        max_conc = max(max_conc, pct)
        if pct > 20:
            issues.append(f"⚠️ {p.get('symbol','')} is {pct:.1f}% of portfolio — above 20% limit")
    return {"issues": issues, "max_concentration": round(max_conc, 1)}


def sector_concentration(positions: List[dict]) -> dict:
    """Block 30: Check sector concentration."""
    sector_map = {
        "RELIANCE": "Energy", "ONGC": "Energy", "BPCL": "Energy",
        "INFY": "IT", "TCS": "IT", "WIPRO": "IT", "HCLTECH": "IT",
        "HDFCBANK": "Banking", "ICICIBANK": "Banking", "SBIN": "Banking", "AXISBANK": "Banking",
        "SUNPHARMA": "Pharma", "DRREDDY": "Pharma", "CIPLA": "Pharma",
        "MARUTI": "Auto", "TATAMOTORS": "Auto", "M&M": "Auto",
        "NESTLEIND": "FMCG", "ITC": "FMCG", "HINDUNILVR": "FMCG",
    }
    sector_exposure = {}
    total = sum(p.get("qty", 0) * p.get("cmp", 0) for p in positions)
    for p in positions:
        sector = sector_map.get(p.get("symbol", ""), "Other")
        exposure = p.get("qty", 0) * p.get("cmp", 0)
        sector_exposure[sector] = sector_exposure.get(sector, 0) + exposure
    if total > 0:
        sector_pct = {k: round(v / total * 100, 1) for k, v in sector_exposure.items()}
    else:
        sector_pct = {}
    issues = [f"⚠️ {s}: {p:.0f}% — concentrated" for s, p in sector_pct.items() if p > 35]
    return {"sector_pct": sector_pct, "issues": issues}


def max_concurrent_positions_check(open_positions: List[dict],
                                    max_positions: int = 5) -> Tuple[bool, str]:
    """Block 30: Limit open positions to reduce correlated exposure."""
    n = len(open_positions)
    if n >= max_positions:
        return False, f"🛑 Max {max_positions} concurrent positions reached ({n} open)"
    return True, f"{n}/{max_positions} positions open"


# ─── Drawdown Controls ────────────────────────────────────────────────────────

def rolling_drawdown(equity_curve: List[float]) -> List[float]:
    """Block 17: Rolling drawdown from peak."""
    ec = pd.Series(equity_curve)
    return ((ec - ec.cummax()) / ec.cummax() * 100).tolist()


def max_drawdown(equity_curve: List[float]) -> float:
    return min(rolling_drawdown(equity_curve)) if equity_curve else 0.0


def drawdown_recovery_time(equity_curve: List[float]) -> int:
    """Block 17: Average bars to recover from drawdown."""
    ec = pd.Series(equity_curve)
    peak = ec.cummax()
    in_drawdown = ec < peak
    transitions = in_drawdown.astype(int).diff()
    starts = transitions[transitions == 1].index.tolist()
    ends = transitions[transitions == -1].index.tolist()
    durations = []
    for start in starts:
        future_ends = [e for e in ends if e > start]
        if future_ends:
            durations.append(future_ends[0] - start)
    return int(np.mean(durations)) if durations else 0


# ─── Greeks (Extended, Block 5/13) ───────────────────────────────────────────

def portfolio_delta(positions: List[dict]) -> float:
    """Net portfolio delta (sum of all option deltas + equity positions)."""
    total_delta = 0.0
    for p in positions:
        delta = p.get("delta", 1.0)  # equity = 1 delta per unit
        qty = p.get("qty", 0)
        side = 1 if p.get("side") == "BUY" else -1
        total_delta += delta * qty * side
    return round(total_delta, 2)


def portfolio_theta(positions: List[dict]) -> float:
    """Daily portfolio theta decay."""
    total_theta = 0.0
    for p in positions:
        theta = p.get("theta", 0.0)
        qty = p.get("qty", 0)
        lot_size = p.get("lot_size", 1)
        side = 1 if p.get("side") == "BUY" else -1
        total_theta += theta * qty * lot_size * side
    return round(total_theta, 2)


def portfolio_vega(positions: List[dict]) -> float:
    """Portfolio vega — sensitivity to IV change."""
    total_vega = 0.0
    for p in positions:
        vega = p.get("vega", 0.0)
        qty = p.get("qty", 0)
        lot_size = p.get("lot_size", 1)
        side = 1 if p.get("side") == "BUY" else -1
        total_vega += vega * qty * lot_size * side
    return round(total_vega, 2)


# ─── Black-Swan / Stress ─────────────────────────────────────────────────────

def stress_scenario(positions: List[dict], scenario: str) -> float:
    """
    Block 30: Named market scenarios.
    Returns portfolio impact in ₹.
    """
    scenarios = {
        "covid_crash": -0.38,        # March 2020 — 38% drop
        "lehman_2008": -0.55,        # 2008 — 55% drop
        "2020_vix_spike": -0.15,
        "flash_crash_5pct": -0.05,
        "flash_crash_10pct": -0.10,
        "rally_10pct": 0.10,
        "rally_20pct": 0.20,
        "inr_depreciation_5pct": -0.03,  # impact on import-heavy cos
    }
    shock = scenarios.get(scenario, -0.05)
    impact = sum(
        p.get("qty", 0) * p.get("cmp", 0) * shock * (1 if p.get("side") == "BUY" else -1)
        for p in positions
    )
    return round(impact, 2)


def all_stress_scenarios(positions: List[dict]) -> dict:
    scenarios = [
        "covid_crash", "lehman_2008", "2020_vix_spike",
        "flash_crash_5pct", "flash_crash_10pct", "rally_10pct", "rally_20pct"
    ]
    return {s: stress_scenario(positions, s) for s in scenarios}


# ─── Slippage & Market Impact ─────────────────────────────────────────────────

def estimate_slippage(price: float, qty: int, avg_volume: int,
                       spread_pct: float = 0.03) -> float:
    """
    Block 24: Estimate slippage based on order size vs ADV.
    Returns slippage per unit in ₹.
    """
    if avg_volume == 0:
        return price * spread_pct / 100
    participation_rate = qty / avg_volume
    market_impact = participation_rate * price * 0.1  # 10% of participation as impact
    spread = price * spread_pct / 100
    return round(spread + market_impact, 4)


def net_pnl_after_slippage(gross_pnl: float, slippage_per_unit: float,
                             qty: int, charges: float) -> float:
    return round(gross_pnl - (slippage_per_unit * qty) - charges, 2)
