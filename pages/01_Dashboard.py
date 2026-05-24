"""
pages/01_Dashboard.py — ProTrader Terminal v2.0
Live Market Dashboard — the command-center view.
Blocks 12 (Pre/Post Market), 18 (Market Intelligence), 32 (Microstructure).
"""

import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="Dashboard | ProTrader", page_icon="🌐", layout="wide")

# Auth check
if not st.session_state.get("authenticated"):
    st.warning("Please login from the main page.")
    st.stop()

from engine import get_global_markets, get_market_mood, get_sector_performance, get_fii_dii_data
from utils.nse_data import (get_market_breadth, get_nifty50_heatmap, get_india_vix,
                              fear_greed_index, get_index_levels, get_sgx_nifty,
                              get_corporate_actions, get_upcoming_ipos)
from utils.mcx_data import get_mcx_demo_prices, is_mcx_session_active, get_mcx_expiry_calendar
from ui import inject_css, build_sector_heatmap, build_fii_dii_chart, get_chart_theme
from components.charts import nifty50_heatmap
from components.widgets import market_clock_widget, risk_warning_banner

inject_css(st.session_state.get("theme", "dark"), st.session_state.get("accent", "blue"))

st.markdown("## 🌐 Live Market Dashboard")
market_clock_widget()

# ── Row 1: Key Indices ────────────────────────────────────────────────────────
st.markdown("### 📊 Key Indices")
indices = get_index_levels()
cols = st.columns(len(indices) + 1)
for col, (name, data) in zip(cols, indices.items()):
    pchange = data.get("pchange", 0)
    color = "#00FF88" if pchange >= 0 else "#FF4466"
    col.markdown(f"""
<div style="background:var(--surface,#0F2035); border:1px solid var(--border,#1E3A5F);
     border-radius:8px; padding:10px; text-align:center;">
  <div style="color:var(--tx3,#475569); font-size:0.7rem;">{name}</div>
  <div style="color:var(--tx,#E2E8F0); font-size:1.1rem; font-weight:800;">
    {data.get('ltp', 0):,.2f}
  </div>
  <div style="color:{color}; font-size:0.85rem;">
    {pchange:+.2f}%
  </div>
</div>""", unsafe_allow_html=True)

# VIX
vix = get_india_vix()
vix_color = "#FF4466" if vix > 20 else ("#FFD700" if vix > 15 else "#00FF88")
cols[-1].markdown(f"""
<div style="background:var(--surface,#0F2035); border:1px solid {vix_color};
     border-radius:8px; padding:10px; text-align:center;">
  <div style="color:var(--tx3,#475569); font-size:0.7rem;">INDIA VIX</div>
  <div style="color:{vix_color}; font-size:1.1rem; font-weight:800;">{vix:.2f}</div>
  <div style="color:{vix_color}; font-size:0.8rem;">
    ±{vix/16:.1f}% expected daily move
  </div>
</div>""", unsafe_allow_html=True)

st.divider()

# ── Row 2: Fear & Greed + Breadth ─────────────────────────────────────────────
col1, col2, col3 = st.columns([1.5, 1.5, 2])

with col1:
    st.markdown("#### 😱 Fear & Greed Index")
    from engine import calculate_pcr, get_option_chain
    chain = get_option_chain("NIFTY")
    pcr = calculate_pcr(chain)
    breadth = get_market_breadth()
    fg = fear_greed_index(vix, breadth["ad_ratio"], pcr)
    score = fg["score"]
    fg_color = "#FF4466" if score < 30 else ("#FFD700" if score < 50 else ("#00D4FF" if score < 70 else "#00FF88"))
    st.markdown(f"""
<div style="background:var(--surface,#0F2035); border:2px solid {fg_color};
     border-radius:12px; padding:20px; text-align:center;">
  <div style="font-size:2.5rem;">{fg['emoji']}</div>
  <div style="font-size:2rem; font-weight:800; color:{fg_color};">{score:.0f}</div>
  <div style="color:{fg_color}; font-weight:700; font-size:0.9rem;">{fg['label']}</div>
  <div style="color:var(--tx3,#475569); font-size:0.75rem; margin-top:6px;">{fg['action']}</div>
</div>""", unsafe_allow_html=True)
    st.progress(int(score) / 100)

with col2:
    st.markdown("#### 📊 Market Breadth")
    adv = breadth.get("advances", 0)
    dec = breadth.get("declines", 0)
    unch = breadth.get("unchanged", 0)
    total = breadth.get("total", 1)
    st.metric("Advances", adv, delta=f"{adv/total*100:.0f}%")
    st.metric("Declines", dec, delta=f"-{dec/total*100:.0f}%", delta_color="inverse")
    st.metric("Unchanged", unch)
    st.metric("A/D Ratio", f"{breadth.get('ad_ratio',1):.2f}x")
    mood = breadth.get("breadth", "NEUTRAL")
    mood_color = "#00FF88" if mood == "BULLISH" else ("#FF4466" if mood == "BEARISH" else "#FFD700")
    st.markdown(f"<b style='color:{mood_color}'>⚡ {mood}</b>", unsafe_allow_html=True)

