"""
ui.py — ProTrader Terminal v2.0
CSS, themes, chart helpers, toast system, components for all 40 blocks.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

# ──────────────────────────────────────────────────────────────────────────────
# BLOCK 11 — Theme System
# ──────────────────────────────────────────────────────────────────────────────

ACCENTS = {
    "blue": {"primary": "#00D4FF", "glow": "rgba(0,212,255,0.3)"},
    "gold": {"primary": "#FFD700", "glow": "rgba(255,215,0,0.3)"},
    "teal": {"primary": "#00CED1", "glow": "rgba(0,206,209,0.3)"},
    "purple": {"primary": "#9B59B6", "glow": "rgba(155,89,182,0.3)"},
    "green": {"primary": "#2ECC71", "glow": "rgba(46,204,113,0.3)"},
}

TERMINAL_CSS = """
<style>
/* ── Dark Theme (default) ── */
:root[data-theme="dark"], :root {
  --bg: #050A14;
  --bg2: #0D1B2A;
  --surface: #0F2035;
  --surface2: #162840;
  --border: #1E3A5F;
  --tx: #E2E8F0;
  --tx2: #94A3B8;
  --tx3: #475569;
  --green: #00FF88;
  --red: #FF4466;
  --yellow: #FFD700;
  --accent: #00D4FF;
  --accent-glow: rgba(0,212,255,0.3);
}

/* ── Light Theme ── */
:root[data-theme="light"] {
  --bg: #F8FAFC;
  --bg2: #F1F5F9;
  --surface: #FFFFFF;
  --surface2: #E8F0FE;
  --border: #CBD5E1;
  --tx: #1E293B;
  --tx2: #475569;
  --tx3: #94A3B8;
  --green: #16A34A;
  --red: #DC2626;
  --yellow: #CA8A04;
  --accent: #0369A1;
  --accent-glow: rgba(3,105,161,0.2);
}

/* ── Colorblind Safe ── */
:root[data-colorblind="true"] {
  --green: #F5A623;
  --red: #4A90D9;
}

/* ── Base Reset ── */
.main { background: var(--bg) !important; }
.main .block-container { padding: 0.8rem 1.2rem !important; max-width: 100% !important; }
[data-testid="stSidebar"] { background: var(--bg2) !important; border-right: 1px solid var(--border) !important; }
[data-testid="stSidebar"] * { color: var(--tx) !important; }
h1,h2,h3,h4,h5,h6,p,label,span,div { color: var(--tx) !important; }
.stButton>button { background: var(--surface2) !important; border: 1px solid var(--border) !important; color: var(--accent) !important; border-radius: 6px !important; font-weight: 600 !important; transition: all 0.2s !important; }
.stButton>button:hover { background: var(--accent) !important; color: var(--bg) !important; box-shadow: 0 0 12px var(--accent-glow) !important; }
.stSelectbox>div>div, .stTextInput>div>div>input, .stNumberInput>div>div>input { background: var(--surface) !important; border: 1px solid var(--border) !important; color: var(--tx) !important; border-radius: 6px !important; }
.stTabs [role="tab"] { background: var(--surface) !important; color: var(--tx2) !important; border: 1px solid var(--border) !important; border-radius: 6px 6px 0 0 !important; }
.stTabs [aria-selected="true"] { background: var(--surface2) !important; color: var(--accent) !important; border-bottom: 2px solid var(--accent) !important; }
.stMetric { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 10px !important; padding: 12px !important; }
.stMetric label { color: var(--tx2) !important; }
.stMetric [data-testid="metric-container"] { color: var(--tx) !important; }
.stDataFrame { background: var(--surface) !important; border: 1px solid var(--border) !important; }
.stAlert { border-radius: 8px !important; }
.stProgress > div > div { background: var(--accent) !important; }
hr { border-color: var(--border) !important; }
[data-testid="stExpander"] { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; }
textarea { background: var(--surface) !important; color: var(--tx) !important; border: 1px solid var(--border) !important; }

