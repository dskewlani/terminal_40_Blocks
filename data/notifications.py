"""
utils/notifications.py — ProTrader Terminal v2.0
Multi-channel alert delivery: Sound, Browser, Email, WhatsApp.
Blocks 15, 34, 38.
"""

import os, time, json, datetime, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from loguru import logger

import streamlit as st


# ─── In-App Notifications ─────────────────────────────────────────────────────

def show_alert(message: str, level: str = "info", symbol: str = "",
               play_sound: bool = False):
    """
    Block 15: Show in-app alert + optional browser sound.
    level: info | success | warning | error
    """
    icon_map = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "🚨"}
    color_map = {"info": "#00D4FF", "success": "#00FF88", "warning": "#FFD700", "error": "#FF4466"}
    icon = icon_map.get(level, "ℹ️")
    color = color_map.get(level, "#00D4FF")

    st.markdown(f"""
<div style="background:var(--surface2,#162840); border-left:4px solid {color};
     border-radius:8px; padding:10px 14px; margin:4px 0; font-size:0.9rem;">
  {icon} <strong>{symbol + ': ' if symbol else ''}</strong>{message}
  <span style="float:right; color:var(--tx3,#475569); font-size:0.75rem;">
    {datetime.datetime.now().strftime('%H:%M:%S')}
  </span>
</div>""", unsafe_allow_html=True)

    if play_sound:
        # Web Audio API via JS injection
        sounds = {
            "success": "440,0.15",   # A4 note
            "error": "200,0.3",      # Low boom
            "warning": "330,0.2",    # E4
            "info": "520,0.1",       # High C
        }
        freq, duration = sounds.get(level, "440,0.15").split(",")
        st.markdown(f"""
<script>
(function() {{
  try {{
    var ctx = new (window.AudioContext || window.webkitAudioContext)();
    var osc = ctx.createOscillator();
    var gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.value = {freq};
    gain.gain.setValueAtTime(0.3, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + {duration});
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + {duration});
  }} catch(e) {{}}
}})();
</script>""", unsafe_allow_html=True)


def browser_notification(title: str, body: str, icon: str = "⚡"):
    """Block 38: Browser push notification via Web Notification API."""
    st.markdown(f"""
<script>
(function() {{
  if ('Notification' in window) {{
    if (Notification.permission === 'granted') {{
      new Notification('{icon} {title}', {{body: '{body}', icon: '/favicon.ico'}});
    }} else if (Notification.permission !== 'denied') {{
      Notification.requestPermission().then(function(p) {{
        if (p === 'granted') {{
          new Notification('{icon} {title}', {{body: '{body}'}});
        }}
      }});
    }}
  }}
}})();
</script>""", unsafe_allow_html=True)


# ─── Alert Rule Engine ────────────────────────────────────────────────────────

class AlertManager:
    """Block 15: Price alert checker against live prices."""

    def __init__(self, user_id: str):
        self.user_id = user_id

    def check_all(self, live_prices: dict, settings: dict) -> List[dict]:
        """
        Check all active alerts against current prices.
        Returns list of triggered alerts.
        """
        from storage import get_alerts, mark_alert_triggered
        alerts = get_alerts(self.user_id)
        triggered = []

        for i, alert in enumerate(alerts):
            if alert.get("triggered"):
                continue
            symbol = alert.get("symbol", "")
            condition = alert.get("condition", "above")
            value = float(alert.get("value", 0))
            current = live_prices.get(symbol, 0)

            if current == 0:
                continue

            fired = False
            if condition == "above" and current >= value:
                fired = True
            elif condition == "below" and current <= value:
                fired = True
            elif condition == "pct_up":
                # % above previous close — would need prev_close stored
                fired = False
            elif condition == "pct_down":
                fired = False

            if fired:
                mark_alert_triggered(self.user_id, i)
                alert["current_price"] = current
                triggered.append(alert)

                # Deliver via all enabled channels
                msg = f"🔔 {symbol}: {condition} {value} — Current: ₹{current:,.2f}"
                if settings.get("sound_alerts"):
                    show_alert(msg, "warning", symbol, play_sound=True)
                else:
                    show_alert(msg, "warning", symbol)
                if settings.get("browser_notifications"):
                    browser_notification(f"{symbol} Alert", msg)
                if settings.get("whatsapp_alerts") and settings.get("whatsapp_phone"):
                    send_whatsapp_message(msg, settings["whatsapp_phone"])
                if settings.get("email_alerts") and settings.get("alert_email"):
                    _send_quick_email(msg, settings["alert_email"])

        return triggered

    def milestone_alerts(self, current_pnl: float, daily_goal: float,
                          settings: dict) -> None:
        """Block 15: Fire alerts at 25%, 50%, 75%, 100% of daily goal."""
        milestones = {0.25: "25%", 0.50: "50%", 0.75: "75%", 1.0: "100%"}
        reached_key = f"milestones_reached_{datetime.date.today()}"
        from storage import get_value, set_value
        reached = get_value(self.user_id, reached_key) or []

        for ratio, label in milestones.items():
            target = daily_goal * ratio
            if current_pnl >= target and label not in reached:
                reached.append(label)
                set_value(self.user_id, reached_key, reached)
                msg = f"🎯 Daily goal {label} reached! P&L: ₹{current_pnl:+,.0f} / ₹{daily_goal:,.0f}"
                show_alert(msg, "success", play_sound=settings.get("sound_alerts", False))
                if settings.get("whatsapp_alerts") and settings.get("whatsapp_phone"):
                    send_whatsapp_message(msg, settings["whatsapp_phone"])


