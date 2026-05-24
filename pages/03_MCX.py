"""
pages/03_MCX.py — ProTrader Terminal v2.0
MCX Evening Session Trading — Block 7.
Gold, Silver, Crude Oil, Natural Gas, Base Metals.
"""

import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="MCX | ProTrader", page_icon="⚗️", layout="wide")

if not st.session_state.get("authenticated"):
    st.warning("Please login from the main page.")
    st.stop()

from engine import (get_dynamic_universe, get_ohlcv, compute_indicators,
                    score_signal, is_trading_allowed, volatility_adjusted_position_size,
                    calculate_targets_and_sl, place_order, run_backtest)
from ui import inject_css, build_candlestick_chart, build_indicator_chart, build_signal_gauge
from utils.mcx_data import (MCX_CONTRACTS, get_mcx_contract_info, calculate_mcx_margin,
                              calculate_mcx_pnl, get_global_correlation_hint,
                              get_seasonal_bias, is_mcx_session_active,
                              get_mcx_demo_prices, get_mcx_expiry_calendar)
from storage import get_watchlist, add_to_watchlist, get_funds, get_settings

inject_css(st.session_state.get("theme", "dark"), st.session_state.get("accent", "blue"))

uid = st.session_state.get("user_id", "demo")
settings = get_settings(uid)

st.markdown("## ⚗️ MCX Commodity Trading")