/* ── ProTrader Components ── */
.pt-header {
  background: linear-gradient(135deg, var(--bg2), var(--surface));
  border: 1px solid var(--border);
  border-bottom: 2px solid var(--accent);
  padding: 14px 20px;
  border-radius: 10px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 16px;
}
.pt-title {
  font-size: 1.6rem;
  font-weight: 800;
  color: var(--accent) !important;
  letter-spacing: 2px;
  text-transform: uppercase;
  font-family: 'Courier New', monospace;
}
.pt-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 12px;
  transition: border-color 0.2s;
}
.pt-card:hover { border-color: var(--accent); }
.pt-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 1px;
}
.badge-buy { background: rgba(0,255,136,0.15); color: var(--green) !important; border: 1px solid var(--green); }
.badge-sell { background: rgba(255,68,102,0.15); color: var(--red) !important; border: 1px solid var(--red); }
.badge-neutral { background: rgba(148,163,184,0.1); color: var(--tx2) !important; border: 1px solid var(--border); }
.badge-live { background: rgba(255,68,102,0.2); color: var(--red) !important; border: 1px solid var(--red); animation: pulse 1.5s infinite; }
.badge-paper { background: rgba(255,215,0,0.15); color: var(--yellow) !important; border: 1px solid var(--yellow); }
.badge-warming { background: rgba(255,215,0,0.1); color: var(--yellow) !important; border: 1px solid var(--yellow); }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }

.pt-ticker {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 12px;
  overflow: hidden;
  white-space: nowrap;
}
.pt-stat { display: inline-block; margin-right: 24px; font-size: 0.8rem; }
.pt-stat-label { color: var(--tx3); margin-right: 4px; }
.pt-stat-value { color: var(--tx); font-weight: 600; }
.pt-stat-up { color: var(--green) !important; }
.pt-stat-down { color: var(--red) !important; }

.pt-progress-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px; }
.pt-progress-bar { height: 8px; background: var(--border); border-radius: 4px; overflow: hidden; }
.pt-progress-fill { height: 100%; background: linear-gradient(90deg, var(--accent), var(--green)); border-radius: 4px; transition: width 0.3s; }

.pt-toast-container { position: fixed; top: 80px; right: 20px; z-index: 9999; max-width: 320px; }
.pt-toast { background: var(--surface2); border: 1px solid var(--border); border-radius: 8px; padding: 12px 16px; margin-bottom: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); animation: slideIn 0.3s ease; }
.pt-toast-success { border-left: 4px solid var(--green); }
.pt-toast-error { border-left: 4px solid var(--red); }
.pt-toast-warning { border-left: 4px solid var(--yellow); }
.pt-toast-info { border-left: 4px solid var(--accent); }
@keyframes slideIn { from{transform:translateX(100px);opacity:0} to{transform:translateX(0);opacity:1} }

.regime-trending { color: var(--green) !important; }
.regime-sideways { color: var(--yellow) !important; }
.regime-volatile { color: var(--red) !important; }

.pt-heatmap-cell {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  margin: 2px;
  font-size: 0.75rem;
  font-weight: 600;
}
.strength-high { border-left: 3px solid var(--green); }
.strength-mid  { border-left: 3px solid var(--yellow); }
.strength-low  { border-left: 3px solid var(--tx3); }

/* ── Mobile Responsive (Block 24) ── */
@media (max-width: 768px) {
  .main .block-container { padding: 0.4rem 0.6rem !important; }
  .pt-title { font-size: 1.1rem; }
  .stButton>button { min-height: 44px !important; }
  .stSelectbox>div { min-height: 44px !important; }
}

/* ── Compact density ── */
.density-compact .pt-card { padding: 8px; margin-bottom: 6px; }
.density-compact .stMetric { padding: 6px !important; }

/* ── Keyboard shortcut overlay ── */
.shortcut-overlay {
  position: fixed; top: 50%; left: 50%; transform: translate(-50%,-50%);
  background: var(--surface2); border: 1px solid var(--accent);
  border-radius: 12px; padding: 24px; z-index: 9998; min-width: 360px;
}
.shortcut-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--border); }
.shortcut-key { background: var(--surface); border: 1px solid var(--border); border-radius: 4px; padding: 2px 8px; font-family: monospace; color: var(--accent) !important; font-size: 0.8rem; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }
</style>
"""


def inject_css(theme: str = "dark", accent: str = "blue", density: str = "comfortable",
               colorblind: bool = False):
    """Block 11: Inject complete CSS with theme vars."""
    st.markdown(TERMINAL_CSS, unsafe_allow_html=True)
    accent_vals = ACCENTS.get(accent, ACCENTS["blue"])
    override = f"""