# ─── WhatsApp ─────────────────────────────────────────────────────────────────

def send_whatsapp_message(message: str, phone: str) -> bool:
    """Block 34/38: WhatsApp Business Cloud API."""
    token = os.getenv("WHATSAPP_TOKEN", "")
    phone_id = os.getenv("WHATSAPP_PHONE_ID", "")
    if not token or not phone_id:
        logger.debug("WhatsApp not configured")
        return False
    try:
        import requests
        clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
        resp = requests.post(
            f"https://graph.facebook.com/v18.0/{phone_id}/messages",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "messaging_product": "whatsapp",
                "to": clean_phone,
                "type": "text",
                "text": {"body": message[:4096]}  # WhatsApp limit
            },
            timeout=10
        )
        success = resp.status_code == 200
        if success:
            logger.info(f"WhatsApp sent to {clean_phone}")
        else:
            logger.warning(f"WhatsApp failed: {resp.text}")
        return success
    except Exception as e:
        logger.error(f"WhatsApp error: {e}")
        return False


def _send_quick_email(message: str, to_email: str) -> bool:
    """Block 38: Send quick text email alert."""
    smtp_email = os.getenv("SMTP_EMAIL", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    if not smtp_email or not smtp_password:
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"⚡ ProTrader Alert — {datetime.datetime.now().strftime('%H:%M')}"
        msg["From"] = smtp_email
        msg["To"] = to_email
        msg.attach(MIMEText(message, "plain"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, to_email, msg.as_string())
        return True
    except Exception as e:
        logger.error(f"Email alert error: {e}")
        return False


# ─── Scheduled Digest ─────────────────────────────────────────────────────────

def build_eod_whatsapp_message(user_id: str, trades: list,
                                pnl: float, goal: float) -> str:
    """Block 34: End-of-day WhatsApp message."""
    wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
    total = len(trades)
    wr = wins / total * 100 if total > 0 else 0
    goal_pct = pnl / goal * 100 if goal > 0 else 0
    pnl_emoji = "🟢" if pnl >= 0 else "🔴"
    return (
        f"⚡ *ProTrader EOD Summary*\n"
        f"📅 {datetime.date.today()}\n\n"
        f"{pnl_emoji} *P&L: ₹{pnl:+,.0f}*\n"
        f"🎯 Goal: ₹{goal:,.0f} ({goal_pct:.0f}% achieved)\n"
        f"📊 Trades: {total} | WR: {wr:.0f}%\n\n"
        f"_Sent by ProTrader Terminal_"
    )


def build_signal_whatsapp_message(symbol: str, signal: str,
                                   price: float, strength: float,
                                   sl: float, target: float) -> str:
    """Block 34: Trading signal WhatsApp message."""
    emoji = "🟢" if signal == "BUY" else "🔴"
    return (
        f"⚡ *ProTrader Signal*\n"
        f"{emoji} *{signal} {symbol}*\n\n"
        f"💰 CMP: ₹{price:,.2f}\n"
        f"🛑 SL: ₹{sl:,.2f}\n"
        f"🎯 Target: ₹{target:,.2f}\n"
        f"💪 Strength: {strength:.0f}%\n\n"
        f"_ProTrader Terminal | Not SEBI advice_"
    )
