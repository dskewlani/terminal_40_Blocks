"""
storage.py — ProTrader Terminal v2.0
PostgreSQL-backed storage with JSON fallback for all 40 blocks.
Per-user namespacing, audit trail, trade log, watchlists, settings.
"""

import os, json, time, hashlib, datetime
from pathlib import Path
from typing import Any, Optional
from loguru import logger

# ── SQLAlchemy (optional, falls back to JSON if no DB) ──────────────────────
try:
    from sqlalchemy import (
        create_engine, text, MetaData, Table, Column,
        String, Float, Integer, DateTime, Boolean, Text, JSON
    )
    from sqlalchemy.exc import OperationalError
    _SA_AVAILABLE = True
except ImportError:
    _SA_AVAILABLE = False

DATABASE_URL = os.getenv("DATABASE_URL", "")
_engine = None
_json_fallback_dir = Path("data")
_json_fallback_dir.mkdir(exist_ok=True)

# ── DB bootstrap ─────────────────────────────────────────────────────────────
_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS kv_store (
    user_id     TEXT NOT NULL,
    key         TEXT NOT NULL,
    value       TEXT,
    updated_at  TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, key)
);

CREATE TABLE IF NOT EXISTS trade_log (
    id              SERIAL PRIMARY KEY,
    user_id         TEXT,
    trade_id        TEXT UNIQUE,
    symbol          TEXT,
    segment         TEXT,
    side            TEXT,
    entry_price     FLOAT,
    exit_price      FLOAT,
    qty             INTEGER,
    entry_time      TIMESTAMP,
    exit_time       TIMESTAMP,
    pnl             FLOAT,
    pnl_pct         FLOAT,
    slippage        FLOAT,
    charges         FLOAT,
    net_pnl         FLOAT,
    strategy        TEXT,
    paper           BOOLEAN DEFAULT FALSE,
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alerts (
    id          SERIAL PRIMARY KEY,
    user_id     TEXT,
    symbol      TEXT,
    condition   TEXT,
    value       FLOAT,
    triggered   BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMP DEFAULT NOW(),
    triggered_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          SERIAL PRIMARY KEY,
    user_id     TEXT,
    action      TEXT,
    detail      TEXT,
    ip          TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tick_data (
    id          SERIAL PRIMARY KEY,
    symbol      TEXT,
    price       FLOAT,
    volume      BIGINT,
    ts          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    user_id     TEXT PRIMARY KEY,
    username    TEXT UNIQUE,
    pin_hash    TEXT,
    role        TEXT DEFAULT 'trader',
    paper_only  BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW()
);
"""


def _get_engine():
    global _engine
    if _engine is None and _SA_AVAILABLE and DATABASE_URL:
        try:
            _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
            with _engine.connect() as conn:
                for stmt in _CREATE_TABLES_SQL.split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        conn.execute(text(stmt))
                conn.commit()
            logger.info("DB connected and tables bootstrapped.")
        except Exception as e:
            logger.warning(f"DB init failed, using JSON fallback: {e}")
            _engine = None
    return _engine


# ── User helpers ─────────────────────────────────────────────────────────────
def get_user_storage_key(user_id: str, key: str) -> str:
    return f"{user_id}:{key}"


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


# ── KV Store ─────────────────────────────────────────────────────────────────
def set_value(user_id: str, key: str, value: Any) -> bool:
    """Persist any JSON-serializable value for a user."""
    serialized = json.dumps(value)
    engine = _get_engine()
    if engine:
        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO kv_store(user_id, key, value, updated_at)
                    VALUES (:u, :k, :v, NOW())
                    ON CONFLICT (user_id, key) DO UPDATE
                    SET value=EXCLUDED.value, updated_at=NOW()
                """), {"u": user_id, "k": key, "v": serialized})
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"set_value DB error: {e}")

    # JSON fallback
    path = _json_fallback_dir / f"{user_id}.json"
    store = {}
    if path.exists():
        try:
            store = json.loads(path.read_text())
        except Exception:
            pass
    store[key] = value
    path.write_text(json.dumps(store, indent=2))
    return True


