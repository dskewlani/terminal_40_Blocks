"""
components/widgets.py — ProTrader Terminal v2.0
Reusable Streamlit widgets used across all 40 blocks.
"""

import streamlit as st
import pandas as pd
import datetime
from typing import Optional, List


# ─── Market Clock (Block 12) ──────────────────────────────────────────────────

def market_clock_widget():
    """Block 12: Live market session indicator."""
    now = datetime.datetime.now()
    h, m = now.hour, now.minute
    t = h * 60 + m

    sessions = [
        (9*60, 9*60+15, "🌅 Pre-Open", "#FFD700"),
        (9*60+15, 9*60+30, "⚠️ Volatile Open", "#FF6B35"),
        (9*60+30, 14*60+30, "✅ Normal Trading", "#00FF88"),
        (14*60+30, 15*60, "⚠️ Near Close", "#FFD700"),
        (15*60, 15*60+30, "🔔 Closing Session", "#FF4466"),
        (20*60, 23*60+30, "⚗️ MCX Session", "#00D4FF"),
    ]

    label, color = "🌙 Market Closed", "#475569"
    for start, end, lbl, col in sessions:
        if start <= t < end:
            label, color = lbl, col
            break

    # MCX override
    if 20*60 <= t <= 23*60+30:
        label, color = "⚗️ MCX Evening Session", "#00D4FF"

    st.markdown(f"""
<div style="background:var(--surface,#0F2035); border:1px solid var(--border,#1E3A5F);
     border-left:4px solid {color}; border-radius:8px; padding:10px 14px;
     display:flex; justify-content:space-between; align-items:center;">
  <span style="color:{color}; font-weight:700; font-size:0.9rem;">{label}</span>
  <span style="color:var(--tx3,#475569); font-size:0.8rem; font-family:monospace;">
    {now.strftime('%H:%M:%S IST')}
  </span>
</div>""", unsafe_allow_html=True)


# ─── Regime Badge (Block 9) ───────────────────────────────────────────────────

def regime_badge(regime: str):
    """Block 9: Market regime visual badge."""
    config = {
        "TRENDING": ("⚡ TRENDING", "#00FF88", "rgba(0,255,136,0.1)"),
        "SIDEWAYS": ("↔️ SIDEWAYS", "#FFD700", "rgba(255,215,0,0.1)"),
        "VOLATILE": ("🌪️ VOLATILE", "#FF4466", "rgba(255,68,102,0.1)"),
    }
    label, color, bg = config.get(regime, ("❓ UNKNOWN", "#94A3B8", "rgba(148,163,184,0.1)"))
    st.markdown(f"""
<span style="background:{bg}; border:1px solid {color}; color:{color};
     border-radius:20px; padding:3px 12px; font-size:0.75rem; font-weight:700;
     letter-spacing:1px;">{label}</span>""", unsafe_allow_html=True)


# ─── PnL Dashboard (Block 14/17) ─────────────────────────────────────────────

def pnl_dashboard(daily_pnl: float, daily_goal: float,
                   daily_loss_limit: float, trades_today: int,
                   max_trades: int, win_streak: int, loss_streak: int):
    """Block 14: Compact P&L dashboard row."""
    pnl_color = "#00FF88" if daily_pnl >= 0 else "#FF4466"
    goal_pct = min(daily_pnl / daily_goal * 100, 150) if daily_goal > 0 else 0
    loss_pct = min(abs(min(0, daily_pnl)) / daily_loss_limit * 100, 100) if daily_loss_limit > 0 else 0

    st.markdown(f"""
<div style="background:var(--surface,#0F2035); border:1px solid var(--border,#1E3A5F);
     border-radius:10px; padding:12px 16px; margin-bottom:12px;">
  <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:10px;">
    <div>
      <div style="color:var(--tx3,#475569); font-size:0.7rem;">TODAY'S P&L</div>
      <div style="color:{pnl_color}; font-size:1.3rem; font-weight:800;">
        {'+'if daily_pnl>=0 else ''}₹{daily_pnl:,.0f}
      </div>
    </div>
    <div>
      <div style="color:var(--tx3,#475569); font-size:0.7rem;">GOAL PROGRESS</div>
      <div style="color:var(--tx,#E2E8F0); font-size:1.1rem; font-weight:700;">
        {goal_pct:.0f}% of ₹{daily_goal:,.0f}
      </div>
    </div>
    <div>
      <div style="color:var(--tx3,#475569); font-size:0.7rem;">TRADES</div>
      <div style="color:var(--tx,#E2E8F0); font-size:1.1rem; font-weight:700;">
        {trades_today} / {max_trades}
      </div>
    </div>
    <div>
      <div style="color:var(--tx3,#475569); font-size:0.7rem;">STREAK</div>
      <div style="color:{'#00FF88' if win_streak>0 else '#FF4466'}; font-size:1.1rem; font-weight:700;">
        {'🟢' if win_streak>0 else '🔴'} {win_streak if win_streak>0 else loss_streak}
      </div>
    </div>
  </div>
  <div style="height:6px; background:var(--border,#1E3A5F); border-radius:3px; overflow:hidden;">
    <div style="height:100%; width:{goal_pct:.0f}%;
         background:linear-gradient(90deg,#00D4FF,{pnl_color}); border-radius:3px;"></div>
  </div>
  <div style="display:flex; justify-content:space-between; margin-top:4px; font-size:0.7rem; color:var(--tx3,#475569);">
    <span>Loss limit used: {loss_pct:.0f}%</span>
    <span>₹{daily_loss_limit:,.0f} limit</span>
  </div>
</div>""", unsafe_allow_html=True)


