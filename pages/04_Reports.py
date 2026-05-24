"""
pages/04_Reports.py — ProTrader Terminal v2.0
Reports & Export — Blocks 22 (Journal), 23 (Tax), 34 (Email).
PDF download, CSV export, weekly HTML report, tax P&L statement.
"""

import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="Reports | ProTrader", page_icon="📑", layout="wide")

if not st.session_state.get("authenticated"):
    st.warning("Please login from the main page.")
    st.stop()

from storage import get_trade_history, get_tax_year_trades
from engine import compute_risk_metrics
from report import (generate_weekly_html_report, generate_tax_pdf, send_email_summary)
from ui import inject_css, build_equity_curve, build_pnl_heatmap_calendar

inject_css(st.session_state.get("theme", "dark"), st.session_state.get("accent", "blue"))

uid = st.session_state.get("user_id", "demo")
paper = st.session_state.get("paper_mode", True)

st.markdown("## 📑 Reports & Export")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Performance Report", "🧾 Tax Statement", "📧 Email Report", "📥 Data Export"])

# ── Tab 1: Performance Report ─────────────────────────────────────────────────
with tab1:
    st.markdown("#### 📊 Weekly / Custom Performance Report")
    col1, col2, col3 = st.columns(3)
    report_start = col1.date_input("From", datetime.date.today() - datetime.timedelta(days=7))
    report_end = col2.date_input("To", datetime.date.today())
    mode = col3.selectbox("Mode", ["Paper", "Live"])

    history = get_trade_history(uid, limit=1000, paper=(mode == "Paper"))
    # Filter dates
    history = [t for t in history
               if report_start <= datetime.datetime.fromisoformat(
                   str(t.get("entry_time", datetime.datetime.now()))[:10]
               ).date() <= report_end]

    if not history:
        st.info("No trades in selected date range.")
    else:
        metrics = compute_risk_metrics(history)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total P&L", f"₹{metrics.get('total_pnl',0):+,.0f}")
        c2.metric("Win Rate", f"{metrics.get('win_rate',0):.1f}%")
        c3.metric("Sharpe", f"{metrics.get('sharpe',0):.2f}")
        c4.metric("Max DD", f"{metrics.get('max_drawdown_pct',0):.1f}%")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Trades", metrics.get("total_trades", len(history)))
        c2.metric("Avg Trade", f"₹{metrics.get('avg_trade',0):+,.0f}")
        c3.metric("VaR 95%", f"₹{metrics.get('var_95',0):,.0f}")
        c4.metric("Sortino", f"{metrics.get('sortino',0):.2f}")

        st.plotly_chart(build_pnl_heatmap_calendar(history), use_container_width=True)

        # By segment
        df = pd.DataFrame(history)
        if "segment" in df.columns and "pnl" in df.columns:
            st.markdown("**P&L by Segment:**")
            seg_df = df.groupby("segment")["pnl"].agg(["sum","mean","count"]).round(2)
            seg_df.columns = ["Total P&L", "Avg P&L", "Trades"]
            st.dataframe(seg_df, use_container_width=True)

        # Generate HTML report
        week_start = str(report_start)
        html = generate_weekly_html_report(uid, history, week_start)
        st.download_button(
            "📥 Download HTML Report",
            html.encode(),
            f"protrader_report_{report_start}_{report_end}.html",
            mime="text/html"
        )