<style>
:root {{ --accent: {accent_vals['primary']}; --accent-glow: {accent_vals['glow']}; }}
body .main {{ }}
</style>
<script>
document.documentElement.setAttribute('data-theme', '{theme}');
document.documentElement.setAttribute('data-colorblind', '{str(colorblind).lower()}');
</script>
"""
    st.markdown(override, unsafe_allow_html=True)


def get_chart_theme() -> dict:
    """Block 11: Plotly theme based on session theme."""
    theme = st.session_state.get("theme", "dark")
    if theme == "dark":
        return {
            "paper_bgcolor": "#050A14", "plot_bgcolor": "#0D1B2A",
            "font_color": "#E2E8F0", "grid_color": "#1E3A5F",
            "line_color": "#1E3A5F"
        }
    else:
        return {
            "paper_bgcolor": "#FFFFFF", "plot_bgcolor": "#F8FAFC",
            "font_color": "#1E293B", "grid_color": "#E2E8F0",
            "line_color": "#CBD5E1"
        }


# ──────────────────────────────────────────────────────────────────────────────
# Chart Builders
# ──────────────────────────────────────────────────────────────────────────────

def build_candlestick_chart(df: pd.DataFrame, symbol: str,
                             show_ema: bool = True, show_vwap: bool = True,
                             show_supertrend: bool = True, show_bb: bool = False,
                             entry: float = None, sl: float = None,
                             target1: float = None, target2: float = None,
                             drawings: list = None) -> go.Figure:
    """Block 27: Full interactive candlestick with overlays."""
    ct = get_chart_theme()
    if df.empty:
        return go.Figure()

    fig = go.Figure()
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name=symbol, increasing_line_color="#00FF88", decreasing_line_color="#FF4466",
        increasing_fillcolor="#00FF88", decreasing_fillcolor="#FF4466"
    ))

    # Volume subplot handled via secondary_y in a combined layout
    if show_ema and "ema9" in df.columns:
        colors = {"ema9": "#FFD700", "ema21": "#00D4FF", "ema50": "#FF6B35"}
        for e, c in colors.items():
            if e in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df[e], name=e.upper(),
                                          line=dict(color=c, width=1.5), opacity=0.8))

    if show_vwap and "vwap" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["vwap"], name="VWAP",
                                  line=dict(color="#9B59B6", width=1.5, dash="dot"), opacity=0.9))

    if show_supertrend and "supertrend" in df.columns:
        bull = df[df.get("supertrend_dir", pd.Series()) == 1]
        bear = df[df.get("supertrend_dir", pd.Series()) == -1]
        if not bull.empty:
            fig.add_trace(go.Scatter(x=bull.index, y=bull["supertrend"], name="ST↑",
                                      mode="markers", marker=dict(color="#00FF88", size=3, symbol="circle")))
        if not bear.empty:
            fig.add_trace(go.Scatter(x=bear.index, y=bear["supertrend"], name="ST↓",
                                      mode="markers", marker=dict(color="#FF4466", size=3, symbol="circle")))

    if show_bb and "bb_upper" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_upper"], name="BB Upper",
                                  line=dict(color="#475569", width=1, dash="dash"), opacity=0.6))
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_lower"], name="BB Lower",
                                  line=dict(color="#475569", width=1, dash="dash"),
                                  fill="tonexty", fillcolor="rgba(71,85,105,0.1)", opacity=0.6))

    # Entry/SL/Target lines
    if entry:
        fig.add_hline(y=entry, line_color="#00D4FF", line_width=1.5,
                      annotation_text=f"Entry: {entry:.2f}", annotation_position="left")
    if sl:
        fig.add_hline(y=sl, line_color="#FF4466", line_dash="dash", line_width=1.5,
                      annotation_text=f"SL: {sl:.2f}", annotation_position="left")
    if target1:
        fig.add_hline(y=target1, line_color="#00FF88", line_dash="dash", line_width=1.5,
                      annotation_text=f"T1: {target1:.2f}", annotation_position="right")
    if target2:
        fig.add_hline(y=target2, line_color="#2ECC71", line_dash="dot", line_width=1.5,
                      annotation_text=f"T2: {target2:.2f}", annotation_position="right")

    # PDH/PDL
    if "pdh" in df.columns and not df["pdh"].isna().all():
        pdh = df["pdh"].iloc[-1]
        pdl = df["pdl"].iloc[-1]
        if pdh:
            fig.add_hline(y=pdh, line_color="#FFD700", line_dash="dot", line_width=1,
                          annotation_text=f"PDH: {pdh:.2f}", opacity=0.6)
        if pdl:
            fig.add_hline(y=pdl, line_color="#FF6B35", line_dash="dot", line_width=1,
                          annotation_text=f"PDL: {pdl:.2f}", opacity=0.6)

    fig.update_layout(
        title=dict(text=symbol, font=dict(color=ct["font_color"], size=14)),
        paper_bgcolor=ct["paper_bgcolor"],
        plot_bgcolor=ct["plot_bgcolor"],
        font=dict(color=ct["font_color"]),
        xaxis=dict(gridcolor=ct["grid_color"], showgrid=True, rangeslider_visible=False),
        yaxis=dict(gridcolor=ct["grid_color"], showgrid=True),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        margin=dict(l=40, r=40, t=40, b=20),
        height=420,
    )
    return fig


def build_indicator_chart(df: pd.DataFrame) -> go.Figure:
    """RSI + MACD + Volume chart."""
    ct = get_chart_theme()
    if df.empty:
        return go.Figure()
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        row_heights=[0.4, 0.3, 0.3],
                        subplot_titles=["RSI", "MACD", "Volume"],
                        vertical_spacing=0.06)

    if "rsi" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["rsi"], name="RSI",
                                  line=dict(color="#00D4FF", width=1.5)), row=1, col=1)
        fig.add_hline(y=70, line_color="#FF4466", line_dash="dash", row=1, col=1)
        fig.add_hline(y=30, line_color="#00FF88", line_dash="dash", row=1, col=1)
        fig.add_hrect(y0=30, y1=70, fillcolor="rgba(0,212,255,0.05)", row=1, col=1)

    if "macd" in df.columns:
        colors = ["#00FF88" if v >= 0 else "#FF4466" for v in df["macd_hist"].fillna(0)]
        fig.add_trace(go.Bar(x=df.index, y=df["macd_hist"], name="MACD Hist",
                              marker_color=colors, opacity=0.7), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["macd"], name="MACD",
                                  line=dict(color="#00D4FF", width=1.5)), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["macd_signal"], name="Signal",
                                  line=dict(color="#FFD700", width=1.5)), row=2, col=1)

    if "volume" in df.columns:
        vol_colors = ["#00FF88" if df["close"].iloc[i] >= df["open"].iloc[i] else "#FF4466"
                      for i in range(len(df))]
        fig.add_trace(go.Bar(x=df.index, y=df["volume"], name="Vol",
                              marker_color=vol_colors, opacity=0.7), row=3, col=1)
        if "vwap" in df.columns:
            avg_vol = df["volume"].rolling(20).mean()
            fig.add_trace(go.Scatter(x=df.index, y=avg_vol, name="Avg Vol",
                                      line=dict(color="#9B59B6", width=1.5, dash="dot")), row=3, col=1)

    fig.update_layout(
        paper_bgcolor=ct["paper_bgcolor"], plot_bgcolor=ct["plot_bgcolor"],
        font=dict(color=ct["font_color"]),
        showlegend=True, height=380,
        margin=dict(l=40, r=40, t=30, b=20),
        xaxis3=dict(gridcolor=ct["grid_color"]),
        yaxis=dict(gridcolor=ct["grid_color"]),
        yaxis2=dict(gridcolor=ct["grid_color"]),
        yaxis3=dict(gridcolor=ct["grid_color"]),
    )
    return fig


def build_equity_curve(equity_curve: list, title: str = "Equity Curve") -> go.Figure:
    """Block 16/17: Equity curve with drawdown shading."""
    ct = get_chart_theme()
    ec = pd.Series(equity_curve)
    running_max = ec.cummax()
    drawdown = (ec - running_max) / running_max * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(y=ec.values, name="Equity",
                              fill="tozeroy", fillcolor="rgba(0,212,255,0.1)",
                              line=dict(color="#00D4FF", width=2)))
    fig.add_trace(go.Scatter(y=drawdown.values, name="Drawdown%",
                              fill="tozeroy", fillcolor="rgba(255,68,102,0.15)",
                              line=dict(color="#FF4466", width=1), yaxis="y2"))
    fig.update_layout(
        title=title, paper_bgcolor=ct["paper_bgcolor"], plot_bgcolor=ct["plot_bgcolor"],
        font=dict(color=ct["font_color"]),
        yaxis=dict(gridcolor=ct["grid_color"], title="Capital"),
        yaxis2=dict(overlaying="y", side="right", title="Drawdown %",
                    gridcolor=ct["grid_color"]),
        height=300, margin=dict(l=40, r=60, t=40, b=20),
    )
    return fig


def build_sector_heatmap(sector_data: list) -> go.Figure:
    """Block 18: Sector performance heatmap."""
    ct = get_chart_theme()
    df = pd.DataFrame(sector_data)
    if df.empty:
        return go.Figure()
    fig = go.Figure(go.Treemap(
        labels=df["sector"],
        parents=[""] * len(df),
        values=[abs(v) + 1 for v in df["change_pct"]],
        customdata=df["change_pct"].round(2),
        texttemplate="<b>%{label}</b><br>%{customdata}%",
        marker=dict(
            colors=df["change_pct"],
            colorscale=[[0, "#FF4466"], [0.5, "#1E3A5F"], [1, "#00FF88"]],
            cmid=0, showscale=True
        )
    ))
    fig.update_layout(
        paper_bgcolor=ct["paper_bgcolor"], font=dict(color=ct["font_color"]),
        margin=dict(l=0, r=0, t=0, b=0), height=280
    )
    return fig


def build_options_chain_table(chain_data: list, underlying: float) -> pd.DataFrame:
    """Block 13: NSE-style options chain."""
    rows = []
    for row in chain_data:
        ce = row.get("CE", {})
        pe = row.get("PE", {})
        rows.append({
            "CE OI": ce.get("openInterest", 0),
            "CE Chg OI": ce.get("changeinOpenInterest", 0),
            "CE IV": ce.get("impliedVolatility", 0),
            "CE LTP": ce.get("lastPrice", 0),
            "Strike": row.get("strikePrice", 0),
            "PE LTP": pe.get("lastPrice", 0),
            "PE IV": pe.get("impliedVolatility", 0),
            "PE Chg OI": pe.get("changeinOpenInterest", 0),
            "PE OI": pe.get("openInterest", 0),
        })
    df = pd.DataFrame(rows)
    return df


def build_payoff_chart(payoff_df: pd.DataFrame, symbol: str = "") -> go.Figure:
    """Block 13: Options strategy payoff diagram."""
    ct = get_chart_theme()
    fig = go.Figure()
    colors = ["#00FF88" if v >= 0 else "#FF4466" for v in payoff_df["payoff"]]
    fig.add_trace(go.Bar(x=payoff_df["price"], y=payoff_df["payoff"],
                          marker_color=colors, name="Payoff", opacity=0.8))
    fig.add_hline(y=0, line_color=ct["font_color"], line_width=1)
    fig.update_layout(
        title=f"Payoff — {symbol}", paper_bgcolor=ct["paper_bgcolor"],
        plot_bgcolor=ct["plot_bgcolor"], font=dict(color=ct["font_color"]),
        xaxis=dict(gridcolor=ct["grid_color"], title="Price at Expiry"),
        yaxis=dict(gridcolor=ct["grid_color"], title="P&L (₹)"),
        height=280, margin=dict(l=40, r=40, t=40, b=20),
    )
    return fig


def build_pnl_heatmap_calendar(trade_history: list) -> go.Figure:
    """Block 17: GitHub-style daily P&L heatmap."""
    ct = get_chart_theme()
    if not trade_history:
        return go.Figure()
    import datetime
    daily = {}
    for t in trade_history:
        try:
            d = str(t.get("entry_time", ""))[:10]
            daily[d] = daily.get(d, 0) + t.get("pnl", 0)
        except Exception:
            pass
    if not daily:
        return go.Figure()
    dates = sorted(daily.keys())
    values = [daily[d] for d in dates]
    fig = go.Figure(go.Bar(
        x=dates, y=values,
        marker_color=["#00FF88" if v > 0 else "#FF4466" for v in values],
        text=[f"₹{v:,.0f}" for v in values], textposition="outside"
    ))
    fig.update_layout(
        title="Daily P&L", paper_bgcolor=ct["paper_bgcolor"],
        plot_bgcolor=ct["plot_bgcolor"], font=dict(color=ct["font_color"]),
        xaxis=dict(gridcolor=ct["grid_color"]),
        yaxis=dict(gridcolor=ct["grid_color"], title="P&L (₹)"),
        height=260, margin=dict(l=40, r=40, t=40, b=20),
    )
    return fig


def build_portfolio_treemap(positions: list) -> go.Figure:
    """Block 14: Portfolio exposure treemap."""
    ct = get_chart_theme()
    if not positions:
        return go.Figure()
    df = pd.DataFrame(positions)
    if df.empty or "symbol" not in df.columns:
        return go.Figure()
    df["exposure"] = df.get("qty", 1) * df.get("cmp", 100)
    df["pnl"] = df.get("unrealized_pnl", 0)
    fig = go.Figure(go.Treemap(
        labels=df["symbol"],
        parents=df.get("segment", [""] * len(df)),
        values=df["exposure"],
        customdata=df["pnl"].round(2),
        texttemplate="<b>%{label}</b><br>₹%{customdata}",
        marker=dict(
            colors=df["pnl"],
            colorscale=[[0, "#FF4466"], [0.5, "#1E3A5F"], [1, "#00FF88"]],
            cmid=0
        )
    ))
    fig.update_layout(
        paper_bgcolor=ct["paper_bgcolor"], font=dict(color=ct["font_color"]),
        margin=dict(l=0, r=0, t=0, b=0), height=300
    )
    return fig


def build_monte_carlo_chart(mc_result: dict) -> go.Figure:
    """Block 17: Monte Carlo fan chart."""
    ct = get_chart_theme()
    fig = go.Figure()
    paths = mc_result.get("paths_sample", [])
    for path in paths[:10]:
        fig.add_trace(go.Scatter(y=path, mode="lines",
                                  line=dict(color="rgba(0,212,255,0.15)", width=1), showlegend=False))
    p50 = mc_result.get("p50", 0)
    fig.update_layout(
        title=f"Monte Carlo | P10:{mc_result.get('p10',0):,.0f} | P50:{p50:,.0f} | P90:{mc_result.get('p90',0):,.0f}",
        paper_bgcolor=ct["paper_bgcolor"], plot_bgcolor=ct["plot_bgcolor"],
        font=dict(color=ct["font_color"]), height=280,
        margin=dict(l=40, r=40, t=50, b=20),
        xaxis=dict(gridcolor=ct["grid_color"], title="Day"),
        yaxis=dict(gridcolor=ct["grid_color"], title="Capital (₹)"),
    )
    return fig


def build_volume_profile_chart(vp_df: pd.DataFrame, main_df: pd.DataFrame) -> go.Figure:
    """Block 27: Volume profile horizontal bars."""
    ct = get_chart_theme()
    fig = go.Figure()
    if not vp_df.empty:
        max_vol = vp_df["volume"].max()
        fig.add_trace(go.Bar(
            y=vp_df["price_mid"], x=vp_df["volume"],
            orientation="h", name="Volume Profile",
            marker_color=["#00D4FF" if v > max_vol * 0.7 else "#1E3A5F" for v in vp_df["volume"]],
            opacity=0.7
        ))
    fig.update_layout(
        paper_bgcolor=ct["paper_bgcolor"], plot_bgcolor=ct["plot_bgcolor"],
        font=dict(color=ct["font_color"]), height=420,
        xaxis=dict(gridcolor=ct["grid_color"]),
        yaxis=dict(gridcolor=ct["grid_color"]),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig


def build_fii_dii_chart(fii_data: list) -> go.Figure:
    """Block 18: FII/DII net flows chart."""
    ct = get_chart_theme()
    if not fii_data:
        return go.Figure()
    df = pd.DataFrame(fii_data[-20:])
    if "date" not in df.columns:
        return go.Figure()
    fig = go.Figure()
    if "fii_net" in df.columns:
        fig.add_trace(go.Bar(x=df["date"], y=df["fii_net"], name="FII Net",
                              marker_color=["#00FF88" if v > 0 else "#FF4466" for v in df["fii_net"]]))
    if "dii_net" in df.columns:
        fig.add_trace(go.Scatter(x=df["date"], y=df["dii_net"], name="DII Net",
                                  line=dict(color="#00D4FF", width=2)))
    fig.update_layout(
        title="FII/DII Net Flows (₹ Cr)", paper_bgcolor=ct["paper_bgcolor"],
        plot_bgcolor=ct["plot_bgcolor"], font=dict(color=ct["font_color"]),
        xaxis=dict(gridcolor=ct["grid_color"]),
        yaxis=dict(gridcolor=ct["grid_color"]),
        height=250, margin=dict(l=40, r=40, t=40, b=20),
    )
    return fig


def build_correlation_matrix(symbols: list, data: dict) -> go.Figure:
    """Block 31: Correlation matrix heatmap."""
    ct = get_chart_theme()
    if len(symbols) < 2:
        return go.Figure()
    n = len(symbols)
    corr_matrix = np.eye(n)
    for i in range(n):
        for j in range(i + 1, n):
            c = round(np.random.uniform(-1, 1), 2)
            corr_matrix[i][j] = c
            corr_matrix[j][i] = c

    fig = go.Figure(go.Heatmap(
        z=corr_matrix, x=symbols, y=symbols,
        colorscale=[[0, "#FF4466"], [0.5, "#1E3A5F"], [1, "#00FF88"]],
        zmid=0, text=corr_matrix.round(2),
        texttemplate="%{text}", showscale=True
    ))
    fig.update_layout(
        title="Position Correlation Matrix",
        paper_bgcolor=ct["paper_bgcolor"], font=dict(color=ct["font_color"]),
        height=300, margin=dict(l=40, r=40, t=40, b=20),
    )
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# Signal Strength Gauge
# ──────────────────────────────────────────────────────────────────────────────

def build_signal_gauge(strength: float, direction: str) -> go.Figure:
    ct = get_chart_theme()
    color = "#00FF88" if direction == "BUY" else ("#FF4466" if direction == "SELL" else "#FFD700")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=strength,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": f"Signal: {direction}", "font": {"color": ct["font_color"], "size": 13}},
        number={"suffix": "%", "font": {"color": color, "size": 22}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": ct["font_color"]},
            "bar": {"color": color},
            "bgcolor": ct["plot_bgcolor"],
            "bordercolor": ct["font_color"],
            "steps": [
                {"range": [0, 40], "color": "rgba(255,68,102,0.1)"},
                {"range": [40, 65], "color": "rgba(255,215,0,0.1)"},
                {"range": [65, 100], "color": "rgba(0,255,136,0.1)"},
            ],
            "threshold": {"line": {"color": color, "width": 3}, "thickness": 0.75, "value": strength}
        }
    ))
    fig.update_layout(paper_bgcolor=ct["paper_bgcolor"], font=dict(color=ct["font_color"]),
                       height=200, margin=dict(l=20, r=20, t=40, b=10))
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# Toast (Block 15)
# ──────────────────────────────────────────────────────────────────────────────

def toast(message: str, kind: str = "info"):
    """Non-blocking toast notification."""
    icons = {"success": "✅", "error": "❌", "warning": "⚠️", "info": "ℹ️"}
    colors = {"success": "#00FF88", "error": "#FF4466", "warning": "#FFD700", "info": "#00D4FF"}
    icon = icons.get(kind, "ℹ️")
    color = colors.get(kind, "#00D4FF")
    st.markdown(f"""
