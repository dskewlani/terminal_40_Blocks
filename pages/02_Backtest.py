"""
pages/02_Backtest.py — ProTrader Terminal v2.0
Full Backtesting Engine page — Block 16.
Single backtest, walk-forward optimization, strategy comparison, export.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import datetime

st.set_page_config(page_title="Backtest | ProTrader", page_icon="📊", layout="wide")

if not st.session_state.get("authenticated"):
    st.warning("Please login from the main page.")
    st.stop()

from engine import get_dynamic_universe, run_backtest
from backtest import run_walk_forward, compare_strategies, generate_backtest_report
from ui import inject_css, build_equity_curve, get_chart_theme
from components.charts import risk_return_scatter

inject_css(st.session_state.get("theme", "dark"), st.session_state.get("accent", "blue"))

st.markdown("## 📊 Backtesting Engine")
st.markdown("*Block 16: Full backtest with walk-forward optimization and strategy comparison*")

universe = get_dynamic_universe("equity")
symbols = [u["symbol"] if isinstance(u, dict) else u for u in universe[:200]]

tab1, tab2, tab3 = st.tabs(["🔍 Single Backtest", "🔄 Walk-Forward", "⚖️ Strategy Comparison"])

# ─── Tab 1: Single Backtest ────────────────────────────────────────────────────
with tab1:
    col1, col2, col3, col4 = st.columns(4)
    bt_sym = col1.selectbox("Symbol", symbols, key="bt1_sym")
    start = col2.date_input("Start", datetime.date.today() - datetime.timedelta(days=90), key="bt1_start")
    end = col3.date_input("End", datetime.date.today(), key="bt1_end")
    tf = col4.selectbox("Timeframe", ["FIVE_MINUTE", "FIFTEEN_MINUTE", "ONE_HOUR", "ONE_DAY"], index=1, key="bt1_tf")

    with st.expander("⚙️ Strategy Parameters"):
        c1, c2, c3, c4 = st.columns(4)
        min_str = c1.slider("Min Signal Strength %", 40, 90, 65, key="bt1_str")
        risk_pct = c2.slider("Risk Per Trade %", 0.25, 3.0, 1.0, 0.25, key="bt1_risk")
        max_hold = c3.number_input("Max Hold Bars", 5, 200, 40, key="bt1_hold")
        sl_mult = c4.slider("SL ATR Multiplier", 0.5, 3.0, 1.5, 0.25, key="bt1_sl")

    if st.button("▶️ Run Backtest", use_container_width=True, key="run_bt1"):
        with st.spinner(f"Backtesting {bt_sym}..."):
            result = run_backtest(bt_sym, str(start), str(end), interval=tf,
                                   strategy_params={"min_strength": min_str,
                                                    "risk_pct": risk_pct,
                                                    "max_hold_bars": max_hold})
        if "error" in result:
            st.error(result["error"])
        else:
            # Metrics
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("Trades", result["total_trades"])
            c2.metric("Win Rate", f"{result['win_rate']:.1f}%")
            c3.metric("Total P&L", f"₹{result['total_pnl']:+,.0f}")
            c4.metric("Max DD", f"{result['max_drawdown']:.1f}%")
            c5.metric("Sharpe", f"{result['sharpe']:.2f}")
            c6.metric("Profit Factor", f"{result['profit_factor']:.2f}")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Avg Win", f"₹{result['avg_win']:+,.0f}")
            c2.metric("Avg Loss", f"₹{result['avg_loss']:+,.0f}")
            c3.metric("Calmar", f"{result['calmar']:.2f}")
            c4.metric("Win/Loss Ratio", f"{abs(result['avg_win'] / (result['avg_loss'] or 1)):.2f}x")

            st.plotly_chart(build_equity_curve(result["equity_curve"],
                                               f"Equity Curve — {bt_sym}"),
                            use_container_width=True)

            with st.expander("📋 Full Trade List"):
                df = pd.DataFrame(result["trades"])
                if not df.empty:
                    df["pnl_color"] = df["pnl"].apply(lambda x: "WIN" if x > 0 else "LOSS")
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    csv = df.to_csv(index=False)
                    st.download_button("📥 Download Trades CSV", csv,
                                       f"backtest_{bt_sym}_{start}_{end}.csv")

            with st.expander("📝 Backtest Report"):
                report = generate_backtest_report(bt_sym, result)
                st.markdown(report)

# ─── Tab 2: Walk-Forward ─────────────────────────────────────────────────────
with tab2:
    st.markdown("#### 🔄 Walk-Forward Optimization")
    st.markdown("Split history into train/test folds. Optimize parameters on train, validate on test.")

    col1, col2, col3 = st.columns(3)
    wf_sym = col1.selectbox("Symbol", symbols, key="wf_sym")
    wf_splits = col2.number_input("Number of Folds", 2, 6, 3, key="wf_splits")
    wf_days = col3.number_input("Historical Days", 30, 365, 90, key="wf_days")

    st.markdown("**Parameter Grid:**")
    col1, col2, col3 = st.columns(3)
    str_options = col1.multiselect("Signal Strength %", [50,55,60,65,70,75,80], default=[60,65,70])
    risk_options = col2.multiselect("Risk %", [0.5,1.0,1.5,2.0], default=[0.5,1.0,1.5])
    hold_options = col3.multiselect("Max Hold Bars", [20,30,40,60], default=[20,40])

    if st.button("🔄 Run Walk-Forward", use_container_width=True):
        param_grid = {
            "min_strength": str_options or [60, 65, 70],
            "risk_pct": risk_options or [0.5, 1.0, 1.5],
            "max_hold_bars": hold_options or [20, 40],
        }
        with st.spinner("Running walk-forward optimization... (this takes a minute)"):
            wf_result = run_walk_forward(wf_sym, days=wf_days, n_splits=wf_splits,
                                          param_grid=param_grid)

        if "error" in wf_result:
            st.error(wf_result["error"])
        else:
            col1, col2, col3 = st.columns(3)
            col1.metric("Avg Test Sharpe", f"{wf_result['avg_test_sharpe']:.2f}")
            col2.metric("Avg Test Win Rate", f"{wf_result['avg_test_win_rate']:.1f}%")
            ofs = wf_result["overfitting_score"]
            col3.metric("Overfitting Score", f"{ofs:.2f}",
                        delta="⚠️ Overfitting risk" if ofs > 0.5 else "✅ Low overfitting",
                        delta_color="inverse" if ofs > 0.5 else "normal")

            st.markdown("#### Fold Results")
            df_folds = pd.DataFrame(wf_result["folds"])
            st.dataframe(df_folds, use_container_width=True, hide_index=True)

            if ofs > 0.5:
                st.warning(f"⚠️ Overfitting score {ofs:.2f} is high — strategy may not generalize well. "
                           f"Consider simpler parameters or more data.")
            else:
                st.success(f"✅ Walk-forward complete. Avg test Sharpe: {wf_result['avg_test_sharpe']:.2f}")

# ─── Tab 3: Strategy Comparison ──────────────────────────────────────────────
with tab3:
    st.markdown("#### ⚖️ Compare Multiple Strategies")
    col1, col2 = st.columns(2)
    comp_sym = col1.selectbox("Symbol", symbols, key="comp_sym")
    comp_tf = col2.selectbox("Timeframe", ["FIFTEEN_MINUTE", "ONE_HOUR", "ONE_DAY"], key="comp_tf")

    strategies_to_compare = [
        {"label": "Conservative", "min_strength": 75, "risk_pct": 0.5, "max_hold_bars": 20},
        {"label": "Balanced", "min_strength": 65, "risk_pct": 1.0, "max_hold_bars": 40},
        {"label": "Aggressive", "min_strength": 55, "risk_pct": 1.5, "max_hold_bars": 60},
        {"label": "Trend-Only", "min_strength": 70, "risk_pct": 1.0, "max_hold_bars": 80},
    ]

    st.markdown("*Comparing 4 preset strategies: Conservative / Balanced / Aggressive / Trend-Only*")

    if st.button("⚖️ Compare Strategies", use_container_width=True):
        with st.spinner("Running strategy comparison..."):
            comp = compare_strategies(comp_sym, strategies_to_compare, interval=comp_tf, days=60)

        if "error" in comp:
            st.error(comp["error"])
        else:
            st.success(f"Best by Sharpe: **{comp['best_by_sharpe']}** | Best by Win Rate: **{comp['best_by_winrate']}**")
            rows = []
            for s in comp["strategies"]:
                rows.append({
                    "Strategy": s.get("label", ""),
                    "Trades": s.get("total_trades", 0),
                    "Win Rate %": f"{s.get('win_rate', 0):.1f}",
                    "Total P&L": f"₹{s.get('total_pnl', 0):+,.0f}",
                    "Max DD %": f"{s.get('max_drawdown', 0):.1f}",
                    "Sharpe": f"{s.get('sharpe', 0):.2f}",
                    "Profit Factor": f"{s.get('profit_factor', 0):.2f}",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            # Risk-return scatter
            scatter_data = [{"label": s.get("label",""), "max_drawdown": s.get("max_drawdown",5),
                              "total_pnl": s.get("total_pnl",0), "sharpe": s.get("sharpe",1)}
                            for s in comp["strategies"]]
            st.plotly_chart(risk_return_scatter(scatter_data), use_container_width=True)

            # Equity curves overlay
            import plotly.graph_objects as go
            ct = get_chart_theme()
            fig = go.Figure()
            colors = ["#00D4FF", "#00FF88", "#FFD700", "#FF6B35"]
            for s, color in zip(comp["strategies"], colors):
                ec = s.get("equity_curve", [])
                if ec:
                    fig.add_trace(go.Scatter(y=ec, name=s.get("label",""),
                                              line=dict(color=color, width=2)))
            fig.update_layout(title="Equity Curves Comparison",
                              paper_bgcolor=ct["paper_bgcolor"],
                              plot_bgcolor=ct["plot_bgcolor"],
                              font_color=ct["font_color"],
                              height=300, margin=dict(l=40, r=40, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)
