import os

import pandas as pd
import requests
import yfinance as yf

DATA_PROVIDERS = {
    "Yahoo Finance (yfinance)": "yfinance",
    "Twelve Data (free API)": "twelvedata",
    "Finnhub (free API)": "finnhub",
    "Alpha Vantage (free API)": "alphavantage",
    "CCXT (Binance)": "ccxt",
    "MetaTrader 5 (local connector)": "mt5",
}

TWELVE_DATA_BASE = "https://api.twelvedata.com"

TWELVEDATA_SYMBOL_MAP = {
    "EURUSD=X": "EUR/USD",
    "GBPUSD=X": "GBP/USD",
    "JPY=X": "USD/JPY",
    "AUDUSD=X": "AUD/USD",
    "CAD=X": "USD/CAD",
    "CHF=X": "USD/CHF",
    "EURJPY=X": "EUR/JPY",
    "GBPJPY=X": "GBP/JPY",
    "AUDJPY=X": "AUD/JPY",
    "EURGBP=X": "EUR/GBP",
    "BTC-USD": "BTC/USD",
    "ETH-USD": "ETH/USD",
    "LTC-USD": "LTC/USD",
    "XRP-USD": "XRP/USD",
}

MARKET_SYMBOLS = {
    "Nasdaq-100 / US100 Proxy": {"symbol": "QQQ", "type": "index", "description": "Nasdaq-100 ETF proxy"},
    "S&P 500 / US500 Proxy": {"symbol": "SPY", "type": "index", "description": "S&P 500 ETF proxy"},
    "Dow Jones / US30 Proxy": {"symbol": "DIA", "type": "index", "description": "Dow Jones Industrial Average ETF proxy"},
    "Russell 2000 Proxy": {"symbol": "IWM", "type": "index", "description": "Russell 2000 ETF proxy"},
    "FTSE 100": {"symbol": "^FTSE", "type": "index", "description": "UK FTSE 100 Index"},
    "Nikkei 225": {"symbol": "^N225", "type": "index", "description": "Japan Nikkei 225 Index"},
    "Hang Seng": {"symbol": "^HSI", "type": "index", "description": "Hong Kong Hang Seng Index"},
    "DAX Germany": {"symbol": "^GDAXI", "type": "index", "description": "Germany DAX Index"},
    "Gold": {"symbol": "GC=F", "type": "commodity", "description": "Gold futures proxy"},
    "Silver": {"symbol": "SI=F", "type": "commodity", "description": "Silver futures proxy"},
    "WTI Crude Oil": {"symbol": "CL=F", "type": "commodity", "description": "WTI crude oil futures"},
    "Brent Crude Oil": {"symbol": "BZ=F", "type": "commodity", "description": "Brent crude oil futures"},
    "Bitcoin": {"symbol": "BTC-USD", "type": "crypto", "description": "Bitcoin against USD"},
    "Ethereum": {"symbol": "ETH-USD", "type": "crypto", "description": "Ethereum against USD"},
    "Litecoin": {"symbol": "LTC-USD", "type": "crypto", "description": "Litecoin against USD"},
    "Ripple": {"symbol": "XRP-USD", "type": "crypto", "description": "Ripple against USD"},
    "EUR/USD": {"symbol": "EURUSD=X", "type": "forex", "description": "Euro against US Dollar"},
    "GBP/USD": {"symbol": "GBPUSD=X", "type": "forex", "description": "British Pound against US Dollar"},
    "USD/JPY": {"symbol": "JPY=X", "type": "forex", "description": "US Dollar against Japanese Yen"},
    "AUD/USD": {"symbol": "AUDUSD=X", "type": "forex", "description": "Australian Dollar against US Dollar"},
    "USD/CAD": {"symbol": "CAD=X", "type": "forex", "description": "US Dollar against Canadian Dollar"},
    "USD/CHF": {"symbol": "CHF=X", "type": "forex", "description": "US Dollar against Swiss Franc"},
    "EUR/JPY": {"symbol": "EURJPY=X", "type": "forex", "description": "Euro against Japanese Yen"},
    "GBP/JPY": {"symbol": "GBPJPY=X", "type": "forex", "description": "British Pound against Japanese Yen"},
    "AUD/JPY": {"symbol": "AUDJPY=X", "type": "forex", "description": "Australian Dollar against Japanese Yen"},
    "EUR/GBP": {"symbol": "EURGBP=X", "type": "forex", "description": "Euro against British Pound"},
    "US 10Y Yield": {"symbol": "^TNX", "type": "bond", "description": "US 10-year Treasury yield proxy"},
    "US 30Y Yield": {"symbol": "^TYX", "type": "bond", "description": "US 30-year Treasury yield proxy"},
    "XM EUR/USD": {"symbol": "EURUSD=X", "type": "forex", "description": "XM broker EUR/USD"},
    "XM GBP/USD": {"symbol": "GBPUSD=X", "type": "forex", "description": "XM broker GBP/USD"},
    "XM Gold": {"symbol": "GC=F", "type": "commodity", "description": "XM broker Gold"},
    "XM Silver": {"symbol": "SI=F", "type": "commodity", "description": "XM broker Silver"},
    "XM Crude Oil": {"symbol": "CL=F", "type": "commodity", "description": "XM broker WTI Crude Oil"},
    "XM Bitcoin": {"symbol": "BTC-USD", "type": "crypto", "description": "XM broker Bitcoin"},
    "MT5 NASDAQ 100": {"symbol": "QQQ", "type": "index", "description": "MT5-style Nasdaq 100 proxy"},
    "MT5 S&P 500": {"symbol": "SPY", "type": "index", "description": "MT5-style S&P 500 proxy"},
    "MT5 Dow Jones": {"symbol": "DIA", "type": "index", "description": "MT5-style Dow Jones proxy"},
}


