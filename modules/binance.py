"""Binance exchange helpers using CCXT with safe dry-run defaults.

This module provides lightweight helpers to place orders via Binance (ccxt).
It is safe by default (dry_run=True) and will not execute live orders unless
API keys are provided via `BINANCE_API_KEY` and `BINANCE_API_SECRET` and
`dry_run` is set to False.
"""
import os
from typing import Optional, Dict, Any
import pandas as pd


def _get_ccxt_exchange() -> Optional[object]:
    try:
        import ccxt
    except Exception:
        return None

    api_key = os.environ.get("BINANCE_API_KEY")
    api_secret = os.environ.get("BINANCE_API_SECRET")

    exchange = getattr(ccxt, "binance")({
        "enableRateLimit": True,
    })

    if api_key and api_secret:
        exchange.apiKey = api_key
        exchange.secret = api_secret

    return exchange


def get_ticker(symbol: str) -> Dict[str, Any]:
    ex = _get_ccxt_exchange()
    if ex is None:
        return {"error": "ccxt not available"}

    try:
        # ccxt symbol format typically 'BTC/USDT'
        s = symbol.replace("-", "/") if "-" in symbol else symbol
        ticker = ex.fetch_ticker(s)
        return ticker
    except Exception as e:
        return {"error": str(e)}


def place_order(symbol: str, side: str, order_type: str, amount: float, price: Optional[float] = None, dry_run: bool = True) -> Dict[str, Any]:
    """Place a market or limit order on Binance via ccxt.

    - `side`: 'buy' or 'sell'
    - `order_type`: 'market' or 'limit'
    - `dry_run`: when True, do not execute live orders and return a simulated response.
    """
    ex = _get_ccxt_exchange()
    if ex is None:
        return {"skipped": True, "reason": "ccxt not installed"}

    api_key = os.environ.get("BINANCE_API_KEY")
    api_secret = os.environ.get("BINANCE_API_SECRET")

    if not api_key or not api_secret:
        return {"skipped": True, "reason": "API keys not configured"}

    # Safety: require explicit permission to execute live orders
    if dry_run:
        return {
            "skipped": True,
            "reason": "dry_run enabled",
            "simulated_order": {
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "amount": amount,
                "price": price
            }
        }

    try:
        s = symbol.replace("-", "/") if "-" in symbol else symbol
        if order_type == "market":
            resp = ex.create_market_order(s, side, amount)
        else:
            resp = ex.create_limit_order(s, side, amount, price)
        return resp
    except Exception as e:
        return {"error": str(e)}


def get_balance() -> Dict[str, Any]:
    ex = _get_ccxt_exchange()
    if ex is None:
        return {"error": "ccxt not available"}

    api_key = os.environ.get("BINANCE_API_KEY")
    api_secret = os.environ.get("BINANCE_API_SECRET")
    if not api_key or not api_secret:
        return {"error": "API keys not configured"}

    try:
        bal = ex.fetch_balance()
        return bal
    except Exception as e:
        return {"error": str(e)}
