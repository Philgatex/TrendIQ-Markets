# TrendIQ Markets

TrendIQ Markets is a real-time multi-market analysis, prediction scoring, and risk planning dashboard built with Python and Streamlit.

## Features

- Multi-market dashboard
- Nasdaq-100, S&P 500, Dow Jones, forex, gold, oil, crypto, and global indices
- Technical indicators: EMA, RSI, MACD, ATR, Bollinger Bands
- Global market regime classification
- Bullish, bearish, and sideways prediction scoring
- Support and resistance detection
- Risk management and position sizing
- Streamlit-ready deployment

## Disclaimer

This tool provides educational market analysis only. It is not financial advice and does not guarantee profits. Free market data may be delayed and may differ from broker CFD prices.

## How to Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud Deployment

Main file path:

```text
app.py
```

## Real-Time Free Market Data

This dashboard uses free market data via Yahoo Finance (`yfinance`) by default.

It also supports a free market data provider:
- `Twelve Data` — requires a free API key from https://twelvedata.com and is configured with the `TWELVE_DATA_API_KEY` environment variable.

The app maps common forex, indices, commodities, and crypto symbols to XM/MT5-style coverage where possible.

For direct broker-level access with XM or MetaTrader 5, a local MT5 installation or broker-specific API is required.

### MT5 / MetaTrader 5 (optional)

TrendIQ includes a simple MT5 connector stub at `modules/mt5_connector.py` to
help users who run a local MetaTrader 5 terminal. This is a placeholder; a
full MT5 integration requires:

- Installing the `MetaTrader5` Python package (not included in `requirements.txt`).
- A running MetaTrader 5 terminal on the same host, with access to your broker account.
- Passing the terminal path or credentials to `mt5.initialize()` as needed.

Usage notes:

- If `MetaTrader5` is not available, the connector functions return safely (False or empty DataFrame).
- See `modules/mt5_connector.py` for example usage and mapping of MT5 rate calls to DataFrame output.

If you want help wiring a full MT5 integration (including authenticated order execution), I can add detailed steps and automated tests — say the word.

## TradingView-style Charts and Live Trends

- The dashboard now supports a TradingView-style widget for supported symbols, embedded directly in the app.
- A TrendIQ technical chart is also available with candlesticks, EMA overlays, volume, and RSI panels.
- Twelve Data trend analysis is used to surface live market trend signals, including moving average bias and oscillator bias, when `TWELVE_DATA_API_KEY` is configured.