def clean_yfinance_data(data: pd.DataFrame) -> pd.DataFrame:
    if data is None or data.empty:
        return pd.DataFrame()

    data = data.copy()

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [col[0] for col in data.columns]

    data = data.reset_index()
    required_columns = ["Open", "High", "Low", "Close"]

    for col in required_columns:
        if col not in data.columns:
            return pd.DataFrame()

    data = data.dropna(subset=required_columns)
    return data


def normalize_twelvedata_symbol(symbol: str) -> str:
    return TWELVEDATA_SYMBOL_MAP.get(symbol, symbol)


def get_twelvedata_history(symbol: str, interval: str = "15m", outputsize: int = 500) -> pd.DataFrame:
    api_key = os.environ.get("TWELVE_DATA_API_KEY", "").strip()
    if not api_key:
        return pd.DataFrame()

    normalized = normalize_twelvedata_symbol(symbol)
    params = {
        "symbol": normalized,
        "interval": interval,
        "outputsize": outputsize,
        "timezone": "UTC",
        "apikey": api_key,
    }

    try:
        response = requests.get(f"{TWELVE_DATA_BASE}/time_series", params=params, timeout=15)
        data = response.json()
        if "values" not in data:
            return pd.DataFrame()

        df = pd.DataFrame(data["values"])
        df = df.rename(columns={
            "datetime": "Datetime",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        })
        df["Datetime"] = pd.to_datetime(df["Datetime"])
        numeric_cols = ["Open", "High", "Low", "Close", "Volume"]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
        return df.sort_values("Datetime").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def get_finnhub_history(symbol: str, interval: str = "15m", count: int = 500) -> pd.DataFrame:
    """Fetch historical candles from Finnhub.io using REST API.

    Requires environment variable `FINNHUB_API_KEY`.
    Returns a DataFrame with columns: Datetime, Open, High, Low, Close, Volume
    """
    api_key = os.environ.get("FINNHUB_API_KEY", "").strip()
    if not api_key:
        return pd.DataFrame()

    # Finnhub uses resolution strings like 1,5,15,30,60,D,W,M
    interval_map = {
        "1m": "1",
        "5m": "5",
        "15m": "15",
        "30m": "30",
        "1h": "60",
        "1d": "D",
    }
    resolution = interval_map.get(interval, "15")

    try:
        import time
        to_ts = int(time.time())
        # request last `count` bars by estimating from resolution (approx)
        from_ts = to_ts - max(60 * int(resolution if resolution.isdigit() else 60) * count, 60 * 60)

        resp = requests.get(
            "https://finnhub.io/api/v1/stock/candle",
            params={
                "symbol": symbol,
                "resolution": resolution,
                "from": from_ts,
                "to": to_ts,
                "token": api_key,
            },
            timeout=15,
        )
        data = resp.json()
        if data.get("s") != "ok":
            return pd.DataFrame()

        df = pd.DataFrame({
            "Datetime": pd.to_datetime(data.get("t", []), unit="s"),
            "Open": data.get("o", []),
            "High": data.get("h", []),
            "Low": data.get("l", []),
            "Close": data.get("c", []),
            "Volume": data.get("v", []),
        })
        return df.sort_values("Datetime").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def get_alphavantage_history(symbol: str, interval: str = "15m", outputsize: str = "compact") -> pd.DataFrame:
    """Fetch intraday history from Alpha Vantage.

    Requires environment variable `ALPHAVANTAGE_API_KEY`.
    Returns a DataFrame with columns: Datetime, Open, High, Low, Close, Volume
    """
    api_key = os.environ.get("ALPHAVANTAGE_API_KEY", "").strip()
    if not api_key:
        return pd.DataFrame()

    interval_map = {
        "1m": "1min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "1h": "60min",
    }
    av_interval = interval_map.get(interval, "15min")

    try:
        params = {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": symbol,
            "interval": av_interval,
            "outputsize": outputsize,
            "datatype": "json",
            "apikey": api_key,
        }
        resp = requests.get("https://www.alphavantage.co/query", params=params, timeout=20)
        data = resp.json()
        key = f"Time Series ({av_interval})"
        if key not in data:
            return pd.DataFrame()

        series = data[key]
        rows = []
        for ts, values in series.items():
            rows.append({
                "Datetime": pd.to_datetime(ts),
                "Open": float(values.get("1. open", 0)),
                "High": float(values.get("2. high", 0)),
                "Low": float(values.get("3. low", 0)),
                "Close": float(values.get("4. close", 0)),
                "Volume": float(values.get("5. volume", 0)),
            })

        df = pd.DataFrame(rows)
        return df.sort_values("Datetime").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


