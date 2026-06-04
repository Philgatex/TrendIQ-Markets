"""Binance exchange helpers using CCXT with safe dry-run defaults.

This module provides lightweight helpers to place orders via Binance (ccxt).
It is safe by default (dry_run=True) and will not execute live orders unless
API keys are provided via `BINANCE_API_KEY` and `BINANCE_API_SECRET` and
`dry_run` is set to False.
"""
import os
from typing import Optional, Dict, Any
import pandas as pd

from .config import BINANCE_ALLOW_LIVE_ORDERS, BINANCE_TESTNET


def _get_ccxt_exchange(testnet: Optional[bool] = None) -> Optional[object]:
    try:
        import ccxt
    except Exception:
        # Provide a lightweight simulated exchange object when ccxt is not installed
        from types import SimpleNamespace
        use_testnet = BINANCE_TESTNET if testnet is None else testnet
        urls = {}
        if use_testnet:
            urls = {
                "api": {
                    "public": "https://testnet.binance.vision/api",
                    "private": "https://testnet.binance.vision/api",
                }
            }
        else:
            urls = {"api": {"public": "https://api.binance.com/api", "private": "https://api.binance.com/api"}}

        return SimpleNamespace(urls=urls)

    api_key = os.environ.get("BINANCE_API_KEY")
    api_secret = os.environ.get("BINANCE_API_SECRET")

    use_testnet = BINANCE_TESTNET if testnet is None else testnet
    exchange_kwargs = {
        "enableRateLimit": True,
    }

    if use_testnet:
        exchange_kwargs["urls"] = {
            "api": {
                "public": "https://testnet.binance.vision/api",
                "private": "https://testnet.binance.vision/api",
            }
        }

    exchange = getattr(ccxt, "binance")(exchange_kwargs)

    if api_key and api_secret:
        exchange.apiKey = api_key
        exchange.secret = api_secret

    return exchange


def get_ticker(symbol: str, testnet: Optional[bool] = None) -> Dict[str, Any]:
    ex = _get_ccxt_exchange(testnet=testnet)
    if ex is None:
        return {"error": "ccxt not available"}

    try:
        # ccxt symbol format typically 'BTC/USDT'
        s = symbol.replace("-", "/") if "-" in symbol else symbol
        ticker = ex.fetch_ticker(s)
        return ticker
    except Exception as e:
        return {"error": str(e)}


def _validate_order_params(side: str, order_type: str, amount: float, price: Optional[float]) -> Optional[Dict[str, Any]]:
    if side.lower() not in {"buy", "sell"}:
        return {"error": "Invalid side; use buy or sell."}
    if order_type.lower() not in {"market", "limit"}:
        return {"error": "Invalid order_type; use market or limit."}
    if amount <= 0:
        return {"error": "Order amount must be greater than zero."}
    if order_type.lower() == "limit" and (price is None or price <= 0):
        return {"error": "Limit orders require a positive price."}
    return None


def can_execute_live_order(allow_live: Optional[bool] = None) -> bool:
    if allow_live is None:
        return BINANCE_ALLOW_LIVE_ORDERS
    return allow_live


def calculate_position_size(
    account_equity: float,
    risk_percentage: float,
    entry_price: float,
    stop_price: float,
) -> float:
    """Calculate a position size based on account equity, risk, and stop loss distance."""
    try:
        risk_amount = abs(account_equity) * abs(risk_percentage) / 100.0
        stop_distance = abs(entry_price - stop_price)
        if stop_distance <= 0:
            return 0.0
        size = risk_amount / stop_distance
        return float(round(size, 8))
    except Exception:
        return 0.0


def place_order(
    symbol: str,
    side: str,
    order_type: str,
    amount: float,
    price: Optional[float] = None,
    dry_run: bool = True,
    testnet: Optional[bool] = None,
    allow_live: Optional[bool] = None,
) -> Dict[str, Any]:
    """Place a market or limit order on Binance via ccxt.

    - `side`: 'buy' or 'sell'
    - `order_type`: 'market' or 'limit'
    - `dry_run`: when True, do not execute live orders and return a simulated response.
    - `testnet`: when True, route calls to Binance spot testnet.
    """
    validation = _validate_order_params(side, order_type, amount, price)
    if validation is not None:
        return validation

    api_key = os.environ.get("BINANCE_API_KEY")
    api_secret = os.environ.get("BINANCE_API_SECRET")

    if dry_run:
        return {
            "skipped": True,
            "reason": "dry_run enabled",
            "simulated_order": simulate_order_response(symbol, side, order_type, amount, price),
            "testnet": BINANCE_TESTNET if testnet is None else testnet,
        }

    if not can_execute_live_order(allow_live=allow_live):
        return {
            "skipped": True,
            "reason": "Live Binance orders disabled. Set BINANCE_ALLOW_LIVE_ORDERS=true to enable.",
        }

    ex = _get_ccxt_exchange(testnet=testnet)
    if ex is None:
        return {"skipped": True, "reason": "ccxt not installed"}

    if not api_key or not api_secret:
        return {"skipped": True, "reason": "API keys not configured"}

    try:
        s = symbol.replace("-", "/") if "-" in symbol else symbol
        if order_type.lower() == "market":
            resp = ex.create_market_order(s, side.lower(), amount)
        else:
            resp = ex.create_limit_order(s, side.lower(), amount, price)
        return resp
    except Exception as e:
        return {"error": str(e)}


def place_order_with_risk(
    symbol: str,
    side: str,
    account_equity: float,
    risk_percentage: float,
    entry_price: float,
    stop_price: float,
    order_type: str = "market",
    price: Optional[float] = None,
    dry_run: bool = True,
    testnet: Optional[bool] = None,
    allow_live: Optional[bool] = None,
) -> Dict[str, Any]:
    """Place a risk-based Binance order using a calculated position size."""
    amount = calculate_position_size(account_equity, risk_percentage, entry_price, stop_price)
    if amount <= 0:
        return {"error": "Position size calculation failed or stop distance is invalid."}

    if order_type.lower() == "limit" and price is None:
        price = entry_price

    return place_order(
        symbol=symbol,
        side=side,
        order_type=order_type,
        amount=amount,
        price=price,
        dry_run=dry_run,
        testnet=testnet,
        allow_live=allow_live,
    )


def simulate_order_response(symbol: str, side: str, order_type: str, amount: float, price: Optional[float] = None) -> Dict[str, Any]:
    """Return a simulated order response resembling ccxt create_order output.

    This is used when `dry_run=True` so tests and demos can inspect expected
    fields without executing live orders.
    """
    import time

    ts = int(time.time() * 1000)
    client_order_id = f"sim-{ts}"
    response = {
        "info": {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "amount": amount,
            "price": price,
        },
        "id": client_order_id,
        "clientOrderId": client_order_id,
        "timestamp": ts,
        "datetime": pd.to_datetime(ts, unit='ms').isoformat(),
        "status": "open" if order_type == "limit" else "closed",
        "symbol": symbol,
        "type": order_type,
        "side": side,
        "price": price,
        "amount": amount,
        "filled": 0.0,
        "remaining": amount,
    }
    return response


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