def get_value(user_id: str, key: str, default: Any = None) -> Any:
    """Retrieve a value for a user."""
    engine = _get_engine()
    if engine:
        try:
            with engine.connect() as conn:
                row = conn.execute(text(
                    "SELECT value FROM kv_store WHERE user_id=:u AND key=:k"
                ), {"u": user_id, "k": key}).fetchone()
            if row:
                return json.loads(row[0])
        except Exception as e:
            logger.error(f"get_value DB error: {e}")

    path = _json_fallback_dir / f"{user_id}.json"
    if path.exists():
        try:
            store = json.loads(path.read_text())
            return store.get(key, default)
        except Exception:
            pass
    return default


def delete_value(user_id: str, key: str) -> bool:
    engine = _get_engine()
    if engine:
        try:
            with engine.connect() as conn:
                conn.execute(text(
                    "DELETE FROM kv_store WHERE user_id=:u AND key=:k"
                ), {"u": user_id, "k": key})
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"delete_value DB error: {e}")
    path = _json_fallback_dir / f"{user_id}.json"
    if path.exists():
        store = json.loads(path.read_text())
        store.pop(key, None)
        path.write_text(json.dumps(store, indent=2))
    return True


# ── Trade Log ────────────────────────────────────────────────────────────────
def log_trade(trade: dict) -> bool:
    """Write a completed trade to the trade_log table."""
    engine = _get_engine()
    if engine:
        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO trade_log
                    (user_id,trade_id,symbol,segment,side,entry_price,exit_price,
                     qty,entry_time,exit_time,pnl,pnl_pct,slippage,charges,
                     net_pnl,strategy,paper,notes)
                    VALUES
                    (:user_id,:trade_id,:symbol,:segment,:side,:entry_price,
                     :exit_price,:qty,:entry_time,:exit_time,:pnl,:pnl_pct,
                     :slippage,:charges,:net_pnl,:strategy,:paper,:notes)
                    ON CONFLICT (trade_id) DO NOTHING
                """), trade)
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"log_trade DB error: {e}")
    # fallback
    trades = get_value("system", "trade_log_fallback") or []
    trades.append(trade)
    set_value("system", "trade_log_fallback", trades[-5000:])
    return True


def get_trade_history(user_id: str, limit: int = 500, paper: bool = False) -> list:
    engine = _get_engine()
    if engine:
        try:
            with engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT * FROM trade_log
                    WHERE user_id=:u AND paper=:p
                    ORDER BY entry_time DESC LIMIT :lim
                """), {"u": user_id, "p": paper, "lim": limit}).fetchall()
            return [dict(r._mapping) for r in rows]
        except Exception as e:
            logger.error(f"get_trade_history DB error: {e}")
    trades = get_value("system", "trade_log_fallback") or []
    return [t for t in trades if t.get("user_id") == user_id and t.get("paper", False) == paper][:limit]


# ── Alerts ───────────────────────────────────────────────────────────────────
def save_alert(user_id: str, symbol: str, condition: str, value: float) -> bool:
    alerts = get_value(user_id, "price_alerts") or []
    alerts.append({
        "symbol": symbol, "condition": condition, "value": value,
        "triggered": False, "created_at": str(datetime.datetime.now())
    })
    return set_value(user_id, "price_alerts", alerts)


def get_alerts(user_id: str) -> list:
    return get_value(user_id, "price_alerts") or []


def mark_alert_triggered(user_id: str, idx: int) -> bool:
    alerts = get_alerts(user_id)
    if 0 <= idx < len(alerts):
        alerts[idx]["triggered"] = True
        alerts[idx]["triggered_at"] = str(datetime.datetime.now())
        return set_value(user_id, "price_alerts", alerts)
    return False


