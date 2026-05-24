"""
utils/indicators.py — ProTrader Terminal v2.0
Extended indicator library. All functions accept pandas Series/DataFrame.
Used by engine.py, backtest.py, and scan pipelines.
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple


# ─── Trend ───────────────────────────────────────────────────────────────────

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def wma(series: pd.Series, period: int) -> pd.Series:
    weights = np.arange(1, period + 1)
    return series.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)


def hull_ma(series: pd.Series, period: int) -> pd.Series:
    half = int(period / 2)
    sqrt_period = int(np.sqrt(period))
    wma1 = wma(series, half)
    wma2 = wma(series, period)
    diff = 2 * wma1 - wma2
    return wma(diff, sqrt_period)


def dema(series: pd.Series, period: int) -> pd.Series:
    """Double EMA."""
    e = ema(series, period)
    return 2 * e - ema(e, period)


def tema(series: pd.Series, period: int) -> pd.Series:
    """Triple EMA."""
    e1 = ema(series, period)
    e2 = ema(e1, period)
    e3 = ema(e2, period)
    return 3 * e1 - 3 * e2 + e3


def ichimoku(df: pd.DataFrame) -> pd.DataFrame:
    """Ichimoku Cloud — Tenkan, Kijun, Senkou A/B, Chikou."""
    high = df["high"]
    low = df["low"]
    close = df["close"]

    tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
    kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
    senkou_a = ((tenkan + kijun) / 2).shift(26)
    senkou_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
    chikou = close.shift(-26)

    df["ichi_tenkan"] = tenkan
    df["ichi_kijun"] = kijun
    df["ichi_senkou_a"] = senkou_a
    df["ichi_senkou_b"] = senkou_b
    df["ichi_chikou"] = chikou
    return df


def parabolic_sar(high: pd.Series, low: pd.Series,
                   af_start: float = 0.02, af_max: float = 0.2) -> pd.Series:
    """Parabolic SAR."""
    sar = pd.Series(index=high.index, dtype=float)
    n = len(high)
    if n < 2:
        return sar
    bull = True
    af = af_start
    ep = float(low.iloc[0])
    current_sar = float(high.iloc[0])

    for i in range(1, n):
        prev_sar = current_sar
        if bull:
            current_sar = prev_sar + af * (ep - prev_sar)
            current_sar = min(current_sar, float(low.iloc[i-1]))
            if i > 1:
                current_sar = min(current_sar, float(low.iloc[i-2]))
            if float(low.iloc[i]) < current_sar:
                bull = False
                current_sar = ep
                ep = float(low.iloc[i])
                af = af_start
            else:
                if float(high.iloc[i]) > ep:
                    ep = float(high.iloc[i])
                    af = min(af + af_start, af_max)
        else:
            current_sar = prev_sar + af * (ep - prev_sar)
            current_sar = max(current_sar, float(high.iloc[i-1]))
            if i > 1:
                current_sar = max(current_sar, float(high.iloc[i-2]))
            if float(high.iloc[i]) > current_sar:
                bull = True
                current_sar = ep
                ep = float(high.iloc[i])
                af = af_start
            else:
                if float(low.iloc[i]) < ep:
                    ep = float(low.iloc[i])
                    af = min(af + af_start, af_max)
        sar.iloc[i] = current_sar
    return sar


# ─── Momentum ─────────────────────────────────────────────────────────────────

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(com=period - 1, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=period - 1, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def stochastic_rsi(series: pd.Series, period: int = 14,
                    smooth_k: int = 3, smooth_d: int = 3) -> Tuple[pd.Series, pd.Series]:
    r = rsi(series, period)
    stoch = (r - r.rolling(period).min()) / (r.rolling(period).max() - r.rolling(period).min() + 1e-9)
    k = stoch.rolling(smooth_k).mean() * 100
    d = k.rolling(smooth_d).mean()
    return k, d


def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
    tp = (high + low + close) / 3
    sma_tp = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (tp - sma_tp) / (0.015 * mad + 1e-9)


def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    highest = high.rolling(period).max()
    lowest = low.rolling(period).min()
    return -100 * (highest - close) / (highest - lowest + 1e-9)


def awesome_oscillator(high: pd.Series, low: pd.Series) -> pd.Series:
    mid = (high + low) / 2
    return sma(mid, 5) - sma(mid, 34)


def tsi(close: pd.Series, long: int = 25, short: int = 13) -> pd.Series:
    """True Strength Index."""
    diff = close.diff()
    double_smoothed = ema(ema(diff, long), short)
    double_smoothed_abs = ema(ema(diff.abs(), long), short)
    return 100 * double_smoothed / (double_smoothed_abs + 1e-9)


def rate_of_change(series: pd.Series, period: int = 12) -> pd.Series:
    return (series - series.shift(period)) / series.shift(period) * 100


# ─── Volatility ───────────────────────────────────────────────────────────────

def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(com=period - 1, adjust=False).mean()


def keltner_channel(high: pd.Series, low: pd.Series, close: pd.Series,
                     period: int = 20, mult: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    mid = ema(close, period)
    a = atr(high, low, close, period)
    return mid + mult * a, mid, mid - mult * a


def donchian_channel(high: pd.Series, low: pd.Series,
                      period: int = 20) -> Tuple[pd.Series, pd.Series, pd.Series]:
    upper = high.rolling(period).max()
    lower = low.rolling(period).min()
    mid = (upper + lower) / 2
    return upper, mid, lower


def historical_volatility(close: pd.Series, period: int = 20, annualize: bool = True) -> pd.Series:
    log_ret = np.log(close / close.shift(1))
    hv = log_ret.rolling(period).std()
    if annualize:
        hv = hv * np.sqrt(252)
    return hv * 100


def average_true_range_percent(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """ATR as percentage of close."""
    a = atr(high, low, close, period)
    return a / close * 100


# ─── Volume ───────────────────────────────────────────────────────────────────

def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume."""
    direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    return (direction * volume).cumsum()


