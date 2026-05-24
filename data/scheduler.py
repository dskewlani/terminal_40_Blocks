"""
utils/scheduler.py — ProTrader Terminal v2.0
Background task scheduler: auto-scan loop, EOD digest, alert polling.
Blocks 4-8 (auto-trade), 15 (alerts), 34 (notifications).
Runs in a daemon thread — safe with Streamlit's rerun model.
"""

import os, time, datetime, threading
from typing import Callable, Optional
from loguru import logger


# ─── Simple Interval Scheduler ────────────────────────────────────────────────

class Task:
    def __init__(self, name: str, fn: Callable, interval_seconds: int,
                 enabled: bool = True, run_at: Optional[str] = None):
        """
        name: task identifier
        fn: callable to execute
        interval_seconds: how often to run (0 = run once at run_at time)
        run_at: "HH:MM" — time-of-day to run (daily, overrides interval)
        """
        self.name = name
        self.fn = fn
        self.interval = interval_seconds
        self.enabled = enabled
        self.run_at = run_at
        self.last_run = 0.0
        self.last_run_date: Optional[datetime.date] = None
        self.run_count = 0
        self.errors = 0

    def should_run(self) -> bool:
        if not self.enabled:
            return False
        now = time.time()
        today = datetime.date.today()

        if self.run_at:
            # Daily time-based — run once per day at specified time
            now_dt = datetime.datetime.now()
            run_h, run_m = map(int, self.run_at.split(":"))
            if (now_dt.hour == run_h and now_dt.minute == run_m
                    and self.last_run_date != today):
                return True
            return False

        return (now - self.last_run) >= self.interval

    def execute(self):
        try:
            self.fn()
            self.last_run = time.time()
            self.last_run_date = datetime.date.today()
            self.run_count += 1
            logger.debug(f"Task '{self.name}' completed (run #{self.run_count})")
        except Exception as e:
            self.errors += 1
            logger.error(f"Task '{self.name}' error #{self.errors}: {e}")


