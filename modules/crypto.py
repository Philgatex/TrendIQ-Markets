"""Crypto connectors using CCXT with graceful fallbacks."""
import pandas as pd


def get_ccxt_history(symbol: str, exchange_id: str = "binance", timeframe: str = "15m", limit: int = 500) -> pd.DataFrame:
    try:
        import ccxt
    except Exception:
        return pd.DataFrame()

    try:
        ex_cls = getattr(ccxt, exchange_id)
        ex = ex_cls({
            'enableRateLimit': True,
        })

        # Normalize symbol for common exchanges (Binance uses USDT pairs)
        s = symbol
        if symbol.endswith("-USD"):
            s = symbol.replace("-USD", "/USDT")
        elif "-" in symbol:
            s = symbol.replace("-", "/")

        ohlcv = ex.fetch_ohlcv(s, timeframe=timeframe, limit=limit)
        if not ohlcv:
            return pd.DataFrame()

        df = pd.DataFrame(ohlcv, columns=["timestamp", "Open", "High", "Low", "Close", "Volume"])
        df["Datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df[["Datetime", "Open", "High", "Low", "Close", "Volume"]]
        return df
    except Exception:
        return pd.DataFrame()


def get_crypto_history(symbol: str, provider: str = "ccxt", **kwargs) -> pd.DataFrame:
    """Try CCXT first, then fall back to other providers if needed."""
    if provider == "ccxt":
        df = get_ccxt_history(symbol, **kwargs)
        if not df.empty:
            return df
    # No further providers here; return empty to let market_data fall back
    return pd.DataFrame()