# ── Audit Trail ──────────────────────────────────────────────────────────────
def audit(user_id: str, action: str, detail: str = "", ip: str = "") -> None:
    engine = _get_engine()
    record = {
        "user_id": user_id, "action": action, "detail": detail,
        "ip": ip, "ts": str(datetime.datetime.now())
    }
    if engine:
        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO audit_log(user_id,action,detail,ip)
                    VALUES (:user_id,:action,:detail,:ip)
                """), record)
                conn.commit()
            return
        except Exception as e:
            logger.error(f"audit DB error: {e}")
    log = get_value("system", "audit_fallback") or []
    log.append(record)
    set_value("system", "audit_fallback", log[-10000:])


def get_audit_log(user_id: str = None, limit: int = 100) -> list:
    engine = _get_engine()
    if engine:
        try:
            with engine.connect() as conn:
                if user_id:
                    rows = conn.execute(text(
                        "SELECT * FROM audit_log WHERE user_id=:u ORDER BY created_at DESC LIMIT :lim"
                    ), {"u": user_id, "lim": limit}).fetchall()
                else:
                    rows = conn.execute(text(
                        "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT :lim"
                    ), {"lim": limit}).fetchall()
            return [dict(r._mapping) for r in rows]
        except Exception as e:
            logger.error(f"get_audit_log DB error: {e}")
    log = get_value("system", "audit_fallback") or []
    if user_id:
        log = [l for l in log if l.get("user_id") == user_id]
    return log[:limit]


# ── User Auth ─────────────────────────────────────────────────────────────────
def create_user(username: str, pin: str, role: str = "trader") -> bool:
    users = get_value("system", "users") or {}
    if username in users:
        return False
    users[username] = {
        "user_id": username,
        "username": username,
        "pin_hash": hash_pin(pin),
        "role": role,
        "paper_only": True,
        "created_at": str(datetime.datetime.now())
    }
    return set_value("system", "users", users)


def authenticate_user(username: str, pin: str) -> Optional[dict]:
    users = get_value("system", "users") or {}
    if not users:
        # Auto-create admin on first run
        create_user("admin", os.getenv("ADMIN_PIN", "123456"), "admin")
        users = get_value("system", "users") or {}
    user = users.get(username)
    if user and user.get("pin_hash") == hash_pin(pin):
        return user
    return None


def get_all_users() -> list:
    users = get_value("system", "users") or {}
    return list(users.values())


def update_user(username: str, updates: dict) -> bool:
    users = get_value("system", "users") or {}
    if username in users:
        users[username].update(updates)
        return set_value("system", "users", users)
    return False


# ── Watchlists ───────────────────────────────────────────────────────────────
def get_watchlist(user_id: str, segment: str) -> list:
    return get_value(user_id, f"watchlist_{segment.lower()}") or []


def set_watchlist(user_id: str, segment: str, symbols: list) -> bool:
    return set_value(user_id, f"watchlist_{segment.lower()}", symbols)


def add_to_watchlist(user_id: str, segment: str, symbol: str) -> bool:
    wl = get_watchlist(user_id, segment)
    if symbol not in wl:
        wl.append(symbol)
        return set_watchlist(user_id, segment, wl)
    return True


def remove_from_watchlist(user_id: str, segment: str, symbol: str) -> bool:
    wl = get_watchlist(user_id, segment)
    wl = [s for s in wl if s != symbol]
    return set_watchlist(user_id, segment, wl)


# ── Drawing Tools (Block 27) ─────────────────────────────────────────────────
def save_drawing(user_id: str, symbol: str, drawing: dict) -> bool:
    key = f"drawings_{symbol}"
    drawings = get_value(user_id, key) or []
    drawings.append(drawing)
    return set_value(user_id, key, drawings)


def get_drawings(user_id: str, symbol: str) -> list:
    return get_value(user_id, f"drawings_{symbol}") or []


def clear_drawings(user_id: str, symbol: str) -> bool:
    return set_value(user_id, f"drawings_{symbol}", [])


# ── Confidence Journal (Block 21) ─────────────────────────────────────────────
def save_confidence_entry(user_id: str, score: int, note: str = "") -> bool:
    entries = get_value(user_id, "confidence_journal") or []
    entries.append({
        "date": str(datetime.date.today()),
        "score": score,
        "note": note,
        "ts": str(datetime.datetime.now())
    })
    return set_value(user_id, "confidence_journal", entries[-365:])


def get_confidence_entries(user_id: str, days: int = 30) -> list:
    entries = get_value(user_id, "confidence_journal") or []
    cutoff = str(datetime.date.today() - datetime.timedelta(days=days))
    return [e for e in entries if e.get("date", "") >= cutoff]


# ── Paper Portfolio ───────────────────────────────────────────────────────────
def get_paper_portfolio(user_id: str) -> dict:
    return get_value(user_id, "paper_portfolio") or {
        "capital": 500000.0, "positions": [], "pnl": 0.0
    }


def set_paper_portfolio(user_id: str, portfolio: dict) -> bool:
    return set_value(user_id, "paper_portfolio", portfolio)


def reset_paper_portfolio(user_id: str, capital: float = 500000.0) -> bool:
    return set_paper_portfolio(user_id, {
        "capital": capital, "positions": [], "pnl": 0.0,
        "reset_at": str(datetime.datetime.now())
    })


# ── Fund Management (Block 14) ────────────────────────────────────────────────
def get_funds(user_id: str) -> dict:
    return get_value(user_id, "fund_allocation") or {
        "intraday": 200000, "swing": 150000,
        "options": 100000, "mcx": 50000, "etf": 50000
    }


def set_funds(user_id: str, funds: dict) -> bool:
    return set_value(user_id, "fund_allocation", funds)


# ── Settings ─────────────────────────────────────────────────────────────────
_DEFAULT_SETTINGS = {
    "theme": "dark",
    "accent": "blue",
    "density": "comfortable",
    "daily_target": 5000,
    "daily_loss_limit": 3000,
    "max_trades_per_day": 10,
    "paper_mode": True,
    "auto_trade_enabled": False,
    "risk_per_trade_pct": 1.0,
    "kelly_fraction": 0.5,
    "mtf_confirm": True,
    "iv_rank_threshold": 30,
    "sound_alerts": True,
    "browser_notifications": False,
    "whatsapp_alerts": False,
    "email_alerts": False,
    "evening_session_mcx": True,
    "paper_days_enforced": 7,
    "onboarding_done": False,
    "confidence_threshold_trade": 5,
    "max_correlation": 0.8,
    "colorblind_mode": False,
    "show_vwap": True,
    "show_supertrend": True,
    "show_ema": True,
    "show_bb": False,
}


def get_settings(user_id: str) -> dict:
    stored = get_value(user_id, "settings") or {}
    return {**_DEFAULT_SETTINGS, **stored}


def update_settings(user_id: str, updates: dict) -> bool:
    settings = get_settings(user_id)
    settings.update(updates)
    return set_value(user_id, "settings", settings)


# ── Strategies (Block 31) ─────────────────────────────────────────────────────
def save_strategy(user_id: str, name: str, definition: dict) -> bool:
    strategies = get_value(user_id, "strategies") or {}
    strategies[name] = {**definition, "name": name, "created_at": str(datetime.datetime.now())}
    return set_value(user_id, "strategies", strategies)


def get_strategies(user_id: str) -> dict:
    return get_value(user_id, "strategies") or {}


def delete_strategy(user_id: str, name: str) -> bool:
    strategies = get_strategies(user_id)
    strategies.pop(name, None)
    return set_value(user_id, "strategies", strategies)


# ── Tax records (Block 23) ────────────────────────────────────────────────────
def get_tax_year_trades(user_id: str, fy: str) -> list:
    """FY format: '2024-25'"""
    all_trades = get_trade_history(user_id, limit=10000)
    year_start = int(fy.split("-")[0])
    start = datetime.datetime(year_start, 4, 1)
    end = datetime.datetime(year_start + 1, 3, 31)
    result = []
    for t in all_trades:
        try:
            et = datetime.datetime.fromisoformat(str(t.get("entry_time", "")))
            if start <= et <= end:
                result.append(t)
        except Exception:
            pass
    return result