# Optional crypto connector via CCXT
try:
    from .crypto import get_crypto_history
except Exception:
    get_crypto_history = None

# Optional MT5 connector
try:
    from .mt5_connector import get_mt5_history
except Exception:
    get_mt5_history = None


def get_yfinance_history(symbol: str, period: str = "5d", interval: str = "15m") -> pd.DataFrame:
    try:
        raw_data = yf.download(
            symbol,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=False
        )
        return clean_yfinance_data(raw_data)
    except Exception:
        return pd.DataFrame()


def get_market_data(symbol: str, period: str = "5d", interval: str = "15m", provider: str = "yfinance") -> pd.DataFrame:
    if provider == "twelvedata":
        interval_map = {
            "1m": "1min",
            "5m": "5min",
            "15m": "15min",
            "30m": "30min",
            "1h": "1h",
            "1d": "1day",
        }
        td_interval = interval_map.get(interval, interval)
        df = get_twelvedata_history(symbol, interval=td_interval, outputsize=500)
        if not df.empty:
            return df

    if provider == "finnhub":
        df = get_finnhub_history(symbol, interval=interval, count=500)
        if not df.empty:
            return df

    if provider == "alphavantage":
        df = get_alphavantage_history(symbol, interval=interval, outputsize="compact")
        if not df.empty:
            return df

    if provider == "ccxt":
        if get_crypto_history is not None:
            df = get_crypto_history(symbol, provider="ccxt", timeframe=interval)
            if not df.empty:
                return df

    if provider == "mt5":
        if get_mt5_history is not None:
            timeframe_map = {
                "1m": "M1",
                "5m": "M5",
                "15m": "M15",
                "30m": "M30",
                "1h": "H1",
                "1d": "D1",
            }
            mt5_timeframe = timeframe_map.get(interval, "M15")
            df = get_mt5_history(symbol, timeframe=mt5_timeframe, count=500)
            if not df.empty:
                return df

    return get_yfinance_history(symbol, period, interval)


def get_latest_snapshot(symbols: dict) -> pd.DataFrame:
    rows = []

    for market_name, details in symbols.items():
        symbol = details.get("symbol")
        market_type = details.get("type")

        try:
            ticker = yf.Ticker(symbol)
            fast_info = getattr(ticker, "fast_info", {}) or {}

            close = fast_info.get("last_price")
            open_price = fast_info.get("open")
            high = fast_info.get("day_high")
            low = fast_info.get("day_low")
            previous_close = fast_info.get("previous_close")

            if close is None or previous_close is None:
                data = ticker.history(period="2d", interval="1d", auto_adjust=False)
                data = clean_yfinance_data(data)
                if data.empty or len(data) < 1:
                    continue
                latest = data.iloc[-1]
                previous = data.iloc[-2] if len(data) > 1 else latest
                close = float(latest["Close"])
                open_price = float(latest["Open"])
                high = float(latest["High"])
                low = float(latest["Low"])
                previous_close = float(previous["Close"])
            else:
                close = float(close)
                open_price = float(open_price or close)
                high = float(high or close)
                low = float(low or close)
                previous_close = float(previous_close)

            change = close - previous_close
            change_pct = (change / previous_close) * 100 if previous_close != 0 else 0

            rows.append({
                "Market": market_name,
                "Symbol": symbol,
                "Type": market_type,
                "Price": close,
                "Open": open_price,
                "High": high,
                "Low": low,
                "Previous Close": previous_close,
                "Change": change,
                "% Change": change_pct
            })
        except Exception:
            continue

    return pd.DataFrame(rows)