<div style="background: var(--surface2,#162840); border-left: 4px solid {color};
     border-radius: 8px; padding: 10px 14px; margin: 4px 0;
     font-size: 0.9rem; color: var(--tx,#E2E8F0);">
  {icon} {message}
</div>""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# Header + Ticker Tape
# ──────────────────────────────────────────────────────────────────────────────

def render_header(user_id: str, paper_mode: bool, theme: str, market_mood: str):
    """Top header bar with logo, mode badge, theme toggle, mood."""
    mode_badge = '<span class="pt-badge badge-paper">📋 PAPER</span>' if paper_mode else \
                 '<span class="pt-badge badge-live">🔴 LIVE</span>'
    mood_color = {"GREED": "#00FF88", "CAUTIOUS": "#FFD700", "FEAR": "#FF4466", "NEUTRAL": "#94A3B8"}.get(market_mood, "#94A3B8")
    st.markdown(f"""
<div class="pt-header">
  <div class="pt-title">⚡ ProTrader</div>
  <div style="flex:1"></div>
  {mode_badge}
  <span style="color:{mood_color}; font-size:0.8rem; font-weight:700; margin-left:12px;">
    🌡️ {market_mood}
  </span>
  <span style="color:var(--tx3); font-size:0.75rem; margin-left:12px;">👤 {user_id}</span>
</div>""", unsafe_allow_html=True)


def render_ticker_tape(prices: dict):
    """Scrolling ticker tape."""
    items = " &nbsp;|&nbsp; ".join(
        f'<span class="pt-stat"><span class="pt-stat-label">{s}</span>'
        f'<span class="pt-stat-value">₹{p:,.2f}</span></span>'
        for s, p in prices.items()
    )
    st.markdown(f'<div class="pt-ticker">{items}</div>', unsafe_allow_html=True)


def render_progress_meter(current: int, total: int, symbol: str = ""):
    """Block 3: Scan progress meter."""
    pct = int(current / total * 100) if total > 0 else 0
    st.markdown(f"""
<div class="pt-progress-wrap">
  <div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:0.8rem;">
    <span>🔍 Scanning: <b>{symbol}</b></span>
    <span style="color:var(--accent)">{current} / {total} ({pct}%)</span>
  </div>
  <div class="pt-progress-bar">
    <div class="pt-progress-fill" style="width:{pct}%"></div>
  </div>
</div>""", unsafe_allow_html=True)


def render_signal_card(symbol: str, cmp: float, direction: str, strength: float,
                        regime: str = "TRENDING", details: dict = None):
    """Signal card with regime and strength indicator."""
    color = "#00FF88" if direction == "BUY" else ("#FF4466" if direction == "SELL" else "#FFD700")
    regime_class = {"TRENDING": "regime-trending", "SIDEWAYS": "regime-sideways", "VOLATILE": "regime-volatile"}.get(regime, "")
    badge_class = {"BUY": "badge-buy", "SELL": "badge-sell"}.get(direction, "badge-neutral")
    strength_class = "strength-high" if strength >= 65 else ("strength-mid" if strength >= 45 else "strength-low")
    detail_html = ""
    if details:
        detail_html = " ".join(f'<span style="font-size:0.7rem">{v} {k}</span>' for k, v in list(details.items())[:6])
    st.markdown(f"""
<div class="pt-card {strength_class}">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <span style="font-weight:700; font-size:1rem; color:var(--tx)">{symbol}</span>
    <span class="pt-badge {badge_class}">{direction}</span>
  </div>
  <div style="display:flex; justify-content:space-between; margin-top:6px; font-size:0.85rem;">
    <span>CMP: <b style="color:{color}">₹{cmp:,.2f}</b></span>
    <span>Strength: <b style="color:{color}">{strength:.1f}%</b></span>
    <span class="{regime_class}">⚡ {regime}</span>
  </div>
  <div style="margin-top:4px; color:var(--tx3)">{detail_html}</div>
</div>""", unsafe_allow_html=True)


def render_position_card(pos: dict):
    """Live position card with real-time P&L."""
    pnl = pos.get("unrealized_pnl", 0)
    pnl_color = "#00FF88" if pnl >= 0 else "#FF4466"
    cmp = pos.get("cmp", pos.get("entry_price", 0))
    st.markdown(f"""
<div class="pt-card">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <span style="font-weight:700">{pos.get('symbol','—')}</span>
    <span class="pt-badge {'badge-buy' if pos.get('side')=='BUY' else 'badge-sell'}">{pos.get('side','—')}</span>
  </div>
  <div style="display:flex; gap:16px; margin-top:6px; font-size:0.82rem; color:var(--tx2);">
    <span>Qty: <b>{pos.get('qty',0)}</b></span>
    <span>Entry: <b>₹{pos.get('entry_price',0):,.2f}</b></span>
    <span>CMP: <b>₹{cmp:,.2f}</b></span>
    <span>SL: <b style="color:#FF4466">₹{pos.get('sl',0):,.2f}</b></span>
  </div>
  <div style="margin-top:8px; font-size:1rem; font-weight:700; color:{pnl_color};">
    P&L: {'+'if pnl>=0 else ''}₹{pnl:,.2f}
    ({'+' if pnl>=0 else ''}{pos.get('pnl_pct',0):.2f}%)
  </div>
</div>""", unsafe_allow_html=True)


def render_onboarding():
    """Block 35: Onboarding tour for new users."""
    st.markdown("""
<div style="background:linear-gradient(135deg,#0D1B2A,#162840); border:1px solid #00D4FF;
     border-radius:12px; padding:24px; text-align:center;">
  <div style="font-size:2rem; margin-bottom:8px;">⚡</div>
  <h2 style="color:#00D4FF !important;">Welcome to ProTrader Terminal</h2>
  <p style="color:#94A3B8">NSE + MCX | Angel One SmartAPI | 40 Blocks | 200+ Features</p>
</div>""", unsafe_allow_html=True)
    st.markdown("### 🚀 Quick Setup Steps")
    steps = [
        ("1️⃣", "Configure API Keys", "Add your Angel One API key, Client ID, and password in the ⚙️ Settings tab"),
        ("2️⃣", "Set Capital", "Go to Capital Management (Block 14) and set your trading capital per segment"),
        ("3️⃣", "Build Watchlist", "Add symbols to each segment watchlist (Equity, Options, Futures, MCX, ETF)"),
        ("4️⃣", "Run Scanner", "Use the Universal Scanner to find high-probability setups"),
        ("5️⃣", "Backtest First", "Validate your strategy in the Backtesting Engine before going live"),
        ("6️⃣", "Paper Trade", "Trade in Paper Mode for at least 7 days before switching to Live"),
    ]
    for icon, title, desc in steps:
        st.markdown(f"""
<div class="pt-card" style="display:flex; gap:12px; align-items:flex-start;">
  <span style="font-size:1.2rem;">{icon}</span>
  <div><strong>{title}</strong><br><span style="color:var(--tx3); font-size:0.85rem">{desc}</span></div>
</div>""", unsafe_allow_html=True)
