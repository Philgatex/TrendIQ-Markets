# TrendIQ Markets

TrendIQ Markets is a real-time multi-market analysis, prediction scoring, and risk planning dashboard built with Python and Streamlit.
It combines TradingView-style charting with TrendSpider/Koyfin-style workflow tools and broker-style MT5 data support.

## Features

- Multi-market dashboard with indices, forex, commodities, crypto, and MT5-style broker coverage
- Technical indicators: EMA, RSI, MACD, ATR, Bollinger Bands
- Auto support and resistance detection
- Global market regime classification with risk-on / risk-off signals
- Prediction probability engine with bias, confidence, and playbook levels
- Broker price input and local MT5 connector support
- News feed and curated economic calendar
- Trade risk calculator and position sizing tools
- Prediction journal for recording thesis and signal notes
- Simple historical backtesting engine for MA crossover strategies
- Mobile-friendly alerts and signal banners
- Streamlit-ready deployment

## Disclaimer

This tool provides educational market analysis only. It is not financial advice and does not guarantee profits. Free market data may be delayed and may differ from broker CFD prices.

## How to Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Snapshot Poller and Multi-Process Safety

TrendIQ now supports a server-side snapshot poller that updates a shared SQLite store instead of relying on a JSON file. This makes the app safer when multiple Streamlit processes or sessions are reading the same snapshot data.

### Run a standalone poller

```bash
export TRENDIQ_SNAPSHOT_DB=trendiq_snapshot.db
export TRENDIQ_POLLER_INTERVAL=30
python poller_runner.py
```

### Run the poller from the Streamlit app process

Set this environment variable before launching the app:

```bash
export TRENDIQ_ENABLE_POLLER=true
export TRENDIQ_POLLER_INTERVAL=30
export TRENDIQ_SNAPSHOT_DB=trendiq_snapshot.db
streamlit run app.py
```

### Systemd service template

A sample systemd unit file is included at `deploy/trendiq-poller.service`.

Update `WorkingDirectory` and `ExecStart` if your repository is installed in a different location, then enable and start it with:

```bash
sudo cp deploy/trendiq-poller.service /etc/systemd/system/trendiq-poller.service
sudo systemctl daemon-reload
sudo systemctl enable --now trendiq-poller.service
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

### Staging and live order safety

TrendIQ supports a simple staging environment via the `APP_ENV` environment
variable. Set `APP_ENV=staging` or `APP_ENV=development` to enable non-production
behavior and clearer warnings.

For Binance live trading, use the following flags:

- `BINANCE_TESTNET=true` — route Binance calls to Binance spot testnet.
- `BINANCE_ALLOW_LIVE_ORDERS=true` — enable actual order placement when `dry_run=False`.
- `BINANCE_API_KEY` and `BINANCE_API_SECRET` — required for authenticated API access.

The live order scaffold in `modules/binance.py` is safe by default; unless
`BINANCE_ALLOW_LIVE_ORDERS` is explicitly enabled, order submissions will be
skipped with a clear warning.

Optional news and calendar support:

- `NEWSAPI_API_KEY` — optional key to fetch live market news from NewsAPI.
- `ECONOMIC_CALENDAR_API_KEY` — set this if you wire a live calendar feed in the future.
- `TRENDIQ_JOURNAL_PATH` — override the local prediction journal file path.

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

### Binance (authenticated orders - scaffold)

The repository now includes a safe, dry-run scaffold for Binance using `ccxt` at `modules/binance.py`.

- It requires `ccxt` (already in `requirements.txt`).
- Configure `BINANCE_API_KEY` and `BINANCE_API_SECRET` environment variables to enable authenticated calls.
- By default `place_order(..., dry_run=True)` will not execute live orders — set `dry_run=False` only when you're sure.

See `tests/binance_test.py` for a non-destructive smoke test.

## TradingView-style Charts and Live Trends

- The dashboard now supports a TradingView-style widget for supported symbols, embedded directly in the app.
- A TrendIQ technical chart is also available with candlesticks, EMA overlays, volume, and RSI panels.
- Twelve Data trend analysis is used to surface live market trend signals, including moving average bias and oscillator bias, when `TWELVE_DATA_API_KEY` is configured.