def load_snapshot_from_file(path: str = None) -> pd.DataFrame:
    path = path or os.environ.get("TRENDIQ_SNAPSHOT_PATH", "trendiq_snapshot.json")
    try:
        if not os.path.exists(path):
            return pd.DataFrame()
        import json

        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        data = payload.get("data", [])
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        # ensure numeric columns
        for col in ["Price", "Open", "High", "Low", "Previous Close", "% Change"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()


def get_twelvedata_trend_summary(symbol: str, interval: str = "1h") -> dict:
    api_key = os.environ.get("TWELVE_DATA_API_KEY", "").strip()
    if not api_key:
        return {}

    normalized_symbol = normalize_twelvedata_symbol(symbol)
    params = {
        "symbol": normalized_symbol,
        "interval": interval,
        "apikey": api_key,
    }

    try:
        response = requests.get(f"{TWELVE_DATA_BASE}/technical_summary", params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "ok":
            return {}

        return data
    except Exception:
        return {}


def get_market_trend_summary(symbol: str, interval: str = "1h") -> dict:
    summary = get_twelvedata_trend_summary(symbol, interval=interval)
    if summary:
        return summary
    return {}


def get_market_info(market_name: str) -> dict:
    return MARKET_SYMBOLS.get(market_name, {})


def check_provider_health(provider: str, symbol: str = None, timeout: int = 8) -> dict:
    """Quick health check for a provider. Returns status and latency_ms.

    provider: one of 'yfinance', 'twelvedata', 'finnhub', 'alphavantage', 'ccxt', 'mt5'
    """
    import time

    start = time.time()
    status = False
    message = "Unknown"

    try:
        if provider == "yfinance":
            # quick price ping
            import yfinance as yf

            if symbol is None:
                symbol = "QQQ"
            t0 = time.time()
            ticker = yf.Ticker(symbol)
            _ = getattr(ticker, "fast_info", None)
            status = True
            message = "yfinance reachable"

        elif provider == "twelvedata":
            api_key = os.environ.get("TWELVE_DATA_API_KEY", "").strip()
            if not api_key:
                raise RuntimeError("TWELVE_DATA_API_KEY not set")
            resp = requests.get(f"{TWELVE_DATA_BASE}/time_series", params={"symbol": normalize_twelvedata_symbol(symbol or "EUR/USD"), "interval": "15min", "apikey": api_key}, timeout=timeout)
            resp.raise_for_status()
            status = True
            message = "TwelveData OK"

        elif provider == "finnhub":
            api_key = os.environ.get("FINNHUB_API_KEY", "").strip()
            if not api_key:
                raise RuntimeError("FINNHUB_API_KEY not set")
            resp = requests.get("https://finnhub.io/api/v1/quote", params={"symbol": symbol or "AAPL", "token": api_key}, timeout=timeout)
            resp.raise_for_status()
            status = True
            message = "Finnhub OK"

        elif provider == "alphavantage":
            api_key = os.environ.get("ALPHAVANTAGE_API_KEY", "").strip()
            if not api_key:
                raise RuntimeError("ALPHAVANTAGE_API_KEY not set")
            resp = requests.get("https://www.alphavantage.co/query", params={"function": "TIME_SERIES_INTRADAY", "symbol": symbol or "IBM", "interval": "15min", "apikey": api_key}, timeout=timeout)
            resp.raise_for_status()
            status = True
            message = "AlphaVantage OK"

        elif provider == "ccxt":
            try:
                import ccxt
                ex = getattr(ccxt, "binance")({"enableRateLimit": True})
                _ = getattr(ex, "load_markets", None)
                status = True
                message = "CCXT available"
            except Exception as e:
                raise

        elif provider == "mt5":
            # check MT5 local availability
            try:
                import MetaTrader5 as mt5
                ok = mt5.initialize()
                if ok:
                    mt5.shutdown()
                status = True
                message = "MT5 available"
            except Exception:
                raise

        else:
            message = "Unknown provider"
    except Exception as e:
        status = False
        message = str(e)

    latency_ms = int((time.time() - start) * 1000)
    return {"provider": provider, "ok": status, "latency_ms": latency_ms, "message": message}