def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    tp = (high + low + close) / 3
    return (tp * volume).cumsum() / volume.cumsum()


def money_flow_index(high: pd.Series, low: pd.Series, close: pd.Series,
                      volume: pd.Series, period: int = 14) -> pd.Series:
    tp = (high + low + close) / 3
    mf = tp * volume
    pos_mf = mf.where(tp > tp.shift(1), 0).rolling(period).sum()
    neg_mf = mf.where(tp <= tp.shift(1), 0).rolling(period).sum()
    return 100 - (100 / (1 + pos_mf / (neg_mf + 1e-9)))


def chaikin_money_flow(high: pd.Series, low: pd.Series, close: pd.Series,
                        volume: pd.Series, period: int = 20) -> pd.Series:
    clv = ((close - low) - (high - close)) / (high - low + 1e-9)
    mfv = clv * volume
    return mfv.rolling(period).sum() / volume.rolling(period).sum()


def volume_weighted_rsi(close: pd.Series, volume: pd.Series, period: int = 14) -> pd.Series:
    """Volume-weighted RSI variant."""
    delta = close.diff()
    vol_weighted = delta * volume
    gain = vol_weighted.clip(lower=0).rolling(period).sum()
    loss = (-vol_weighted.clip(upper=0)).rolling(period).sum()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))


def ease_of_movement(high: pd.Series, low: pd.Series, volume: pd.Series,
                      period: int = 14) -> pd.Series:
    """Ease of Movement (EMV)."""
    distance = (high + low) / 2 - (high.shift(1) + low.shift(1)) / 2
    box_ratio = volume / (high - low + 1e-9)
    emv = distance / box_ratio
    return emv.rolling(period).mean()


# ─── Support / Resistance ─────────────────────────────────────────────────────