with col3:
    st.markdown("#### 🌍 Global Markets")
    markets = get_global_markets()
    for name, val in markets.items():
        change = round((val - val * 0.998), 2)  # demo change
        c = "#00FF88" if change >= 0 else "#FF4466"
        st.markdown(f"""
<div style="display:flex; justify-content:space-between; padding:4px 0;
     border-bottom:1px solid var(--border,#1E3A5F); font-size:0.85rem;">
  <span style="color:var(--tx2,#94A3B8);">{name}</span>
  <span style="color:var(--tx,#E2E8F0); font-weight:600;">{val:,.2f}</span>
  <span style="color:{c};">{change:+.2f}</span>
</div>""", unsafe_allow_html=True)

st.divider()

# ── Row 3: Sector + FII/DII ───────────────────────────────────────────────────
col1, col2 = st.columns([2, 1])
with col1:
    st.markdown("#### 🗺️ Sector Heatmap")
    sectors = get_sector_performance()
    st.plotly_chart(build_sector_heatmap(sectors), use_container_width=True)

with col2:
    st.markdown("#### 💰 FII/DII Flows")
    fii_data = get_fii_dii_data()
    st.plotly_chart(build_fii_dii_chart(fii_data), use_container_width=True)
    if fii_data:
        latest = fii_data[-1] if fii_data else {}
        st.metric("Latest FII Net", f"₹{latest.get('fii_net', 0):+,.0f} Cr")
        st.metric("Latest DII Net", f"₹{latest.get('dii_net', 0):+,.0f} Cr")

st.divider()

# ── Row 4: Nifty 50 Heatmap ────────────────────────────────────────────────────
st.markdown("#### 🔥 Nifty 50 Stocks")
nifty_stocks = get_nifty50_heatmap()
st.plotly_chart(nifty50_heatmap(nifty_stocks), use_container_width=True)

st.divider()

# ── Row 5: MCX + Events + GIFT Nifty ─────────────────────────────────────────
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### ⚗️ MCX Prices")
    active, reason = is_mcx_session_active()
    session_color = "#00FF88" if active else "#475569"
    st.markdown(f"<span style='color:{session_color}; font-size:0.8rem;'>⚗️ {reason}</span>",
                unsafe_allow_html=True)
    mcx_prices = get_mcx_demo_prices()
    for sym, price in list(mcx_prices.items())[:6]:
        st.markdown(f"""
<div style="display:flex; justify-content:space-between; padding:3px 0;
     border-bottom:1px solid var(--border,#1E3A5F); font-size:0.82rem;">
  <span style="color:var(--tx2,#94A3B8);">{sym}</span>
  <span style="color:var(--tx,#E2E8F0); font-weight:600;">₹{price:,.2f}</span>
</div>""", unsafe_allow_html=True)

with col2:
    st.markdown("#### 📅 Upcoming Corporate Actions")
    actions = get_corporate_actions(days_ahead=14)
    for a in actions[:5]:
        st.markdown(f"""
<div style="padding:4px 0; border-bottom:1px solid var(--border,#1E3A5F); font-size:0.8rem;">
  <b>{a.get('symbol', '')}</b> — {a.get('purpose', '')}
  <span style="color:var(--tx3,#475569);"> Ex: {a.get('exDate', '')}</span>
</div>""", unsafe_allow_html=True)

with col3:
    st.markdown("#### 🌏 GIFT Nifty (Pre-Market)")
    sgx = get_sgx_nifty()
    st.metric("GIFT Nifty", f"{sgx.get('sgx_nifty', 0):,.2f}")
    premium = sgx.get("premium_discount", 0)
    st.metric("Premium/Discount vs Spot",
              f"₹{premium:+,.2f}",
              delta=f"{sgx.get('expected_gap_pct', 0):+.2f}% expected gap",
              delta_color="normal" if premium >= 0 else "inverse")

    st.markdown("#### 🆕 Upcoming IPOs")
    ipos = get_upcoming_ipos()
    for ipo in ipos[:3]:
        st.markdown(f"""
<div style="padding:4px 0; border-bottom:1px solid var(--border,#1E3A5F); font-size:0.8rem;">
  <b>{ipo.get('companyName', '')}</b> {ipo.get('price', '')}
  <br><span style="color:var(--tx3,#475569);">Open: {ipo.get('openDate', '')} | Size: {ipo.get('issueSize', '')}</span>
</div>""", unsafe_allow_html=True)

# ── MCX Expiry Calendar ────────────────────────────────────────────────────────
with st.expander("📅 MCX Expiry Calendar"):
    expiries = get_mcx_expiry_calendar()
    st.dataframe(pd.DataFrame(expiries), use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown(f'<p style="text-align:center; color:var(--tx3,#475569); font-size:0.7rem;">Dashboard refreshes on page reload • {datetime.datetime.now().strftime("%H:%M:%S IST")}</p>',
            unsafe_allow_html=True)
