"""
backtest.py — ProTrader Terminal v2.0
Standalone backtesting engine — Block 16.
Walk-forward optimization, strategy comparison, multiple parameter sets.
"""

import pandas as pd
import numpy as np
import math
from typing import List, Optional, Dict, Tuple
from loguru import logger

from engine import (
    get_ohlcv, compute_indicators, score_signal,
    volatility_adjusted_position_size, calculate_targets_and_sl,
    classify_regime, _compile_backtest_results
)


def run_walk_forward(symbol: str, interval: str = "FIFTEEN_MINUTE",
                     days: int = 90, n_splits: int = 3,
                     param_grid: dict = None) -> dict:
    """
    Block 16: Walk-forward optimization.
    Split history into train/test windows.
    Optimize on train, validate on test.
    """
    df = get_ohlcv(symbol, interval=interval, days=days)
    if df.empty or len(df) < 100:
        return {"error": "Insufficient data"}

    df = compute_indicators(df)
    chunk_size = len(df) // (n_splits * 2)

    param_grid = param_grid or {
        "min_strength": [55, 65, 75],
        "risk_pct": [0.5, 1.0, 1.5],
        "max_hold_bars": [20, 40, 60],
    }

    results = []
    for fold in range(n_splits):
        train_start = fold * chunk_size
        train_end = train_start + chunk_size
        test_start = train_end
        test_end = test_start + chunk_size

        train_df = df.iloc[train_start:train_end]
        test_df = df.iloc[test_start:test_end]

        # Grid search on train
        best_params = None
        best_sharpe = -999
        for min_str in param_grid["min_strength"]:
            for risk in param_grid["risk_pct"]:
                for hold in param_grid["max_hold_bars"]:
                    params = {"min_strength": min_str, "risk_pct": risk, "max_hold_bars": hold}
                    res = _backtest_df(train_df, params)
                    if res.get("sharpe", -999) > best_sharpe:
                        best_sharpe = res.get("sharpe", -999)
                        best_params = params

        # Validate on test
        test_result = _backtest_df(test_df, best_params or {"min_strength": 65, "risk_pct": 1.0, "max_hold_bars": 40})
        results.append({
            "fold": fold + 1,
            "best_params": best_params,
            "train_sharpe": round(best_sharpe, 2),
            "test_sharpe": round(test_result.get("sharpe", 0), 2),
            "test_win_rate": round(test_result.get("win_rate", 0), 1),
            "test_pnl": round(test_result.get("total_pnl", 0), 2),
            "test_max_dd": round(test_result.get("max_drawdown", 0), 2),
        })

    avg_test_sharpe = np.mean([r["test_sharpe"] for r in results])
    avg_test_wr = np.mean([r["test_win_rate"] for r in results])

    return {
        "symbol": symbol,
        "folds": results,
        "avg_test_sharpe": round(avg_test_sharpe, 2),
        "avg_test_win_rate": round(avg_test_wr, 1),
        "overfitting_score": round(
            np.mean([r["train_sharpe"] for r in results]) - avg_test_sharpe, 2
        ),
    }


def _backtest_df(df: pd.DataFrame, params: dict) -> dict:
    """Run backtest on a pre-loaded DataFrame slice."""
    min_strength = params.get("min_strength", 65)
    risk_pct = params.get("risk_pct", 1.0)
    max_hold_bars = params.get("max_hold_bars", 40)

    trades = []
    position = None
    capital = 100000
    equity_curve = [capital]

    for i in range(30, len(df)):
        slice_df = df.iloc[:i]
        direction, strength, _ = score_signal(slice_df)
        row = df.iloc[i]
        price = float(row["close"])
        atr = float(row.get("atr", price * 0.01))

        if position is None and strength >= min_strength:
            qty = volatility_adjusted_position_size(capital, atr, price, risk_pct)
            if qty > 0:
                targets = calculate_targets_and_sl(price, atr, direction)
                position = {
                    "side": direction, "entry": price, "qty": qty,
                    "sl": targets["sl"], "target": targets["target1"],
                    "entry_idx": i
                }
        elif position:
            hit_sl = (position["side"] == "BUY" and price <= position["sl"]) or \
                     (position["side"] == "SELL" and price >= position["sl"])
            hit_target = (position["side"] == "BUY" and price >= position["target"]) or \
                         (position["side"] == "SELL" and price <= position["target"])
            force_exit = (i - position["entry_idx"]) > max_hold_bars

            if hit_sl or hit_target or force_exit:
                exit_price = position["sl"] if hit_sl else (position["target"] if hit_target else price)
                pnl = (exit_price - position["entry"]) * position["qty"]
                if position["side"] == "SELL":
                    pnl = -pnl
                capital += pnl
                trades.append({
                    "entry": position["entry"], "exit": exit_price,
                    "side": position["side"], "qty": position["qty"],
                    "pnl": round(pnl, 2),
                    "bars_held": i - position["entry_idx"],
                    "result": "WIN" if pnl > 0 else "LOSS",
                    "exit_reason": "SL" if hit_sl else ("TARGET" if hit_target else "TIMEOUT")
                })
                equity_curve.append(capital)
                position = None

    return _compile_backtest_results(trades, equity_curve, capital)


def compare_strategies(symbol: str, param_sets: List[dict],
                        interval: str = "FIFTEEN_MINUTE", days: int = 60) -> Dict:
    """
    Block 16: Compare multiple parameter sets on the same symbol.
    Returns results for each, and equity curves for plotting.
    """
    df = get_ohlcv(symbol, interval=interval, days=days)
    if df.empty:
        return {"error": "No data"}
    df = compute_indicators(df)

    comparison = []
    for i, params in enumerate(param_sets):
        result = _backtest_df(df, params)
        result["label"] = params.get("label", f"Strategy {i+1}")
        result["params"] = params
        comparison.append(result)

    return {
        "symbol": symbol,
        "strategies": comparison,
        "best_by_sharpe": max(comparison, key=lambda x: x.get("sharpe", 0)).get("label"),
        "best_by_winrate": max(comparison, key=lambda x: x.get("win_rate", 0)).get("label"),
    }


def generate_backtest_report(symbol: str, result: dict) -> str:
    """Generate markdown backtest summary."""
    if "error" in result:
        return f"## ❌ Error\n{result['error']}"

    lines = [
        f"## 📊 Backtest Report — {symbol}",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Trades | {result.get('total_trades', 0)} |",
        f"| Win Rate | {result.get('win_rate', 0):.1f}% |",
        f"| Total P&L | ₹{result.get('total_pnl', 0):+,.2f} |",
        f"| Max Drawdown | {result.get('max_drawdown', 0):.1f}% |",
        f"| Sharpe Ratio | {result.get('sharpe', 0):.2f} |",
        f"| Calmar Ratio | {result.get('calmar', 0):.2f} |",
        f"| Profit Factor | {result.get('profit_factor', 0):.2f} |",
        f"| Avg Win | ₹{result.get('avg_win', 0):+,.2f} |",
        f"| Avg Loss | ₹{result.get('avg_loss', 0):+,.2f} |",
    ]
    return "\n".join(lines)