def pivot_points(high: float, low: float, close: float) -> dict:
    """Classic, Fibonacci, Camarilla pivot points."""
    pivot = (high + low + close) / 3
    r1 = 2 * pivot - low
    s1 = 2 * pivot - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    r3 = high + 2 * (pivot - low)
    s3 = low - 2 * (high - pivot)

    # Fibonacci
    fr1 = pivot + 0.382 * (high - low)
    fs1 = pivot - 0.382 * (high - low)
    fr2 = pivot + 0.618 * (high - low)
    fs2 = pivot - 0.618 * (high - low)
    fr3 = pivot + 1.000 * (high - low)
    fs3 = pivot - 1.000 * (high - low)

    return {
        "pivot": round(pivot, 2),
        "r1": round(r1, 2), "r2": round(r2, 2), "r3": round(r3, 2),
        "s1": round(s1, 2), "s2": round(s2, 2), "s3": round(s3, 2),
        "fib_r1": round(fr1, 2), "fib_r2": round(fr2, 2), "fib_r3": round(fr3, 2),
        "fib_s1": round(fs1, 2), "fib_s2": round(fs2, 2), "fib_s3": round(fs3, 2),
    }


def find_swing_highs_lows(high: pd.Series, low: pd.Series,
                            window: int = 5) -> Tuple[pd.Series, pd.Series]:
    """Detect swing highs and lows for SR mapping."""
    swing_highs = high[(high == high.rolling(window * 2 + 1, center=True).max())]
    swing_lows = low[(low == low.rolling(window * 2 + 1, center=True).min())]
    return swing_highs, swing_lows


def detect_support_resistance(df: pd.DataFrame,
                               n_levels: int = 5,
                               tolerance: float = 0.002) -> dict:
    """Cluster-based support and resistance levels."""
    highs, lows = find_swing_highs_lows(df["high"], df["low"])
    all_levels = list(highs.values) + list(lows.values)
    if not all_levels:
        return {"support": [], "resistance": []}

    all_levels.sort()
    clusters = []
    current_cluster = [all_levels[0]]
    for level in all_levels[1:]:
        if abs(level - current_cluster[-1]) / current_cluster[-1] <= tolerance:
            current_cluster.append(level)
        else:
            clusters.append(current_cluster)
            current_cluster = [level]
    clusters.append(current_cluster)

    centroids = sorted([np.mean(c) for c in clusters], key=lambda x: len([c for c in clusters if abs(np.mean(c) - x) < 1]), reverse=True)
    current_price = float(df["close"].iloc[-1])
    resistance = sorted([c for c in centroids if c > current_price])[:n_levels]
    support = sorted([c for c in centroids if c <= current_price], reverse=True)[:n_levels]
    return {
        "support": [round(x, 2) for x in support],
        "resistance": [round(x, 2) for x in resistance]
    }


# ─── Pattern Recognition ──────────────────────────────────────────────────────

def detect_doji(open_: pd.Series, close: pd.Series, high: pd.Series,
                 low: pd.Series, threshold: float = 0.05) -> pd.Series:
    body = (close - open_).abs()
    total_range = high - low + 1e-9
    return body / total_range < threshold


def detect_hammer(open_: pd.Series, close: pd.Series, high: pd.Series,
                   low: pd.Series) -> pd.Series:
    body = (close - open_).abs()
    lower_wick = pd.concat([open_, close], axis=1).min(axis=1) - low
    upper_wick = high - pd.concat([open_, close], axis=1).max(axis=1)
    return (lower_wick >= 2 * body) & (upper_wick <= 0.3 * body)


def detect_engulfing(open_: pd.Series, close: pd.Series) -> Tuple[pd.Series, pd.Series]:
    prev_open = open_.shift(1)
    prev_close = close.shift(1)
    bullish = (prev_close < prev_open) & (close > open_) & (open_ < prev_close) & (close > prev_open)
    bearish = (prev_close > prev_open) & (close < open_) & (open_ > prev_close) & (close < prev_open)
    return bullish, bearish


