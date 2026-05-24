"""
report.py — ProTrader Terminal v2.0
PDF/HTML report generation, email summaries.
Blocks 22 (Journal), 23 (Tax), 34 (Email summary).
"""

import os, datetime, smtplib, json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from loguru import logger

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    _REPORTLAB = True
except ImportError:
    _REPORTLAB = False


# ──────────────────────────────────────────────────────────────────────────────
# HTML Report (Block 22)
# ──────────────────────────────────────────────────────────────────────────────

def generate_weekly_html_report(user_id: str, trades: list, week_start: str) -> str:
    """Generate weekly HTML performance report."""
    total_pnl = sum(t.get("pnl", 0) for t in trades)
    wins = [t for t in trades if t.get("pnl", 0) > 0]
    losses = [t for t in trades if t.get("pnl", 0) <= 0]
    win_rate = len(wins) / len(trades) * 100 if trades else 0
    avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["pnl"] for t in losses) / len(losses) if losses else 0

    trade_rows = ""
    for t in trades[:20]:
        pnl = t.get("pnl", 0)
        color = "#00FF88" if pnl >= 0 else "#FF4466"
        trade_rows += f"""
        <tr>
          <td>{str(t.get("entry_time",""))[:10]}</td>
          <td><b>{t.get("symbol","—")}</b></td>
          <td>{t.get("segment","—")}</td>
          <td>{t.get("side","—")}</td>
          <td>₹{t.get("entry_price",0):,.2f}</td>
          <td>₹{t.get("exit_price",0):,.2f}</td>
          <td style="color:{color}"><b>₹{pnl:+,.2f}</b></td>
        </tr>"""

    pnl_color = "#00FF88" if total_pnl >= 0 else "#FF4466"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>ProTrader Weekly Report — {week_start}</title>
