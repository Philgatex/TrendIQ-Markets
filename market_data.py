import pandas as pd
import yfinance as yf


MARKET_SYMBOLS = {
    "Nasdaq-100 / US100 Proxy": {
        "symbol": "QQQ",
        "type": "index",
        "description": "Nasdaq-100 ETF proxy"
    },
    "S&P 500 / US500 Proxy": {
        "symbol": "SPY",
        "type": "index",
        "description": "S&P 500 ETF proxy"
    },
    "Dow Jones / US30 Proxy": {
        "symbol": "DIA",
        "type": "index",
        "description": "Dow Jones Industrial Average ETF proxy"
    },
    "Russell 2000 Proxy": {
        "symbol": "IWM",
        "type": "index",
        "description": "Russell 2000 ETF proxy"
    },
    "FTSE 100": {
        "symbol": "^FTSE",
        "type": "index",
        "description": "UK FTSE 100 Index"
    },
    "Nikkei 225": {
        "symbol": "^N225",
        "type": "index",
        "description": "Japan Nikkei 225 Index"
    },
    "Hang Seng": {
        "symbol": "^HSI",
        "type": "index",
        "description": "Hong Kong Hang Seng Index"
    },
    "DAX Germany": {
        "symbol": "^GDAXI",
        "type": "index",
        "description": "Germany DAX Index"
    },
    "Gold": {
        "symbol": "GC=F",
        "type": "commodity",
        "description": "Gold futures proxy"
    },
    "Silver": {
        "symbol": "SI=F",
        "type": "commodity",
        "description": "Silver futures proxy"
    },
    "WTI Crude Oil": {
        "symbol": "CL=F",
        "type": "commodity",
        "description": "WTI crude oil futures"
    },
    "Brent Crude Oil": {
        "symbol": "BZ=F",
        "type": "commodity",
        "description": "Brent crude oil futures"
    },
    "Bitcoin": {
        "symbol": "BTC-USD",
        "type": "crypto",
        "description": "Bitcoin against USD"
    },
    "Ethereum": {
        "symbol": "ETH-USD",
        "type": "crypto",
        "description": "Ethereum against USD"
    },
    "EUR/USD": {
        "symbol": "EURUSD=X",
        "type": "forex",
        "description": "Euro against US Dollar"
    },
    "GBP/USD": {
        "symbol": "GBPUSD=X",
        "type": "forex",
        "description": "British Pound against US Dollar"
    },
    "USD/JPY": {
        "symbol": "JPY=X",
        "type": "forex",
        "description": "US Dollar against Japanese Yen"
    },
    "AUD/USD": {
        "symbol": "AUDUSD=X",
        "type": "forex",
        "description": "Australian Dollar against US Dollar"
    },
    "USD/CAD": {
        "symbol": "CAD=X",
        "type": "forex",
        "description": "US Dollar against Canadian Dollar"
    },
    "USD/CHF": {
        "symbol": "CHF=X",
        "type": "forex",
        "description": "US Dollar against Swiss Franc"
    },
    "US 10Y Yield": {
        "symbol": "^TNX",
        "type": "bond",
        "description": "US 10-year Treasury yield proxy"
    }
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


def get_market_data(symbol: str, period: str = "5d", interval: str = "15m") -> pd.DataFrame:
    try:
        raw_data = yf.download(
            symbol,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=False
        )
        data = clean_yfinance_data(raw_data)
        return data
    except Exception:
        return pd.DataFrame()


def get_latest_snapshot(symbols: dict) -> pd.DataFrame:
    rows = []

    for market_name, details in symbols.items():
        symbol = details.get("symbol")
        market_type = details.get("type")

        try:
            data = yf.download(
                symbol,
                period="2d",
                interval="1d",
                progress=False,
                auto_adjust=False
            )

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


def get_market_info(market_name: str) -> dict:
    return MARKET_SYMBOLS.get(market_name, {})