# ─── Signal Scorecard (Block 9) ───────────────────────────────────────────────

def signal_scorecard(details: dict, direction: str):
    """Block 9: Detailed signal scorecard showing each indicator verdict."""
    bull_count = sum(1 for v in details.values() if v == "✅")
    total = len(details)
    pct = bull_count / total * 100 if total > 0 else 0
    color = "#00FF88" if direction == "BUY" else ("#FF4466" if direction == "SELL" else "#FFD700")

    rows_html = ""
    for k, v in details.items():
        rows_html += f"""
    <div style="display:flex; justify-content:space-between; padding:3px 0;
         border-bottom:1px solid var(--border,#1E3A5F); font-size:0.78rem;">
      <span style="color:var(--tx2,#94A3B8);">{k}</span>
      <span>{v}</span>
    </div>"""

    st.markdown(f"""
<div style="background:var(--surface,#0F2035); border:1px solid {color};
     border-radius:10px; padding:14px; margin-bottom:8px;">
  <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
    <span style="font-weight:700; color:{color};">{direction} Signal</span>
    <span style="color:{color}; font-weight:800; font-size:1.1rem;">{pct:.0f}%</span>
  </div>
  <div style="height:4px; background:var(--border,#1E3A5F); border-radius:2px; margin-bottom:10px;">
    <div style="width:{pct:.0f}%; height:100%; background:{color}; border-radius:2px;"></div>
  </div>
  {rows_html}
</div>""", unsafe_allow_html=True)


# ─── Position Sizing Widget (Block 14) ────────────────────────────────────────

def position_size_widget(capital: float, key_prefix: str = "ps") -> dict:
    """Block 14: Interactive position sizing calculator widget."""
    st.markdown("#### 📐 Position Size Calculator")
    col1, col2, col3, col4 = st.columns(4)
    price = col1.number_input("Entry Price (₹)", value=1000.0, step=10.0, key=f"{key_prefix}_price")
    sl = col2.number_input("Stop Loss (₹)", value=980.0, step=5.0, key=f"{key_prefix}_sl")
    risk_pct = col3.slider("Risk %", 0.25, 3.0, 1.0, 0.25, key=f"{key_prefix}_risk")
    atr = col4.number_input("ATR (₹)", value=20.0, step=1.0, key=f"{key_prefix}_atr")

    from utils.risk import fixed_fractional_size, risk_reward_ratio
    sl_distance = abs(price - sl)
    qty = fixed_fractional_size(capital, risk_pct, sl_distance, price)
    exposure = qty * price
    risk_amount = capital * risk_pct / 100
    target_1r = price + sl_distance * 2
    target_2r = price + sl_distance * 3
    rr = risk_reward_ratio(price, sl, target_1r)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Recommended Qty", qty)
    col2.metric("Exposure", f"₹{exposure:,.0f}", delta=f"{exposure/capital*100:.1f}% of capital")
    col3.metric("Risk Amount", f"₹{risk_amount:,.0f}")
    col4.metric("R:R @2R Target", f"{rr:.1f}x")

    return {"price": price, "sl": sl, "qty": qty, "exposure": exposure,
            "target_1r": target_1r, "target_2r": target_2r, "risk_pct": risk_pct}


# ─── Trade History Table (Block 22) ───────────────────────────────────────────