# Session status
active, reason = is_mcx_session_active()
session_color = "#00FF88" if active else "#FF4466"
st.markdown(f"""
<div style="background:var(--surface,#0F2035); border:1px solid {session_color};
     border-radius:8px; padding:10px 16px; margin-bottom:12px;
     display:flex; justify-content:space-between;">
  <span style="color:{session_color}; font-weight:700;">⚗️ {reason}</span>
  <span style="color:var(--tx3,#475569); font-size:0.8rem;">
    {datetime.datetime.now().strftime('%H:%M:%S IST')}
  </span>
</div>""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📊 Analysis", "💰 Trade", "📅 Expiry", "🌍 Fundamentals"])

# ── Tab 1: MCX Analysis ───────────────────────────────────────────────────────
with tab1:
    mcx_universe = get_dynamic_universe("mcx")
    mcx_symbols = [u["symbol"] if isinstance(u, dict) else u for u in mcx_universe]
    if not mcx_symbols:
        mcx_symbols = list(MCX_CONTRACTS.keys())

    col1, col2, col3 = st.columns([2, 2, 1])
    sym = col1.selectbox("Commodity", mcx_symbols, key="mcx_sym")
    tf = col2.selectbox("Timeframe", ["ONE_MINUTE","FIVE_MINUTE","FIFTEEN_MINUTE","ONE_HOUR"], index=1, key="mcx_tf")
    if col3.button("➕ Add to Watchlist"):
        add_to_watchlist(uid, "mcx", sym)
        st.success(f"Added {sym}")

    df = get_ohlcv(sym, interval=tf, days=3, exchange="MCX")
    if df.empty:
        st.warning(f"No data for {sym} — showing demo prices")
    else:
        df = compute_indicators(df)
        direction, strength, details = score_signal(df)
        row = df.iloc[-1]
        cmp = float(row["close"])
        atr = float(row.get("atr", cmp * 0.01))

        info = get_mcx_contract_info(sym)
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.plotly_chart(build_signal_gauge(strength, direction), use_container_width=True)
        col2.metric("CMP", f"₹{cmp:,.2f}")
        col3.metric("Lot Size", f"{info.get('lot_size',1)} {info.get('unit','')}")
        col4.metric("Margin %", f"{info.get('margin_pct',5)}%")
        col5.metric("ATR", f"₹{atr:,.2f}")

        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(build_candlestick_chart(df, sym), use_container_width=True)
        with c2:
            st.plotly_chart(build_indicator_chart(df), use_container_width=True)

        # Seasonal bias
        seasonal = get_seasonal_bias(sym)
        s_color = "#00FF88" if seasonal["direction"] == "BULLISH" else (
            "#FF4466" if seasonal["direction"] == "BEARISH" else "#FFD700")
        st.markdown(f"""
<div style="background:var(--surface,#0F2035); border-left:4px solid {s_color};
     border-radius:6px; padding:10px 14px; font-size:0.85rem;">
  🌱 <b>Seasonal Bias ({datetime.date.today().strftime('%B')}):</b>
  <span style="color:{s_color};">{seasonal['direction']}</span> |
  {seasonal['note']}
</div>""", unsafe_allow_html=True)

# ── Tab 2: MCX Trade ──────────────────────────────────────────────────────────
with tab2:
    mcx_universe = get_dynamic_universe("mcx")
    mcx_symbols = [u["symbol"] if isinstance(u, dict) else u for u in mcx_universe] or list(MCX_CONTRACTS.keys())

    col1, col2 = st.columns(2)
    trade_sym = col1.selectbox("Symbol", mcx_symbols, key="mcx_trade_sym")
    side = col2.selectbox("Side", ["BUY", "SELL"], key="mcx_side")

    info = get_mcx_contract_info(trade_sym)
    funds = get_funds(uid)
    capital = funds.get("mcx", 50000)

    df_t = get_ohlcv(trade_sym, interval="FIVE_MINUTE", days=2, exchange="MCX")
    if not df_t.empty:
        df_t = compute_indicators(df_t)
        cmp = float(df_t["close"].iloc[-1])
        atr = float(df_t.get("atr", pd.Series([cmp * 0.01])).iloc[-1] if "atr" in df_t.columns else cmp * 0.01)
    else:
        demo = get_mcx_demo_prices()
        cmp = demo.get(trade_sym, 1000)
        atr = cmp * 0.01

    col1, col2, col3 = st.columns(3)
    qty = col1.number_input("Lots", 1, 20, 1, key="mcx_qty")
    sl = col2.number_input("Stop Loss (₹)", value=round(cmp - atr * 1.5, 2), key="mcx_sl")
    target = col3.number_input("Target (₹)", value=round(cmp + atr * 2.5, 2), key="mcx_tgt")

    # Margin & P&L calculation
    margin = calculate_mcx_margin(trade_sym, qty, cmp)
    pnl_at_target = calculate_mcx_pnl(trade_sym, cmp, target, qty, side)
    pnl_at_sl = calculate_mcx_pnl(trade_sym, cmp, sl, qty, side)
    rr = abs(pnl_at_target["gross_pnl"] / (pnl_at_sl["gross_pnl"] or 1))

    st.markdown(f"""
<div style="background:var(--surface2,#162840); border-radius:8px; padding:12px; font-size:0.85rem;">
  <b>Contract:</b> {trade_sym} × {qty} lot(s) × {info.get('lot_size',1)} {info.get('unit','')} |
  <b>Margin Required:</b> ₹{margin:,.0f} |
  <b>P&L @Target:</b>
  <span style="color:#00FF88">₹{pnl_at_target['net_pnl']:+,.0f}</span> |
  <b>P&L @SL:</b>
  <span style="color:#FF4466">₹{pnl_at_sl['net_pnl']:+,.0f}</span> |
  <b>R:R</b> = {rr:.1f}x
</div>""", unsafe_allow_html=True)

    allowed, reason_str = is_trading_allowed("mcx")
    col1, col2 = st.columns(2)
    with col1:
        paper = st.session_state.get("paper_mode", True)
        if st.button(f"{'📋 PAPER ' if paper else '💰 '}Place {side} Order",
                     use_container_width=True,
                     disabled=not allowed and not paper):
            result = place_order(trade_sym, side, qty, cmp, "mcx", paper=paper)
            if result["status"]:
                st.success(f"✅ {'Paper ' if paper else ''}{side} {qty} {trade_sym} @ ₹{cmp:,.2f}")
            else:
                st.error(result["message"])
    with col2:
        if not allowed:
            st.warning(f"⏳ {reason_str}")

# ── Tab 3: Expiry Calendar ────────────────────────────────────────────────────
with tab3:
    st.markdown("#### 📅 MCX Expiry Calendar")
    expiries = get_mcx_expiry_calendar()
    df_exp = pd.DataFrame(expiries)
    st.dataframe(df_exp, use_container_width=True, hide_index=True)

    # Contract rollover alert
    soon = [e for e in expiries if e.get("dte", 999) <= 5]
    for e in soon:
        st.warning(f"⚠️ {e['symbol']} expires in {e['dte']} days ({e['expiry']}) — consider rolling!")

# ── Tab 4: Fundamentals ───────────────────────────────────────────────────────
with tab4:
    st.markdown("#### 🌍 Global Drivers & Seasonal Analysis")
    selected = st.selectbox("Commodity", list(MCX_CONTRACTS.keys())[:8], key="mcx_fund_sym")
    hint = get_global_correlation_hint(selected)
    st.info(f"📊 {hint}")
    seasonal = get_seasonal_bias(selected)
    s_color = "#00FF88" if seasonal["direction"] == "BULLISH" else (
        "#FF4466" if seasonal["direction"] == "BEARISH" else "#FFD700")
    st.markdown(f"**Seasonal Bias:** <span style='color:{s_color}'>{seasonal['direction']}</span> "
                f"(strength: {seasonal['strength']:.1f})", unsafe_allow_html=True)
    st.markdown(f"*{seasonal['note']}*")

    # All months seasonal
    months = range(1, 13)
    month_labels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    biases = [get_seasonal_bias(selected, m)["seasonal_bias"] for m in months]
    import plotly.graph_objects as go
    ct = {"paper_bgcolor": "#050A14" if st.session_state.get("theme","dark") == "dark" else "#FFF",
          "plot_bgcolor": "#0D1B2A" if st.session_state.get("theme","dark") == "dark" else "#F8FAFC",
          "font_color": "#E2E8F0" if st.session_state.get("theme","dark") == "dark" else "#1E293B"}
    colors = ["#00FF88" if b >= 0 else "#FF4466" for b in biases]
    fig = go.Figure(go.Bar(x=month_labels, y=biases, marker_color=colors, opacity=0.8))
    fig.add_hline(y=0, line_color=ct["font_color"], line_width=1)
    fig.update_layout(title=f"{selected} — Monthly Seasonal Bias",
                      paper_bgcolor=ct["paper_bgcolor"], plot_bgcolor=ct["plot_bgcolor"],
                      font_color=ct["font_color"], height=280,
                      margin=dict(l=40, r=40, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Key Macro Watchlist")
    macro = {
        "GOLD": ["Fed Rate Decision", "US CPI", "DXY (Dollar Index)", "Geopolitical Risk", "RBI Policy"],
        "CRUDEOIL": ["OPEC Meeting", "EIA Inventory", "Global Demand Outlook", "INRUSD Rate", "Geopolitics"],
        "COPPER": ["China PMI", "LME Inventory", "US Manufacturing ISM", "Infrastructure Spend"],
        "NATURALGAS": ["Weather Forecast", "US Inventory (EIA)", "LNG Exports", "Winter Demand"],
    }
    factors = macro.get(selected.upper(), ["Global supply/demand balance", "Currency rates (INRUSD)", "Domestic demand"])
    for f in factors:
        st.markdown(f"• {f}")