<style>
  body {{ font-family: Arial, sans-serif; background: #050A14; color: #E2E8F0; margin: 0; padding: 20px; }}
  .container {{ max-width: 800px; margin: 0 auto; }}
  .header {{ background: linear-gradient(135deg, #0D1B2A, #162840); border: 1px solid #1E3A5F;
             border-bottom: 3px solid #00D4FF; padding: 24px; border-radius: 10px; margin-bottom: 24px; }}
  .title {{ font-size: 1.8rem; font-weight: 800; color: #00D4FF; letter-spacing: 3px; }}
  .metric-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }}
  .metric {{ background: #0F2035; border: 1px solid #1E3A5F; border-radius: 8px; padding: 16px; text-align: center; }}
  .metric-label {{ color: #94A3B8; font-size: 0.75rem; margin-bottom: 4px; }}
  .metric-value {{ font-size: 1.4rem; font-weight: 800; }}
  table {{ width: 100%; border-collapse: collapse; background: #0F2035; border-radius: 8px; overflow: hidden; }}
  th {{ background: #162840; padding: 10px 12px; text-align: left; color: #94A3B8; font-size: 0.8rem; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #1E3A5F; font-size: 0.85rem; }}
  .footer {{ text-align: center; color: #475569; font-size: 0.7rem; margin-top: 24px; padding: 12px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="title">⚡ PROTRADER</div>
    <div style="color:#94A3B8; margin-top:4px;">Weekly Performance Report | {week_start}</div>
    <div style="color:#94A3B8; font-size:0.8rem;">User: {user_id}</div>
  </div>

  <div class="metric-grid">
    <div class="metric">
      <div class="metric-label">TOTAL P&L</div>
      <div class="metric-value" style="color:{pnl_color}">₹{total_pnl:+,.0f}</div>
    </div>
    <div class="metric">
      <div class="metric-label">WIN RATE</div>
      <div class="metric-value" style="color:#00D4FF">{win_rate:.1f}%</div>
    </div>
    <div class="metric">
      <div class="metric-label">TOTAL TRADES</div>
      <div class="metric-value">{len(trades)}</div>
    </div>
    <div class="metric">
      <div class="metric-label">AVG WIN / LOSS</div>
      <div class="metric-value" style="font-size:1rem">₹{avg_win:+,.0f} / ₹{avg_loss:+,.0f}</div>
    </div>
  </div>

  <h2 style="color:#00D4FF; font-size:1rem; margin-bottom:12px;">📋 Trade Details</h2>
  <table>
    <thead>
      <tr><th>Date</th><th>Symbol</th><th>Segment</th><th>Side</th><th>Entry</th><th>Exit</th><th>P&L</th></tr>
    </thead>
    <tbody>{trade_rows}</tbody>
  </table>

  <div class="footer">
    ⚡ ProTrader Terminal v2.0 | Generated {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
    <br>⚠️ This report is for informational purposes only. Past performance does not guarantee future results.
  </div>
</div>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────────────────────
# PDF Tax Statement (Block 23)
# ──────────────────────────────────────────────────────────────────────────────

def generate_tax_pdf(user_id: str, trades: list, fy: str) -> Optional[bytes]:
    """Generate CA-friendly tax P&L statement as PDF."""
    if not _REPORTLAB:
        logger.warning("reportlab not installed — skipping PDF generation")
        return None

    from io import BytesIO
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph(f"ProTrader Terminal — Tax P&L Statement", styles["Title"]))
    elements.append(Paragraph(f"Financial Year: {fy} | User: {user_id}", styles["Normal"]))
    elements.append(Paragraph(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
    elements.append(Spacer(1, 0.25*inch))

    # Summary
    total_pnl = sum(t.get("pnl", 0) for t in trades)
    total_charges = sum(t.get("charges", 0) for t in trades)
    net_pnl = total_pnl - total_charges
    fo_turnover = sum(abs(t.get("pnl",0)) for t in trades if t.get("segment","").upper() in ("NFO","OPTIONS","FUTURES","MCX"))

    summary_data = [
        ["Description", "Amount (₹)"],
        ["Total Gross P&L", f"₹{total_pnl:,.2f}"],
        ["Total Transaction Charges", f"₹{total_charges:,.2f}"],
        ["Net P&L (after charges)", f"₹{net_pnl:,.2f}"],
        ["F&O Turnover (absolute)", f"₹{fo_turnover:,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[4*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0D1B2A")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("PADDING", (0,0), (-1,-1), 6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.25*inch))

    # Trade details
    elements.append(Paragraph("Trade-wise Detail", styles["Heading2"]))
    headers = ["Date", "Symbol", "Segment", "Side", "Entry", "Exit", "Gross P&L", "Charges", "Net P&L"]
    data = [headers]
    for t in trades[:100]:
        data.append([
            str(t.get("entry_time",""))[:10],
            t.get("symbol",""),
            t.get("segment",""),
            t.get("side",""),
            f"₹{t.get('entry_price',0):,.2f}",
            f"₹{t.get('exit_price',0):,.2f}",
            f"₹{t.get('pnl',0):+,.2f}",
            f"₹{t.get('charges',0):,.2f}",
            f"₹{t.get('net_pnl',0):+,.2f}",
        ])

    trade_table = Table(data, repeatRows=1)
    trade_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0D1B2A")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 7),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("PADDING", (0,0), (-1,-1), 4),
    ]))
    elements.append(trade_table)

    doc.build(elements)
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────────────────
# Email (Block 34)
# ──────────────────────────────────────────────────────────────────────────────

def send_email_summary(user_id: str, to_email: str, trades: list = None) -> str:
    """Send daily/weekly email summary via SMTP."""
    smtp_email = os.getenv("SMTP_EMAIL", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")

    if not smtp_email or not smtp_password:
        return "⚠️ SMTP not configured. Set SMTP_EMAIL and SMTP_PASSWORD in .env"
    if not to_email:
        return "⚠️ No recipient email provided"

    trades = trades or []
    total_pnl = sum(t.get("pnl",0) for t in trades)
    html = generate_weekly_html_report(user_id, trades, str(datetime.date.today()))

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"⚡ ProTrader Daily Summary | {datetime.date.today()} | P&L: ₹{total_pnl:+,.0f}"
    msg["From"] = smtp_email
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, to_email, msg.as_string())
        logger.info(f"Email sent to {to_email}")
        return f"✅ Email sent to {to_email}"
    except Exception as e:
        logger.error(f"Email error: {e}")
        return f"❌ Email failed: {e}"


def send_whatsapp_alert(message: str, phone: str) -> bool:
    """Send WhatsApp alert via Business Cloud API (Block 34)."""
    token = os.getenv("WHATSAPP_TOKEN", "")
    phone_id = os.getenv("WHATSAPP_PHONE_ID", "")
    if not token or not phone_id:
        logger.warning("WhatsApp not configured")
        return False
    try:
        import requests
        resp = requests.post(
            f"https://graph.facebook.com/v18.0/{phone_id}/messages",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "messaging_product": "whatsapp",
                "to": phone.replace("+","").replace(" ",""),
                "type": "text",
                "text": {"body": message}
            },
            timeout=10
        )
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"WhatsApp error: {e}")
        return False