def trade_history_table(trades: list, show_charges: bool = False,
                          editable_notes: bool = False):
    """Block 22: Styled trade history table with P&L coloring."""
    if not trades:
        st.info("No trades yet.")
        return

    df = pd.DataFrame(trades)
    display_cols = ["symbol", "segment", "side", "entry_price", "exit_price",
                    "qty", "pnl", "net_pnl", "entry_time"]
    if show_charges:
        display_cols += ["charges"]
    existing = [c for c in display_cols if c in df.columns]
    df_display = df[existing].copy()

    # Format
    for col in ["entry_price", "exit_price", "pnl", "net_pnl", "charges"]:
        if col in df_display.columns:
            df_display[col] = df_display[col].apply(
                lambda x: f"₹{x:+,.2f}" if x is not None else "—"
            )
    if "entry_time" in df_display.columns:
        df_display["entry_time"] = df_display["entry_time"].astype(str).str[:16]

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "pnl": st.column_config.TextColumn("Gross P&L"),
            "net_pnl": st.column_config.TextColumn("Net P&L"),
        }
    )


# ─── Watchlist Quick Widget (Block 2) ─────────────────────────────────────────

def mini_watchlist(symbols: list, prices: dict, signals: dict = None):
    """Block 2: Compact watchlist for sidebar or small panels."""
    signals = signals or {}
    for sym in symbols[:10]:
        price = prices.get(sym, 0)
        sig = signals.get(sym, {})
        direction = sig.get("direction", "NEUTRAL")
        dot = "🟢" if direction == "BUY" else ("🔴" if direction == "SELL" else "⚪")
        st.markdown(f"""
<div style="display:flex; justify-content:space-between; padding:4px 0;
     border-bottom:1px solid var(--border,#1E3A5F); font-size:0.82rem;">
  <span>{dot} <b>{sym}</b></span>
  <span style="color:var(--tx,#E2E8F0);">₹{price:,.2f}</span>
</div>""", unsafe_allow_html=True)


# ─── Expiry Countdown (Block 5/13) ────────────────────────────────────────────

def expiry_countdown(expiry_date_str: str):
    """Block 5/13: Days to expiry countdown."""
    try:
        expiry = datetime.datetime.strptime(expiry_date_str, "%Y-%m-%d")
        now = datetime.datetime.now()
        dte = (expiry - now).days
        color = "#FF4466" if dte <= 3 else ("#FFD700" if dte <= 7 else "#00FF88")
        st.markdown(f"""
<div style="background:rgba(0,0,0,0.2); border:1px solid {color}; border-radius:6px;
     padding:6px 12px; text-align:center; font-size:0.8rem;">
  ⏳ Expiry: <b style="color:{color};">{dte} days</b>
  ({expiry.strftime('%d %b %Y')})
</div>""", unsafe_allow_html=True)
    except Exception:
        st.markdown(f"Expiry: {expiry_date_str}")


# ─── Risk Warning Banner (Block 30) ───────────────────────────────────────────

def risk_warning_banner(message: str, severity: str = "warning"):
    """Block 30: Full-width risk warning banner."""
    config = {
        "warning": ("#FFD700", "rgba(255,215,0,0.1)", "⚠️"),
        "danger": ("#FF4466", "rgba(255,68,102,0.1)", "🚨"),
        "info": ("#00D4FF", "rgba(0,212,255,0.1)", "ℹ️"),
    }
    color, bg, icon = config.get(severity, config["warning"])
    st.markdown(f"""
<div style="background:{bg}; border:1px solid {color}; border-radius:8px;
     padding:10px 16px; margin:8px 0; font-size:0.88rem; color:{color};">
  {icon} <strong>{message}</strong>
</div>""", unsafe_allow_html=True)


# ─── Keyboard Shortcuts Help (Block 35) ───────────────────────────────────────

def keyboard_shortcuts_help():
    """Block 35: Show keyboard shortcuts reference."""
    shortcuts = [
        ("S", "Open Scanner"),
        ("W", "Go to Watchlist"),
        ("T", "Quick Trade panel"),
        ("B", "Backtest"),
        ("A", "Analytics"),
        ("P", "Paper/Live toggle"),
        ("R", "Refresh prices"),
        ("?", "This help"),
    ]
    st.markdown("#### ⌨️ Keyboard Shortcuts")
    st.markdown("*(Available in desktop browser — click shortcut key while focused on app)*")
    for key, action in shortcuts:
        st.markdown(f"""
<div style="display:flex; justify-content:space-between; padding:5px 0;
     border-bottom:1px solid var(--border,#1E3A5F); font-size:0.85rem;">
  <span style="background:var(--surface2,#162840); border:1px solid var(--border,#1E3A5F);
        border-radius:4px; padding:1px 8px; font-family:monospace;
        color:var(--accent,#00D4FF);">{key}</span>
  <span style="color:var(--tx2,#94A3B8);">{action}</span>
</div>""", unsafe_allow_html=True)
