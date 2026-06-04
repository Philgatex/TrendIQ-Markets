import numpy as np
import pandas as pd


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    return rsi.fillna(50)


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()

    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(period).mean()

    return atr.bfill()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    data = df.copy()

    data["EMA20"] = data["Close"].ewm(span=20, adjust=False).mean()
    data["EMA50"] = data["Close"].ewm(span=50, adjust=False).mean()
    data["EMA200"] = data["Close"].ewm(span=200, adjust=False).mean()

    data["RSI14"] = calculate_rsi(data["Close"], 14)

    ema12 = data["Close"].ewm(span=12, adjust=False).mean()
    ema26 = data["Close"].ewm(span=26, adjust=False).mean()

    data["MACD"] = ema12 - ema26
    data["MACD_SIGNAL"] = data["MACD"].ewm(span=9, adjust=False).mean()
    data["MACD_HIST"] = data["MACD"] - data["MACD_SIGNAL"]

    data["ATR14"] = calculate_atr(data, 14)

    data["BB_MIDDLE"] = data["Close"].rolling(20).mean()
    data["BB_STD"] = data["Close"].rolling(20).std()
    data["BB_UPPER"] = data["BB_MIDDLE"] + (2 * data["BB_STD"])
    data["BB_LOWER"] = data["BB_MIDDLE"] - (2 * data["BB_STD"])

    data = data.bfill().ffill()

    return data


def detect_support_resistance(df: pd.DataFrame, lookback: int = 50) -> dict:
    if df is None or df.empty:
        return {
            "support": None,
            "resistance": None,
            "recent_low": None,
            "recent_high": None
        }

    recent = df.tail(lookback).copy()

    recent_low = float(recent["Low"].min())
    recent_high = float(recent["High"].max())

    support_series = recent["Low"].rolling(5).min().dropna().tail(10)
    resistance_series = recent["High"].rolling(5).max().dropna().tail(10)

    support = float(support_series.mean()) if not support_series.empty else recent_low
    resistance = float(resistance_series.mean()) if not resistance_series.empty else recent_high

    return {
        "support": support,
        "resistance": resistance,
        "recent_low": recent_low,
        "recent_high": recent_high
    }


def get_indicator_summary(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {
            "trend": "No Data",
            "rsi_status": "No Data",
            "macd_status": "No Data",
            "volatility_status": "No Data"
        }

    latest = df.iloc[-1]

    close = float(latest["Close"])
    ema20 = float(latest["EMA20"])
    ema50 = float(latest["EMA50"])
    ema200 = float(latest["EMA200"])
    rsi = float(latest["RSI14"])
    macd = float(latest["MACD"])
    macd_signal = float(latest["MACD_SIGNAL"])
    atr = float(latest["ATR14"])

    if close > ema20 > ema50 > ema200:
        trend = "Strong Bullish"
    elif close > ema20 and ema20 > ema50:
        trend = "Bullish"
    elif close < ema20 < ema50 < ema200:
        trend = "Strong Bearish"
    elif close < ema20 and ema20 < ema50:
        trend = "Bearish"
    else:
        trend = "Sideways / Mixed"

    if rsi >= 70:
        rsi_status = "Overbought"
    elif rsi >= 55:
        rsi_status = "Bullish Momentum"
    elif rsi <= 30:
        rsi_status = "Oversold"
    elif rsi <= 45:
        rsi_status = "Bearish Momentum"
    else:
        rsi_status = "Neutral"

    macd_status = "Bullish" if macd > macd_signal else "Bearish"

    atr_pct = (atr / close) * 100 if close != 0 else 0

    if atr_pct >= 2:
        volatility_status = "High Volatility"
    elif atr_pct >= 1:
        volatility_status = "Moderate Volatility"
    else:
        volatility_status = "Low Volatility"

    return {
        "latest_close": close,
        "ema20": ema20,
        "ema50": ema50,
        "ema200": ema200,
        "rsi": rsi,
        "atr": atr,
        "trend": trend,
        "rsi_status": rsi_status,
        "macd_status": macd_status,
        "volatility_status": volatility_status
    }
