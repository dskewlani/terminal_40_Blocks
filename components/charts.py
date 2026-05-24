"""
components/charts.py — ProTrader Terminal v2.0
Reusable advanced chart components.
Blocks 27 (Drawing Tools), 13 (Options viz), 17 (Risk charts), 18 (Heatmaps).
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st
from typing import Optional, List


def _theme() -> dict:
    """Get current theme colors from session state."""
    dark = st.session_state.get("theme", "dark") == "dark"
    return {
        "bg": "#050A14" if dark else "#FFFFFF",
        "bg2": "#0D1B2A" if dark else "#F8FAFC",
        "surface": "#0F2035" if dark else "#FFFFFF",
        "grid": "#1E3A5F" if dark else "#E2E8F0",
        "text": "#E2E8F0" if dark else "#1E293B",
        "green": "#00FF88",
        "red": "#FF4466",
        "accent": "#00D4FF",
        "yellow": "#FFD700",
    }


# ─── Full OHLCV + Subplots (Block 27) ────────────────────────────────────────

def full_chart(df: pd.DataFrame, symbol: str,
               show_volume: bool = True,
               show_rsi: bool = True,
               show_macd: bool = False,
               overlay_indicators: list = None,
               drawings: list = None,
               levels: dict = None) -> go.Figure:
    """
    Block 27: Full multi-panel chart with optional RSI/MACD subplots.
    overlay_indicators: list of column names to overlay on price panel.
    drawings: list of {type, x0, y0, x1, y1, color} dicts.
    levels: {support: [...], resistance: [...]} for SR lines.
    """
    t = _theme()
    overlay_indicators = overlay_indicators or []
    drawings = drawings or []

    # Row configuration
    rows = 1
    row_heights = [0.6]
    subplot_titles = [symbol]
    if show_volume:
        rows += 1
        row_heights.append(0.15)
        subplot_titles.append("Volume")
    if show_rsi:
        rows += 1
        row_heights.append(0.12)
        subplot_titles.append("RSI")
    if show_macd:
        rows += 1
        row_heights.append(0.13)
        subplot_titles.append("MACD")

    fig = make_subplots(
        rows=rows, cols=1,
        shared_xaxes=True,
        row_heights=row_heights,
        subplot_titles=subplot_titles,
        vertical_spacing=0.04
    )

    # ── Candlestick ──
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name=symbol,
        increasing_line_color=t["green"], decreasing_line_color=t["red"],
        increasing_fillcolor=t["green"], decreasing_fillcolor=t["red"],
    ), row=1, col=1)

    # ── Overlays ──
    overlay_colors = {
        "ema9": t["yellow"], "ema21": t["accent"], "ema50": "#FF6B35", "ema200": "#9B59B6",
        "vwap": "#9B59B6", "bb_upper": "#475569", "bb_lower": "#475569", "bb_mid": "#334155",
        "hma21": "#F97316", "kc_upper": "#475569", "kc_lower": "#475569",
        "supertrend": t["green"],
    }
    for ind in overlay_indicators:
        if ind in df.columns:
            color = overlay_colors.get(ind, t["accent"])
            dash = "dot" if "bb" in ind or "kc" in ind else "solid"
            fig.add_trace(go.Scatter(
                x=df.index, y=df[ind], name=ind.upper(),
                line=dict(color=color, width=1.5, dash=dash), opacity=0.85
            ), row=1, col=1)

    # ── Support / Resistance (Block 27) ──
    if levels:
        for sr_price in levels.get("resistance", []):
            fig.add_hline(y=sr_price, line_color=t["red"], line_dash="dot",
                          line_width=1, opacity=0.6,
                          annotation_text=f"R {sr_price:.0f}",
                          annotation_position="right", row=1, col=1)
        for sr_price in levels.get("support", []):
            fig.add_hline(y=sr_price, line_color=t["green"], line_dash="dot",
                          line_width=1, opacity=0.6,
                          annotation_text=f"S {sr_price:.0f}",
                          annotation_position="right", row=1, col=1)

    # ── Drawing Tools (Block 27) ──
    for d in drawings:
        d_type = d.get("type", "line")
        color = d.get("color", t["accent"])
        if d_type == "trendline":
            fig.add_shape(type="line",
                          x0=d["x0"], y0=d["y0"], x1=d["x1"], y1=d["y1"],
                          line=dict(color=color, width=2),
                          xref="x", yref="y", row=1, col=1)
        elif d_type == "hline":
            fig.add_hline(y=d["y0"], line_color=color, line_width=1.5,
                          line_dash=d.get("dash", "solid"), row=1, col=1)
        elif d_type == "rect":
            fig.add_shape(type="rect",
                          x0=d["x0"], y0=d["y0"], x1=d["x1"], y1=d["y1"],
                          line=dict(color=color), fillcolor=color.replace(")", ",0.1)").replace("rgb", "rgba"),
                          xref="x", yref="y", row=1, col=1)
        elif d_type == "fib":
            # Fibonacci retracement levels
            y_range = d["y1"] - d["y0"]
            fibs = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
            fib_colors = ["#00FF88", "#00D4FF", "#FFD700", "#FF6B35", "#FF4466", "#9B59B6", "#00FF88"]
            for fib, fc in zip(fibs, fib_colors):
                fib_level = d["y0"] + y_range * fib
                fig.add_hline(y=fib_level, line_color=fc, line_dash="dot",
                              line_width=1, opacity=0.7,
                              annotation_text=f"Fib {fib:.3f}: {fib_level:.1f}",
                              annotation_position="right", row=1, col=1)

    # ── Volume ──
    current_row = 2
    if show_volume and "volume" in df.columns:
        vol_colors = [t["green"] if df["close"].iloc[i] >= df["open"].iloc[i] else t["red"]
                      for i in range(len(df))]
        fig.add_trace(go.Bar(
            x=df.index, y=df["volume"], name="Volume",
            marker_color=vol_colors, opacity=0.7
        ), row=current_row, col=1)
        if "vol_ratio" in df.columns:
            avg_vol = df["volume"].rolling(20).mean()
            fig.add_trace(go.Scatter(
                x=df.index, y=avg_vol, name="Avg Vol",
                line=dict(color=t["accent"], width=1, dash="dot"), opacity=0.7
            ), row=current_row, col=1)
        current_row += 1

    # ── RSI ──
    if show_rsi and "rsi" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["rsi"], name="RSI",
            line=dict(color=t["accent"], width=1.5)
        ), row=current_row, col=1)
        fig.add_hline(y=70, line_color=t["red"], line_dash="dash", opacity=0.5,
                      row=current_row, col=1)
        fig.add_hline(y=30, line_color=t["green"], line_dash="dash", opacity=0.5,
                      row=current_row, col=1)
        fig.add_hrect(y0=30, y1=70, fillcolor="rgba(0,212,255,0.03)",
                      row=current_row, col=1)
        current_row += 1

    # ── MACD ──
    if show_macd and "macd" in df.columns:
        macd_colors = [t["green"] if v >= 0 else t["red"] for v in df["macd_hist"].fillna(0)]
        fig.add_trace(go.Bar(
            x=df.index, y=df["macd_hist"], name="MACD Hist",
            marker_color=macd_colors, opacity=0.7
        ), row=current_row, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["macd"], name="MACD",
            line=dict(color=t["accent"], width=1.5)
        ), row=current_row, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["macd_signal"], name="Signal",
            line=dict(color=t["yellow"], width=1.5)
        ), row=current_row, col=1)

    # ── Layout ──
    fig.update_layout(
        paper_bgcolor=t["bg"],
        plot_bgcolor=t["bg2"],
        font=dict(color=t["text"], size=11),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9)),
        margin=dict(l=50, r=60, t=30, b=20),
        height=500 + (rows - 1) * 80,
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        hoverlabel=dict(bgcolor=t["surface"], font_color=t["text"]),
    )
    for i in range(1, rows + 1):
        fig.update_xaxes(gridcolor=t["grid"], row=i, col=1)
        fig.update_yaxes(gridcolor=t["grid"], row=i, col=1)

    return fig


# ─── OI Change Chart (Block 13) ───────────────────────────────────────────────

def oi_change_chart(chain_data: list, underlying: float) -> go.Figure:
    """Block 13: OI change bar chart — CE vs PE at each strike."""
    t = _theme()
    if not chain_data:
        return go.Figure()
    strikes, ce_oi_chg, pe_oi_chg = [], [], []
    for row in chain_data:
        strike = row.get("strikePrice", 0)
        ce_chg = row.get("CE", {}).get("changeinOpenInterest", 0) or 0
        pe_chg = row.get("PE", {}).get("changeinOpenInterest", 0) or 0
        # Only show strikes near ATM
        if abs(strike - underlying) <= underlying * 0.05:
            strikes.append(strike)
            ce_oi_chg.append(ce_chg)
            pe_oi_chg.append(pe_chg)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=strikes, y=ce_oi_chg, name="CE OI Change",
                          marker_color=t["red"], opacity=0.8))
    fig.add_trace(go.Bar(x=strikes, y=pe_oi_chg, name="PE OI Change",
                          marker_color=t["green"], opacity=0.8))
    fig.update_layout(
        title="OI Change at Each Strike",
        barmode="group",
        paper_bgcolor=t["bg"], plot_bgcolor=t["bg2"],
        font=dict(color=t["text"]),
        xaxis=dict(gridcolor=t["grid"], title="Strike"),
        yaxis=dict(gridcolor=t["grid"], title="OI Change"),
        height=300, margin=dict(l=40, r=40, t=40, b=20),
    )
    return fig


def iv_smile_chart(chain_data: list) -> go.Figure:
    """Block 13: IV smile / skew chart."""
    t = _theme()
    strikes, ce_iv, pe_iv = [], [], []
    for row in chain_data:
        ce_ivv = row.get("CE", {}).get("impliedVolatility", 0) or 0
        pe_ivv = row.get("PE", {}).get("impliedVolatility", 0) or 0
        if ce_ivv > 0 or pe_ivv > 0:
            strikes.append(row.get("strikePrice", 0))
            ce_iv.append(ce_ivv)
            pe_iv.append(pe_ivv)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=strikes, y=ce_iv, name="CE IV",
                              mode="lines+markers",
                              line=dict(color=t["red"], width=2)))
    fig.add_trace(go.Scatter(x=strikes, y=pe_iv, name="PE IV",
                              mode="lines+markers",
                              line=dict(color=t["green"], width=2)))
    fig.update_layout(
        title="IV Smile / Skew",
        paper_bgcolor=t["bg"], plot_bgcolor=t["bg2"],
        font=dict(color=t["text"]),
        xaxis=dict(gridcolor=t["grid"], title="Strike"),
        yaxis=dict(gridcolor=t["grid"], title="Implied Volatility %"),
        height=280, margin=dict(l=40, r=40, t=40, b=20),
    )
    return fig


# ─── Nifty50 Heatmap (Block 18) ───────────────────────────────────────────────

def nifty50_heatmap(stocks: list) -> go.Figure:
    """Block 18: Nifty 50 performance treemap / heatmap."""
    t = _theme()
    if not stocks:
        return go.Figure()
    df = pd.DataFrame(stocks)
    if "symbol" not in df.columns or "change_pct" not in df.columns:
        return go.Figure()

    fig = go.Figure(go.Treemap(
        labels=df["symbol"],
        parents=["Nifty 50"] * len(df),
        values=[abs(v) + 0.1 for v in df["change_pct"]],
        customdata=df["change_pct"].round(2),
        texttemplate="<b>%{label}</b><br>%{customdata}%",
        textfont=dict(size=11),
        marker=dict(
            colors=df["change_pct"],
            colorscale=[[0, "#FF4466"], [0.4, "#1E3A5F"], [0.6, "#1E3A5F"], [1, "#00FF88"]],
            cmid=0,
            showscale=True,
            colorbar=dict(title="% Change", tickfont=dict(color=t["text"]))
        ),
        hovertemplate="<b>%{label}</b><br>Change: %{customdata}%<extra></extra>"
    ))
    fig.update_layout(
        paper_bgcolor=t["bg"],
        font=dict(color=t["text"]),
        margin=dict(l=0, r=0, t=0, b=0),
        height=380
    )
    return fig


# ─── Multi-Symbol Comparison (Block 37) ───────────────────────────────────────

def multi_symbol_comparison(dfs: dict, normalized: bool = True) -> go.Figure:
    """Block 37: Overlay normalized price performance for multiple symbols."""
    t = _theme()
    fig = go.Figure()
    colors = [t["accent"], t["green"], t["yellow"], t["red"], "#9B59B6", "#F97316"]
    for i, (symbol, df) in enumerate(dfs.items()):
        if df.empty:
            continue
        y = df["close"]
        if normalized:
            y = y / y.iloc[0] * 100  # base 100
        color = colors[i % len(colors)]
        fig.add_trace(go.Scatter(
            x=df.index, y=y, name=symbol,
            line=dict(color=color, width=2), opacity=0.9
        ))

    fig.update_layout(
        title="Relative Performance (Base 100)" if normalized else "Price Comparison",
        paper_bgcolor=t["bg"], plot_bgcolor=t["bg2"],
        font=dict(color=t["text"]),
        xaxis=dict(gridcolor=t["grid"]),
        yaxis=dict(gridcolor=t["grid"], title="Base 100" if normalized else "Price (₹)"),
        height=300, margin=dict(l=40, r=40, t=40, b=20),
        hovermode="x unified",
    )
    return fig


# ─── Risk/Return Scatter (Block 17/33) ────────────────────────────────────────

def risk_return_scatter(strategies: list) -> go.Figure:
    """Block 17/33: Risk vs return scatter for strategies or portfolio."""
    t = _theme()
    fig = go.Figure()
    for s in strategies:
        fig.add_trace(go.Scatter(
            x=[s.get("max_drawdown", 5)],
            y=[s.get("total_pnl", 0)],
            mode="markers+text",
            name=s.get("label", "Strategy"),
            text=[s.get("label", "")],
            textposition="top center",
            marker=dict(
                size=max(10, s.get("sharpe", 1) * 10),
                color=t["accent"], opacity=0.85,
                line=dict(width=1, color=t["text"])
            )
        ))
    fig.update_layout(
        title="Risk vs Return",
        paper_bgcolor=t["bg"], plot_bgcolor=t["bg2"],
        font=dict(color=t["text"]),
        xaxis=dict(gridcolor=t["grid"], title="Max Drawdown %"),
        yaxis=dict(gridcolor=t["grid"], title="Total P&L (₹)"),
        height=280, margin=dict(l=40, r=40, t=40, b=20),
    )
    return fig


# ─── Efficient Frontier (Block 33) ────────────────────────────────────────────

def efficient_frontier_chart(ef_result: dict) -> go.Figure:
    """Block 33: Efficient frontier scatter plot."""
    t = _theme()
    if not ef_result or "volatilities" not in ef_result:
        return go.Figure()

    fig = go.Figure()
    # All portfolios
    fig.add_trace(go.Scatter(
        x=ef_result["volatilities"],
        y=ef_result["returns"],
        mode="markers",
        name="Portfolios",
        marker=dict(
            color=ef_result["sharpes"],
            colorscale=[[0, t["red"]], [0.5, t["yellow"]], [1, t["green"]]],
            size=5, opacity=0.6, showscale=True,
            colorbar=dict(title="Sharpe", tickfont=dict(color=t["text"]))
        )
    ))
    # Optimal portfolio
    fig.add_trace(go.Scatter(
        x=[ef_result.get("optimal_vol", 0) / 100],
        y=[ef_result.get("optimal_return", 0) / 100],
        mode="markers",
        name=f"Optimal (Sharpe {ef_result.get('optimal_sharpe', 0):.2f})",
        marker=dict(size=18, color=t["accent"], symbol="star",
                    line=dict(width=2, color=t["text"]))
    ))
    fig.update_layout(
        title="Efficient Frontier — MPT",
        paper_bgcolor=t["bg"], plot_bgcolor=t["bg2"],
        font=dict(color=t["text"]),
        xaxis=dict(gridcolor=t["grid"], title="Volatility (Annual)"),
        yaxis=dict(gridcolor=t["grid"], title="Return (Annual)"),
        height=320, margin=dict(l=40, r=60, t=40, b=20),
    )
    return fig
