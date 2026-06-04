"""MetaTrader 5 connector stubs.

These functions are placeholders. Direct MT5 integration requires a local
MetaTrader 5 terminal and the `MetaTrader5` Python package. Provide this
integration only when the runtime environment has MT5 installed.
"""
from typing import Optional
import pandas as pd


def connect_mt5(terminal_path: Optional[str] = None) -> bool:
    """Attempt to initialize MT5 connection.

    Returns True if connected, False otherwise. This is a safe stub that
    will return False when `MetaTrader5` is not available.
    """
    try:
        import MetaTrader5 as mt5
        if terminal_path:
            mt5.initialize(terminal_path)
        else:
            mt5.initialize()
        return True
    except Exception:
        return False


def get_mt5_history(symbol: str, timeframe: str = "M15", count: int = 500):
    """Fetch OHLCV history from MT5. Returns empty DataFrame when unavailable."""
    try:
        import MetaTrader5 as mt5

        # Map timeframe string to mt5 timeframe constants if needed; keep simple
        rates = mt5.copy_rates_from_pos(
            symbol, getattr(mt5, timeframe, mt5.TIMEFRAME_M15), 0, count
        )
        if rates is None:
            return pd.DataFrame()
        df = pd.DataFrame(rates)
        df['Datetime'] = pd.to_datetime(df['time'], unit='s')
        df = df[['Datetime', 'open', 'high', 'low', 'close', 'tick_volume']]
        df.columns = ['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']
        return df
    except Exception:
        return pd.DataFrame()


def place_mt5_order(symbol: str, side: str, volume: float, price: Optional[float] = None, dry_run: bool = True) -> dict:
    """Stub for placing an MT5 order. Returns a simulated response when MT5 isn't available.

    Note: Real MT5 order placement requires the MetaTrader5 package and a running MT5 terminal.
    """
    try:
        import MetaTrader5 as mt5
        # Reference mt5 to satisfy linters (real implementation would use mt5.order_send)
        _ = getattr(mt5, '__name__', None)
        if dry_run:
            return {"skipped": True, "reason": "dry_run enabled", "simulated": True}
        # Live execution path would be implemented here when MT5 is available.
        return {"skipped": True, "reason": "MT5 live execution not implemented in stub"}
    except Exception:
        return {"skipped": True, "reason": "MetaTrader5 not available", "simulated": True}