# ── Tab 2: Tax Statement ─────────────────────────────────────────────────────
with tab2:
    st.markdown("#### 🧾 Tax P&L Statement (ITR-3 compatible)")
    col1, col2 = st.columns(2)
    fy = col1.selectbox("Financial Year", ["2024-25", "2023-24", "2022-23"])
    mode_tax = col2.selectbox("Mode", ["All", "Live Only", "Paper Only"])

    if st.button("📊 Generate Tax Statement"):
        trades = get_tax_year_trades(uid, fy)
        if not trades:
            st.info(f"No trades found for FY {fy}")
        else:
            from engine import calculate_trade_charges, classify_trade_for_tax, compute_fo_turnover

            classified = {}
            for t in trades:
                cat = classify_trade_for_tax(t)
                classified.setdefault(cat, []).append(t)

            st.markdown("#### Summary by Tax Category")
            summary = []
            for cat, cat_trades in classified.items():
                pnl = sum(t.get("pnl", 0) for t in cat_trades)
                charges = sum(t.get("charges", 0) for t in cat_trades)
                summary.append({
                    "Category": cat.replace("_", " "),
                    "Trades": len(cat_trades),
                    "Gross P&L": f"₹{pnl:+,.2f}",
                    "Charges": f"₹{charges:,.2f}",
                    "Net P&L": f"₹{pnl - charges:+,.2f}",
                })
            st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)

            fo_turnover = compute_fo_turnover(trades)
            total_pnl = sum(t.get("pnl",0) for t in trades)
            total_charges = sum(t.get("charges",0) for t in trades)

            c1, c2, c3 = st.columns(3)
            c1.metric("F&O Turnover", f"₹{fo_turnover:,.0f}")
            c2.metric("Total Net P&L", f"₹{total_pnl - total_charges:+,.0f}")
            c3.metric("Total Charges", f"₹{total_charges:,.0f}")

            if fo_turnover > 100000000:
                st.error("🚨 F&O Turnover > ₹10 Crore — **Tax Audit mandatory** under Section 44AB")
            elif fo_turnover > 10000000:
                st.warning("⚠️ F&O Turnover > ₹1 Crore — Consult CA for audit requirement")
            else:
                st.success("✅ F&O Turnover within non-audit limit")

            # PDF download
            pdf_bytes = generate_tax_pdf(uid, trades, fy)
            if pdf_bytes:
                st.download_button("📥 Download PDF Tax Statement", pdf_bytes,
                                    f"tax_pnl_{fy}.pdf", mime="application/pdf")
            else:
                st.info("Install `reportlab` for PDF generation: `pip install reportlab`")

            # CSV download
            df_tax = pd.DataFrame(trades)
            st.download_button("📥 Download CSV", df_tax.to_csv(index=False),
                                f"tax_{fy}.csv", mime="text/csv")

# ── Tab 3: Email Report ──────────────────────────────────────────────────────
with tab3:
    st.markdown("#### 📧 Email Performance Summary")
    st.info("Requires SMTP_EMAIL and SMTP_PASSWORD in .env (Gmail App Password recommended)")

    col1, col2 = st.columns(2)
    to_email = col1.text_input("Recipient Email", key="rpt_email")
    period = col2.selectbox("Period", ["Today", "This Week", "Last 7 Days", "This Month"])

    if st.button("📧 Send Email Report"):
        if not to_email:
            st.warning("Enter a recipient email")
        else:
            history = get_trade_history(uid, limit=100, paper=paper)
            with st.spinner("Sending email..."):
                result = send_email_summary(uid, to_email, history)
            if "✅" in result:
                st.success(result)
            else:
                st.error(result)

    st.markdown("---")
    st.markdown("#### 📱 WhatsApp EOD Summary")
    from storage import get_settings
    settings = get_settings(uid)
    phone = st.text_input("Phone (+91...)", value=settings.get("whatsapp_phone", ""), key="rpt_phone")
    if st.button("💬 Send WhatsApp Summary"):
        history = get_trade_history(uid, limit=50, paper=paper)
        pnl = sum(t.get("pnl",0) for t in history[-20:])
        from utils.notifications import send_whatsapp_message, build_eod_whatsapp_message
        msg = build_eod_whatsapp_message(uid, history[-20:], pnl, settings.get("daily_target", 5000))
        ok = send_whatsapp_message(msg, phone)
        if ok:
            st.success("WhatsApp sent!")
        else:
            st.error("WhatsApp failed — check WHATSAPP_TOKEN in .env")

# ── Tab 4: Data Export ────────────────────────────────────────────────────────
with tab4:
    st.markdown("#### 📥 Export Your Data")
    history = get_trade_history(uid, limit=10000, paper=paper)
    df_all = pd.DataFrame(history) if history else pd.DataFrame()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Trade History**")
        if not df_all.empty:
            st.write(f"{len(df_all)} trades")
            st.download_button("📥 Download All Trades (CSV)",
                                df_all.to_csv(index=False),
                                "all_trades.csv", mime="text/csv")
        else:
            st.info("No trades yet")

    with col2:
        st.markdown("**Watchlists**")
        from storage import get_watchlist
        for seg in ["equity","futures","options","mcx","etf"]:
            wl = get_watchlist(uid, seg)
            if wl:
                df_wl = pd.DataFrame({"symbol": wl, "segment": seg})
                st.download_button(f"📥 {seg.title()} Watchlist",
                                    df_wl.to_csv(index=False),
                                    f"watchlist_{seg}.csv",
                                    mime="text/csv",
                                    key=f"dl_wl_{seg}")

    st.markdown("---")
    st.markdown("**Settings Backup**")
    from storage import get_settings, get_strategies
    settings = get_settings(uid)
    strategies = get_strategies(uid)
    import json
    backup = {"settings": settings, "strategies": strategies}
    st.download_button("📥 Download Settings Backup (JSON)",
                        json.dumps(backup, indent=2, default=str),
                        "protrader_settings_backup.json",
                        mime="application/json")