class Scheduler:
    """Thread-safe background scheduler."""

    def __init__(self):
        self.tasks: dict[str, Task] = {}
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

    def add(self, task: Task):
        with self._lock:
            self.tasks[task.name] = task
        logger.info(f"Scheduler: registered task '{task.name}'")

    def remove(self, name: str):
        with self._lock:
            self.tasks.pop(name, None)

    def enable(self, name: str):
        with self._lock:
            if name in self.tasks:
                self.tasks[name].enabled = True

    def disable(self, name: str):
        with self._lock:
            if name in self.tasks:
                self.tasks[name].enabled = False

    def start(self, tick_seconds: float = 10.0):
        """Start background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, args=(tick_seconds,), daemon=True, name="ProTraderScheduler"
        )
        self._thread.start()
        logger.info("Scheduler started.")

    def stop(self):
        self._running = False
        logger.info("Scheduler stopped.")

    def _loop(self, tick: float):
        while self._running:
            with self._lock:
                tasks = list(self.tasks.values())
            for task in tasks:
                if task.should_run():
                    task.execute()
            time.sleep(tick)

    def status(self) -> list:
        with self._lock:
            return [
                {
                    "name": t.name, "enabled": t.enabled,
                    "interval": t.interval, "run_at": t.run_at,
                    "run_count": t.run_count, "errors": t.errors,
                    "last_run": datetime.datetime.fromtimestamp(t.last_run).strftime("%H:%M:%S")
                    if t.last_run > 0 else "Never"
                }
                for t in self.tasks.values()
            ]


# ─── Shared Singleton ────────────────────────────────────────────────────────
_scheduler: Optional[Scheduler] = None


def get_scheduler() -> Scheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
    return _scheduler


# ─── Pre-built Task Factories ─────────────────────────────────────────────────

def make_price_refresh_task(user_id: str, interval: int = 15) -> Task:
    """Block 2/15: Refresh watchlist prices every N seconds."""
    def _refresh():
        from storage import get_watchlist, get_settings
        from engine import get_live_prices_bulk
        settings = get_settings(user_id)
        segments = ["equity", "futures", "mcx"]
        all_symbols = []
        for seg in segments:
            all_symbols.extend(get_watchlist(user_id, seg))
        if all_symbols:
            prices = get_live_prices_bulk(all_symbols[:20])
            logger.debug(f"Price refresh: {len(prices)} symbols")
    return Task("price_refresh", _refresh, interval)


def make_alert_check_task(user_id: str, interval: int = 30) -> Task:
    """Block 15: Check all price alerts every N seconds."""
    def _check():
        from storage import get_watchlist, get_settings
        from engine import get_live_prices_bulk
        from utils.notifications import AlertManager
        settings = get_settings(user_id)
        wl = get_watchlist(user_id, "equity")
        if not wl:
            return
        prices = get_live_prices_bulk(wl[:30])
        mgr = AlertManager(user_id)
        triggered = mgr.check_all(prices, settings)
        if triggered:
            logger.info(f"Alerts triggered: {[a['symbol'] for a in triggered]}")
    return Task("alert_check", _check, interval)


def make_auto_scan_task(user_id: str, interval: int = 60) -> Task:
    """Block 3/4-8: Auto-scan and optionally place orders."""
    def _scan():
        from storage import get_watchlist, get_settings, get_funds
        from engine import (get_ohlcv, compute_indicators, score_signal,
                            volatility_adjusted_position_size, calculate_targets_and_sl,
                            is_trading_allowed, place_order)
        settings = get_settings(user_id)
        if not settings.get("auto_trade_enabled", False):
            return

        # Check daily loss limit
        # (would read session state in production; here we log only)
        logger.info(f"Auto-scan running for {user_id}")

        for seg in ["equity", "futures", "mcx"]:
            wl = get_watchlist(user_id, seg)
            if not wl:
                continue
            allowed, reason = is_trading_allowed(seg)
            if not allowed:
                continue
            funds = get_funds(user_id)
            capital = funds.get(seg, 100000)

            for sym in wl[:10]:
                try:
                    df = get_ohlcv(sym, interval="FIVE_MINUTE", days=2)
                    if df.empty:
                        continue
                    df = compute_indicators(df)
                    direction, strength, _ = score_signal(df)
                    if strength < settings.get("signal_threshold", 70):
                        continue
                    row = df.iloc[-1]
                    atr = float(row.get("atr", float(row["close"]) * 0.01))
                    cmp = float(row["close"])
                    qty = volatility_adjusted_position_size(capital, atr, cmp, settings.get("risk_per_trade_pct", 1.0))
                    if qty > 0:
                        targets = calculate_targets_and_sl(cmp, atr, direction)
                        result = place_order(sym, direction, qty, cmp, seg,
                                             paper=settings.get("paper_mode", True))
                        if result["status"]:
                            logger.info(f"AUTO ORDER: {direction} {qty} {sym} @ {cmp}")
                except Exception as e:
                    logger.warning(f"Auto-scan {sym}: {e}")
    return Task("auto_scan", _scan, interval)


def make_eod_summary_task(user_id: str, send_time: str = "15:35") -> Task:
    """Block 12/34: Send EOD summary at market close."""
    def _eod():
        from storage import get_trade_history, get_settings
        from report import send_email_summary
        settings = get_settings(user_id)
        import datetime as dt
        today = str(dt.date.today())
        trades = [t for t in get_trade_history(user_id, limit=100)
                  if str(t.get("entry_time", "")).startswith(today)]
        pnl = sum(t.get("pnl", 0) for t in trades)
        logger.info(f"EOD summary for {user_id}: {len(trades)} trades, P&L: {pnl:+,.0f}")

        if settings.get("email_alerts") and settings.get("alert_email"):
            send_email_summary(user_id, settings["alert_email"], trades)

        if settings.get("whatsapp_alerts") and settings.get("whatsapp_phone"):
            from utils.notifications import send_whatsapp_message, build_eod_whatsapp_message
            msg = build_eod_whatsapp_message(user_id, trades, pnl,
                                              settings.get("daily_target", 5000))
            send_whatsapp_message(msg, settings["whatsapp_phone"])
    return Task("eod_summary", _eod, 0, run_at=send_time)


def make_mcx_session_task(user_id: str) -> Task:
    """Block 7: Scan MCX evening session (20:00–23:00)."""
    def _mcx_scan():
        now = datetime.datetime.now()
        if not (20 <= now.hour < 23):
            return
        from storage import get_watchlist, get_settings
        from engine import get_ohlcv, compute_indicators, score_signal
        settings = get_settings(user_id)
        if not settings.get("evening_session_mcx", True):
            return
        wl = get_watchlist(user_id, "mcx")
        for sym in wl[:5]:
            try:
                df = get_ohlcv(sym, interval="FIVE_MINUTE", days=1, exchange="MCX")
                if df.empty:
                    continue
                df = compute_indicators(df)
                direction, strength, _ = score_signal(df)
                if strength >= 70:
                    logger.info(f"MCX signal: {direction} {sym} ({strength:.0f}%)")
            except Exception as e:
                logger.warning(f"MCX scan {sym}: {e}")
    return Task("mcx_evening_scan", _mcx_scan, 120)


def make_premarket_task(user_id: str, run_at: str = "09:00") -> Task:
    """Block 12: Pre-market gap scan at 9 AM."""
    def _premarket():
        from engine import get_dynamic_universe, get_premarket_gaps
        universe = get_dynamic_universe("equity")
        symbols = [u["symbol"] if isinstance(u, dict) else u for u in universe[:50]]
        gaps = get_premarket_gaps(symbols)
        if gaps:
            logger.info(f"Pre-market gaps: {[g['symbol'] for g in gaps[:5]]}")
        from storage import set_value
        set_value(user_id, "premarket_gaps", gaps[:20])
    return Task("premarket_scan", _premarket, 0, run_at=run_at)