def detect_morning_star(open_: pd.Series, close: pd.Series) -> pd.Series:
    c1_bear = close.shift(2) < open_.shift(2)
    c2_small = (close.shift(1) - open_.shift(1)).abs() < (open_.shift(2) - close.shift(2)) * 0.3
    c3_bull = close > open_
    c3_recovers = close > (open_.shift(2) + close.shift(2)) / 2
    return c1_bear & c2_small & c3_bull & c3_recovers


def detect_inside_bar(high: pd.Series, low: pd.Series) -> pd.Series:
    return (high < high.shift(1)) & (low > low.shift(1))


def pattern_summary(df: pd.DataFrame) -> dict:
    """Run all pattern detectors on the last bar."""
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    patterns = {}
    try:
        patterns["doji"] = bool(detect_doji(o, c, h, l).iloc[-1])
        patterns["hammer"] = bool(detect_hammer(o, c, h, l).iloc[-1])
        bull_eng, bear_eng = detect_engulfing(o, c)
        patterns["bullish_engulfing"] = bool(bull_eng.iloc[-1])
        patterns["bearish_engulfing"] = bool(bear_eng.iloc[-1])
        patterns["morning_star"] = bool(detect_morning_star(o, c).iloc[-1])
        patterns["inside_bar"] = bool(detect_inside_bar(h, l).iloc[-1])
    except Exception:
        pass
    return {k: v for k, v in patterns.items() if v}


# ─── Market Structure ─────────────────────────────────────────────────────────

def detect_higher_highs_higher_lows(high: pd.Series, low: pd.Series,
                                      window: int = 3) -> bool:
    """Uptrend structure: HH + HL."""
    if len(high) < window * 2:
        return False
    recent_highs = high.iloc[-window:]
    recent_lows = low.iloc[-window:]
    return bool(recent_highs.is_monotonic_increasing and recent_lows.is_monotonic_increasing)


def detect_lower_highs_lower_lows(high: pd.Series, low: pd.Series,
                                    window: int = 3) -> bool:
    """Downtrend structure: LH + LL."""
    if len(high) < window * 2:
        return False
    recent_highs = high.iloc[-window:]
    recent_lows = low.iloc[-window:]
    return bool(recent_highs.is_monotonic_decreasing and recent_lows.is_monotonic_decreasing)


def compute_all_extended(df: pd.DataFrame) -> pd.DataFrame:
    """Add all extended indicators to a OHLCV DataFrame."""
    if df.empty or len(df) < 35:
        return df
    h, l, c, o, v = df["high"], df["low"], df["close"], df["open"], df["volume"]

    # Hull MA
    df["hma21"] = hull_ma(c, 21)

    # Parabolic SAR
    df["psar"] = parabolic_sar(h, l)

    # Ichimoku
    df = ichimoku(df)

    # Stochastic RSI
    df["stoch_rsi_k"], df["stoch_rsi_d"] = stochastic_rsi(c)

    # OBV
    df["obv"] = obv(c, v)

    # CMF
    df["cmf"] = chaikin_money_flow(h, l, c, v)

    # Historical volatility
    df["hv20"] = historical_volatility(c, 20)

    # Ease of movement
    df["eom"] = ease_of_movement(h, l, v)

    # Rate of change
    df["roc12"] = rate_of_change(c, 12)

    # TSI
    df["tsi"] = tsi(c)

    # Keltner channels
    df["kc_upper"], df["kc_mid"], df["kc_lower"] = keltner_channel(h, l, c)

    # Donchian
    df["dc_upper"], df["dc_mid"], df["dc_lower"] = donchian_channel(h, l)

    # Patterns on last bar (stored as flags)
    patterns = pattern_summary(df)
    df["pattern_doji"] = detect_doji(o, c, h, l)
    df["pattern_hammer"] = detect_hammer(o, c, h, l)
    bull_eng, bear_eng = detect_engulfing(o, c)
    df["pattern_bull_eng"] = bull_eng
    df["pattern_bear_eng"] = bear_eng
    df["pattern_inside_bar"] = detect_inside_bar(h, l)

    return df
