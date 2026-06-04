import json
import os
import sys
from datetime import datetime

# Ensure repo root is on path (helps Streamlit Cloud imports)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from streamlit.components.v1 import html as st_html
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from modules.config import APP_ENV, IS_STAGING, IS_DEVELOPMENT

from modules.market_data import (
    DATA_PROVIDERS,
    MARKET_SYMBOLS,
    get_market_data,
    get_latest_snapshot,
    get_market_info,
    get_market_trend_summary
)
from modules.config_store import load_keys, save_key, get_key, save_provider_for_market, get_provider_for_market
from modules.poller import start_global_poller
from modules.snapshot_store import load_latest_snapshot

from modules.indicators import (
    add_indicators,
    get_indicator_summary,
    detect_support_resistance
)

from modules.sentiment_engine import build_market_regime
from modules.prediction_engine import generate_prediction
from modules.risk_engine import generate_trade_plan
from modules.news_engine import fetch_market_news, get_economic_calendar
from modules.journal import append_journal_entry, load_journal_entries
from modules.prediction_log import (
    append_prediction_entry as append_prediction_log_entry,
    load_prediction_entries as load_prediction_entries_log,
    evaluate_pending_predictions,
)
from modules.backtest import backtest_moving_average_crossover


st.set_page_config(
    page_title="TrendIQ Markets",
    page_icon="📈",
    layout="wide"
)

st.markdown(
    """
    <style>
    .css-1d391kg {padding-top: 1rem;}
    .stApp {
        background-color: #0b1120;
        color: #f8fafc;
    }
    .stSidebar {
        background-color: #081026;
    }
    .st-bf {
        background-color: #0f172a;
    }
    .streamlit-expanderHeader {
        color: #f8fafc;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Start the background snapshot poller when enabled for this process.
# This is safe because `start_global_poller` is idempotent.
if os.environ.get("TRENDIQ_ENABLE_POLLER", "false").strip().lower() in {"1", "true", "yes", "on"}:
    poll_interval = int(os.environ.get("TRENDIQ_POLLER_INTERVAL", "30"))
    start_global_poller(interval=poll_interval, symbols=MARKET_SYMBOLS)


@st.cache_data(ttl=60)
def cached_market_data(symbol: str, period: str, interval: str, provider: str):
    return get_market_data(symbol, period, interval, provider)


@st.cache_data(ttl=120)
def cached_snapshot():
    # Prefer a polled snapshot store when available to avoid blocking calls.
    snapshot_db = os.environ.get("TRENDIQ_SNAPSHOT_DB", "trendiq_snapshot.db")
    df = load_latest_snapshot(snapshot_db)
    if df is not None and not df.empty:
        return df

    return get_latest_snapshot(MARKET_SYMBOLS)


def format_number(value, decimals=2):
    try:
        return f"{float(value):,.{decimals}f}"
    except Exception:
        return "N/A"


def format_percentage(value, decimals=2):
    try:
        return f"{float(value):.{decimals}f}%"
    except Exception:
        return "N/A"


def sanitize_for_streamlit(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure DataFrame dtypes are safe for Streamlit/pyarrow rendering.

    - Convert numeric-like columns to numeric (coerce errors).
    - Parse datelike strings.
    - Convert nested objects and mixed types to strings.
    """
    if df is None or df.empty:
        return df

    df = df.copy()
    df.columns = df.columns.map(str)

    for col in df.columns:
        try:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                continue

            if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
                if df[col].apply(lambda x: isinstance(x, (dict, list, tuple))).any():
                    # Convert nested objects to JSON strings but keep plain object dtype
                    df[col] = df[col].apply(lambda x: json.dumps(x, default=str)).astype(object)
                    continue
                parsed = pd.to_datetime(df[col], errors="coerce")
                if parsed.notna().any():
                    df[col] = parsed
                    continue

            df[col] = pd.to_numeric(df[col], errors="coerce")
            if pd.api.types.is_numeric_dtype(df[col]):
                continue
            if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
                df[col] = df[col].astype(str)
        except Exception:
            df[col] = df[col].astype(str)

    return df


def create_candlestick_chart(df: pd.DataFrame, market_name: str):
    fig = go.Figure()
    time_col = df.columns[0]

    fig.add_trace(
        go.Candlestick(
            x=df[time_col],
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price",
            increasing_line_color="#00b894",
            decreasing_line_color="#d63031"
        )
    )

    if "EMA20" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df[time_col],
                y=df["EMA20"],
                mode="lines",
                name="EMA 20",
                line=dict(color="#74b9ff", width=1)
            )
        )

    if "EMA50" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df[time_col],
                y=df["EMA50"],
                mode="lines",
                name="EMA 50",
                line=dict(color="#fdcb6e", width=1)
            )
        )

    if "EMA200" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df[time_col],
                y=df["EMA200"],
                mode="lines",
                name="EMA 200",
                line=dict(color="#6c5ce7", width=1)
            )
        )

    fig.update_layout(
        template="plotly_dark",
        title=f"{market_name} Price Chart",
        height=650,
        xaxis_rangeslider_visible=False,
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", y=1.02, x=0)
    )

    return fig


def create_technical_plot(df: pd.DataFrame, market_name: str):
    time_col = df.columns[0]
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.55, 0.2, 0.25]
    )

    fig.add_trace(
        go.Candlestick(
            x=df[time_col],
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price",
            increasing_line_color="#00b894",
            decreasing_line_color="#d63031"
        ),
        row=1,
        col=1
    )

    for name, color in [("EMA20", "#74b9ff"), ("EMA50", "#fdcb6e"), ("EMA200", "#6c5ce7")]:
        if name in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df[time_col],
                    y=df[name],
                    mode="lines",
                    name=name,
                    line=dict(color=color, width=1)
                ),
                row=1,
                col=1
            )

    if "Volume" in df.columns:
        fig.add_trace(
            go.Bar(
                x=df[time_col],
                y=df["Volume"],
                name="Volume",
                marker_color="#0984e3"
            ),
            row=2,
            col=1
        )

    if "RSI" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df[time_col],
                y=df["RSI"],
                mode="lines",
                name="RSI 14",
                line=dict(color="#fd79a8", width=1)
            ),
            row=3,
            col=1
        )
        fig.add_hline(y=70, line_dash="dash", line_color="#d63031", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#00b894", row=3, col=1)

    fig.update_layout(
        template="plotly_dark",
        title=f"{market_name} Technical Chart",
        height=900,
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", y=1.02, x=0)
    )

    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    return fig


def get_tradingview_symbol(symbol: str) -> str:
    if symbol == "EURUSD=X":
        return "OANDA:EURUSD"
    if symbol == "GBPUSD=X":
        return "OANDA:GBPUSD"
    if symbol == "JPY=X":
        return "OANDA:USDJPY"
    if symbol == "AUDUSD=X":
        return "OANDA:AUDUSD"
    if symbol == "CAD=X":
        return "OANDA:USDCAD"
    if symbol == "CHF=X":
        return "OANDA:USDCHF"
    if symbol == "EURJPY=X":
        return "OANDA:EURJPY"
    if symbol == "GBPJPY=X":
        return "OANDA:GBPJPY"
    if symbol == "AUDJPY=X":
        return "OANDA:AUDJPY"
    if symbol == "EURGBP=X":
        return "OANDA:EURGBP"
    if symbol == "BTC-USD":
        return "COINBASE:BTCUSD"
    if symbol == "ETH-USD":
        return "COINBASE:ETHUSD"
    if symbol in ["QQQ", "SPY", "DIA", "IWM"]:
        return f"NASDAQ:{symbol}"
    return ""


def render_tradingview_widget(symbol: str, interval: str = "15m") -> bool:
    tradingview_symbol = get_tradingview_symbol(symbol)
    if not tradingview_symbol:
        return False

    interval_map = {
        "1m": "1",
        "5m": "5",
        "15m": "15",
        "30m": "30",
        "1h": "60",
        "1d": "D",
    }
    tv_interval = interval_map.get(interval, "15")
    st_html(
        f"""
        <div class="tradingview-widget-container">
          <div id="tradingview_{symbol.replace('/', '').replace('=', '')}"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
          new TradingView.widget({{
            "width": "100%",
            "height": 650,
            "symbol": "{tradingview_symbol}",
            "interval": "{tv_interval}",
            "timezone": "Etc/UTC",
            "theme": "dark",
            "style": "1",
            "locale": "en",
            "toolbar_bg": "#0f172a",
            "enable_publishing": false,
            "allow_symbol_change": true,
            "container_id": "tradingview_{symbol.replace('/', '').replace('=', '')}"
          }});
          </script>
        </div>
        """,
        height=700,
    )
    return True


def create_alert_banner(prediction: dict, regime: dict, support_resistance: dict) -> str:
    bias = prediction.get("final_bias", "N/A")
    confidence = prediction.get("confidence_score", 0)
    regime_label = regime.get("market_regime", "N/A")
    support = support_resistance.get("support")
    resistance = support_resistance.get("resistance")

    alerts = []
    if regime_label == "Risk-Off":
        alerts.append("Global regime is risk-off. Defensive positioning and tighter risk control are advised.")
    elif regime_label == "Risk-On":
        alerts.append("Global regime is risk-on. Trends may favor growth and cyclical assets.")
    else:
        alerts.append("Market regime is mixed. Proceed with caution and wait for cleaner setups.")

    if bias == "Bullish":
        alerts.append(f"Bias is bullish with {confidence}% confidence. Look for long entries above support levels.")
    elif bias == "Bearish":
        alerts.append(f"Bias is bearish with {confidence}% confidence. Look for short entries near resistance.")
    else:
        alerts.append("Bias is sideways/cautious. Avoid directional overcommitment.")

    if support and resistance:
        alerts.append(f"Support: {format_number(support)} / Resistance: {format_number(resistance)}")

    return "\n".join(alerts)


def create_equity_curve_chart(df: pd.DataFrame):
    fig = go.Figure()
    if "Datetime" in df.columns:
        x_values = df["Datetime"]
    else:
        x_values = df.index

    fig.add_trace(
        go.Scatter(
            x=x_values,
            y=df["Equity"],
            mode="lines",
            name="Equity Curve",
            line=dict(color="#00b894", width=2),
        )
    )

    fig.update_layout(
        template="plotly_dark",
        title="Backtest Equity Curve",
        margin=dict(l=20, r=20, t=40, b=20),
        height=450,
    )

    return fig


st.title("TrendIQ Markets")
st.caption("Real-time multi-market analysis, prediction scoring, broker-style data, and studio-grade journal/backtest features.")

st.warning(
    "This tool provides educational market analysis only. "
    "It is not financial advice and does not guarantee profits. "
    "Free market data may be delayed and may differ from broker CFD prices."
)

if not APP_ENV or APP_ENV != "production":
    st.info(f"Running in {APP_ENV or 'development'} mode. Set APP_ENV=production for live production behavior.")

st.sidebar.header("Dashboard Settings")

# API keys management
with st.sidebar.expander("API Keys (local)"):
    keys = load_keys()
    finnhub_key = st.text_input("Finnhub API Key", value=keys.get("FINNHUB_API_KEY", ""), type="password")
    alphav_key = st.text_input("Alpha Vantage API Key", value=keys.get("ALPHAVANTAGE_API_KEY", ""), type="password")
    if st.button("Save API Keys"):
        if finnhub_key:
            save_key("FINNHUB_API_KEY", finnhub_key)
            os.environ["FINNHUB_API_KEY"] = finnhub_key
        if alphav_key:
            save_key("ALPHAVANTAGE_API_KEY", alphav_key)
            os.environ["ALPHAVANTAGE_API_KEY"] = alphav_key
        st.success("API keys saved locally to trendiq_config.json")


market_names = list(MARKET_SYMBOLS.keys())

selected_market = st.sidebar.selectbox(
    "Select Market",
    market_names,
    index=0
)

# default provider per-market binding
provider_options = list(DATA_PROVIDERS.keys())
bound_provider = get_provider_for_market(selected_market)
default_index = 0
if bound_provider and bound_provider in provider_options:
    default_index = provider_options.index(bound_provider)

provider_label = st.sidebar.selectbox(
    "Data Provider",
    provider_options,
    index=default_index,
    help="Select a live market data provider. Twelve Data requires a free API key set in TWELVE_DATA_API_KEY."
)


if provider_label == "Twelve Data (free API)" and not os.environ.get("TWELVE_DATA_API_KEY"):
    st.sidebar.warning(
        "Twelve Data is selected but TWELVE_DATA_API_KEY is not configured. "
        "The app will fall back to Yahoo Finance until a free Twelve Data key is provided."
    )

if provider_label == "MetaTrader 5 (local connector)":
    st.sidebar.info(
        "MetaTrader 5 provider uses a local MT5 terminal if available. "
        "Install the MetaTrader5 package and configure your terminal path via MT5_TERMINAL_PATH if needed."
    )

chart_mode = st.sidebar.selectbox(
    "Chart Mode",
    ["TrendIQ chart", "TradingView widget"],
    index=0,
    help="Use a built-in TrendIQ chart or the TradingView-style embedded widget."
)

period = st.sidebar.selectbox(
    "Data Period",
    ["1d", "5d", "1mo", "3mo", "6mo", "1y"],
    index=1
)

interval = st.sidebar.selectbox(
    "Candle Interval",
    ["1m", "5m", "15m", "30m", "1h", "1d"],
    index=2
)

st.sidebar.divider()

st.sidebar.header("Risk Settings")

account_equity = st.sidebar.number_input(
    "Account Equity",
    min_value=1.0,
    value=100.0,
    step=10.0
)

risk_percentage = st.sidebar.number_input(
    "Risk % Per Trade",
    min_value=0.1,
    max_value=20.0,
    value=2.0,
    step=0.1
)

value_per_point = st.sidebar.number_input(
    "Value Per Point",
    min_value=0.01,
    value=1.0,
    step=0.01,
    help="Confirm this from your broker contract specification."
)

manual_refresh = st.sidebar.button("Refresh Data")

# Auto-refresh settings
auto_refresh = st.sidebar.checkbox("Enable Auto-Refresh (page reload)", value=False)
refresh_interval = st.sidebar.slider("Refresh interval (seconds)", min_value=5, max_value=300, value=30, step=5)

auto_log_predictions = st.sidebar.checkbox(
    "Auto-log each prediction to the prediction history",
    value=True,
    help="Save a structured prediction record for later accuracy tracking.",
)

if auto_refresh:
    # Prefer streamlit_autorefresh when available (partial rerun); fallback to JS page reload
    try:
        from streamlit_autorefresh import st_autorefresh

        # st_autorefresh returns an int counter that increments each interval
        st_autorefresh(interval=refresh_interval * 1000, limit=None, key="trendiq_autorefresh")
    except Exception:
        st_html(
            f"""
            <script>
            const _ri = {refresh_interval} * 1000;
            setTimeout(()=>{{ window.location.reload(); }}, _ri);
            </script>
            """,
            height=1,
        )

if manual_refresh:
    st.cache_data.clear()


market_info = get_market_info(selected_market)
symbol = market_info.get("symbol")
market_type = market_info.get("type", "index")

# Provider binding and health (placed after symbol is available)
with st.sidebar.expander("Provider per market"):
    current_binding = get_provider_for_market(selected_market) or "(not set)"
    st.write(f"Current provider for {selected_market}: {current_binding}")
    if st.button("Bind selected provider to this market"):
        ok = save_provider_for_market(selected_market, provider_label)
        if ok:
            st.success(f"Bound {provider_label} to {selected_market}")
        else:
            st.error("Failed to bind provider")

with st.sidebar.expander("Provider Health"):
    from modules.market_data import check_provider_health

    prov_key = DATA_PROVIDERS.get(provider_label)
    health = check_provider_health(prov_key, symbol)
    status_text = "OK" if health.get("ok") else "UNAVAILABLE"
    st.write(f"Provider: {provider_label} — {status_text}")
    st.write(f"Latency: {health.get('latency_ms', 'N/A')} ms")
    st.write(f"Message: {health.get('message')}")

with st.sidebar.expander("All Providers Health"):
    from modules.market_data import check_provider_health

    rows = []
    for label, key in DATA_PROVIDERS.items():
        try:
            h = check_provider_health(key, symbol)
            rows.append({"Provider": label, "OK": h.get("ok"), "Latency(ms)": h.get("latency_ms"), "Message": h.get("message")})
        except Exception as e:
            rows.append({"Provider": label, "OK": False, "Latency(ms)": None, "Message": str(e)})

    if rows:
        import pandas as _pd

        st.dataframe(_pd.DataFrame(rows))
    else:
        st.write("No provider health data available.")


with st.spinner("Loading market data..."):
    data = cached_market_data(symbol, period, interval, DATA_PROVIDERS.get(provider_label, "yfinance"))
    snapshot_df = cached_snapshot()

trend_summary = get_market_trend_summary(symbol, interval="1h")

if data.empty:
    st.error("No data available. Try another market, period, or interval.")
    st.stop()

data = add_indicators(data)

if data.empty:
    st.error("Indicator calculation failed due to insufficient data.")
    st.stop()

regime = build_market_regime(snapshot_df)
indicator_summary = get_indicator_summary(data)
prediction = generate_prediction(data, regime, market_type)
levels = prediction.get("levels", {})

latest = data.iloc[-1]
latest_close = float(latest["Close"])
previous_close = float(data["Close"].iloc[-2]) if len(data) > 1 else latest_close

change = latest_close - previous_close
sr = detect_support_resistance(data)
change_pct = (change / previous_close) * 100 if previous_close != 0 else 0

prediction_log_key = (
    f"{selected_market}|{provider_label}|{period}|{interval}|"
    f"{prediction.get('final_bias')}|{prediction.get('confidence_score')}"
)
if st.session_state.get("prediction_log_key") != prediction_log_key:
    st.session_state["prediction_log_key"] = prediction_log_key
    st.session_state["prediction_log_saved"] = False

if auto_log_predictions and not st.session_state.get("prediction_log_saved", False):
    append_prediction_log_entry(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "market": selected_market,
            "symbol": symbol,
            "market_type": market_type,
            "provider": provider_label,
            "period": period,
            "interval": interval,
            "final_bias": prediction.get("final_bias", "N/A"),
            "confidence_score": prediction.get("confidence_score", 0),
            "bullish_probability": prediction.get("bullish_probability", 0),
            "bearish_probability": prediction.get("bearish_probability", 0),
            "sideways_probability": prediction.get("sideways_probability", 0),
            "current_price": latest_close,
            "support": levels.get("support"),
            "resistance": levels.get("resistance"),
            "buy_confirmation": levels.get("buy_confirmation"),
            "sell_confirmation": levels.get("sell_confirmation"),
            "bullish_invalidation": levels.get("bullish_invalidation"),
            "bearish_invalidation": levels.get("bearish_invalidation"),
            "tp1_bullish": levels.get("tp1_bullish"),
            "tp2_bullish": levels.get("tp2_bullish"),
            "tp1_bearish": levels.get("tp1_bearish"),
            "tp2_bearish": levels.get("tp2_bearish"),
            "market_regime": regime.get("market_regime"),
            "note": "Auto-logged TrendIQ prediction.",
        }
    )
    st.session_state["prediction_log_saved"] = True


st.subheader("Selected Market Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Market", selected_market)
col2.metric("Current Price", format_number(latest_close))
col3.metric("Change", format_number(change), format_percentage(change_pct))
col4.metric("Bias", prediction.get("final_bias", "N/A"))

st.caption(
    f"Symbol used: **{symbol}** | Market type: **{market_type}** | "
    f"Data provider: **{provider_label}**"
)


tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "Global Market Regime",
    "Market Chart",
    "Prediction",
    "Risk Manager",
    "Technical Summary",
    "News & Calendar",
    "Journal / Alerts",
    "Backtesting",
    "Accuracy Tracker"
])


with tab1:
    st.header("Global Market Regime")

    m1, m2, m3 = st.columns(3)

    m1.metric("Market Regime", regime.get("market_regime", "N/A"))
    m2.metric("Risk-On Probability", f"{regime.get('risk_on_probability', 0)}%")
    m3.metric("Risk-Off Probability", f"{regime.get('risk_off_probability', 0)}%")

    st.info(regime.get("summary", "No regime summary available."))

    regime_table = regime.get("table", pd.DataFrame())

    if regime_table is not None and not regime_table.empty:
        safe_regime = sanitize_for_streamlit(regime_table)
        for numeric_col in ["Price", "% Change"]:
            if numeric_col in safe_regime.columns:
                safe_regime[numeric_col] = pd.to_numeric(safe_regime[numeric_col], errors="coerce")
        st.dataframe(
            safe_regime.style.format({
                "Price": "{:,.2f}",
                "% Change": "{:.2f}%"
            }),
            width='stretch'
        )
    else:
        st.warning("No global market snapshot available.")


with tab2:
    st.header("Market Chart")

    if chart_mode == "TradingView widget":
        rendered = render_tradingview_widget(symbol, interval)
        if not rendered:
            st.warning("TradingView widget is not available for this symbol. Showing TrendIQ chart instead.")
            fig = create_technical_plot(data, selected_market)
            st.plotly_chart(fig, width='stretch')
    else:
        fig = create_technical_plot(data, selected_market)
        st.plotly_chart(fig, width='stretch')

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Support", format_number(sr.get("support")))
    c2.metric("Resistance", format_number(sr.get("resistance")))
    c3.metric("Recent Low", format_number(sr.get("recent_low")))
    c4.metric("Recent High", format_number(sr.get("recent_high")))


with tab3:
    st.header("Prediction Engine")

    p1, p2, p3, p4 = st.columns(4)

    p1.metric("Final Bias", prediction.get("final_bias", "N/A"))
    p2.metric("Bullish", f"{prediction.get('bullish_probability', 0)}%")
    p3.metric("Bearish", f"{prediction.get('bearish_probability', 0)}%")
    p4.metric("Sideways", f"{prediction.get('sideways_probability', 0)}%")

    st.metric("Confidence Score", f"{prediction.get('confidence_score', 0)}%")

    st.subheader("Trade Scenario Levels")

    level_df = pd.DataFrame([
        {"Level": "Current Price", "Value": levels.get("current_price")},
        {"Level": "Support", "Value": levels.get("support")},
        {"Level": "Resistance", "Value": levels.get("resistance")},
        {"Level": "Buy Confirmation", "Value": levels.get("buy_confirmation")},
        {"Level": "Sell Confirmation", "Value": levels.get("sell_confirmation")},
        {"Level": "Bullish Invalidation", "Value": levels.get("bullish_invalidation")},
        {"Level": "Bearish Invalidation", "Value": levels.get("bearish_invalidation")},
        {"Level": "Bullish TP1", "Value": levels.get("tp1_bullish")},
        {"Level": "Bullish TP2", "Value": levels.get("tp2_bullish")},
        {"Level": "Bearish TP1", "Value": levels.get("tp1_bearish")},
        {"Level": "Bearish TP2", "Value": levels.get("tp2_bearish")},
    ])

    st.dataframe(sanitize_for_streamlit(level_df), width='stretch')

    st.subheader("Prediction Explanation")

    signal_label = prediction.get("final_bias", "N/A")
    if trend_summary:
        signal_label = trend_summary.get("summary", {}).get("signal", signal_label)

    st.markdown(f"**Suggested Action:** {signal_label}")

    if trend_summary:
        st.write("**Market trend analysis:**")
        st.write(f"- Overall summary: {trend_summary.get('summary', {}).get('signal', 'N/A')}")
        st.write(f"- Strength: {trend_summary.get('summary', {}).get('strength', 'N/A')}")

        moving_averages = trend_summary.get("moving_averages", {})
        oscillators = trend_summary.get("oscillators", {})

        if moving_averages:
            st.write("- Moving average bias:")
            for item, value in moving_averages.items():
                st.write(f"  - {item}: {value}")

        if oscillators:
            st.write("- Momentum oscillator bias:")
            for item, value in oscillators.items():
                st.write(f"  - {item}: {value}")

    for item in prediction.get("explanations", []):
        st.write(f"- {item}")


with tab4:
    st.header("Risk Manager")

    st.write(
        "Use this section to estimate safer risk. "
        "For CFDs, confirm value per point and contract size with your broker."
    )

    direction = st.selectbox("Trade Direction", ["Buy", "Sell"])

    default_entry = float(levels.get("current_price", latest_close))

    if direction == "Buy":
        default_sl = float(levels.get("bullish_invalidation", latest_close - indicator_summary.get("atr", 1)))
    else:
        default_sl = float(levels.get("bearish_invalidation", latest_close + indicator_summary.get("atr", 1)))

    entry_price = st.number_input(
        "Entry Price",
        value=default_entry,
        step=0.01
    )

    stop_loss_price = st.number_input(
        "Stop Loss Price",
        value=default_sl,
        step=0.01
    )

    trade_plan = generate_trade_plan(
        direction=direction,
        entry_price=entry_price,
        stop_loss_price=stop_loss_price,
        account_equity=account_equity,
        risk_percentage=risk_percentage,
        value_per_point=value_per_point
    )

    r1, r2, r3 = st.columns(3)

    r1.metric("Risk Amount", f"{trade_plan.get('risk_amount', 0)}")
    r2.metric("Stop Distance", f"{trade_plan.get('stop_distance', 0)}")
    r3.metric("Suggested Position Size", f"{trade_plan.get('suggested_position_size', 0)}")

    st.subheader("Risk/Reward Targets")

    rr_df = pd.DataFrame([
        {"Target": "Entry", "Price": trade_plan.get("entry_price")},
        {"Target": "Stop Loss", "Price": trade_plan.get("stop_loss_price")},
        {"Target": "TP1", "Price": trade_plan.get("tp1"), "Risk/Reward": "1:1"},
        {"Target": "TP2", "Price": trade_plan.get("tp2"), "Risk/Reward": "1:2"},
        {"Target": "TP3", "Price": trade_plan.get("tp3"), "Risk/Reward": "1:3"},
    ])

    st.dataframe(sanitize_for_streamlit(rr_df), width='stretch')

    st.warning(trade_plan.get("warning", ""))


with tab5:
    st.header("Technical Summary")

    t1, t2, t3, t4 = st.columns(4)

    t1.metric("Trend", indicator_summary.get("trend", "N/A"))
    t2.metric("RSI 14", format_number(indicator_summary.get("rsi")))
    t3.metric("MACD", indicator_summary.get("macd_status", "N/A"))
    t4.metric("Volatility", indicator_summary.get("volatility_status", "N/A"))

    summary_df = pd.DataFrame([
        {"Indicator": "EMA 20", "Value": indicator_summary.get("ema20")},
        {"Indicator": "EMA 50", "Value": indicator_summary.get("ema50")},
        {"Indicator": "EMA 200", "Value": indicator_summary.get("ema200")},
        {"Indicator": "RSI 14", "Value": indicator_summary.get("rsi")},
        {"Indicator": "ATR 14", "Value": indicator_summary.get("atr")},
        {"Indicator": "Trend", "Value": indicator_summary.get("trend")},
        {"Indicator": "RSI Status", "Value": indicator_summary.get("rsi_status")},
        {"Indicator": "MACD Status", "Value": indicator_summary.get("macd_status")},
        {"Indicator": "Volatility Status", "Value": indicator_summary.get("volatility_status")},
    ])

    st.dataframe(sanitize_for_streamlit(summary_df), width='stretch')

with tab6:
    st.header("News & Economic Calendar")
    news_items = fetch_market_news(query=selected_market, page_size=4)
    if news_items:
        for item in news_items:
            title = item.get("title", "Untitled")
            source = item.get("source", "Unknown")
            url = item.get("url", "")
            published = item.get("published_at", "")
            if url:
                st.markdown(f"- **{title}**  \n  Source: {source} | Published: {published}  \n  [Read more]({url})")
            else:
                st.markdown(f"- **{title}**  \n  Source: {source} | Published: {published}")
    else:
        st.warning("No news items are available at this time.")

    st.subheader("Economic Calendar")
    calendar = get_economic_calendar(days=7)
    if calendar:
        cal_df = pd.DataFrame(calendar)
        st.dataframe(sanitize_for_streamlit(cal_df), width='stretch')
    else:
        st.warning("Economic calendar is unavailable. Configure an API key for live events.")

with tab7:
    st.header("Prediction Journal & Alerts")
    st.write(
        "Capture your trade thesis, journal entries, or signal commentary here. "
        "This section is mobile-friendly and works well on smaller screens."
    )

    alert_text = create_alert_banner(prediction, regime, sr)
    st.info(alert_text)

    journal_note = st.text_area(
        "Journal Note",
        value=f"{selected_market}: {prediction.get('final_bias', 'N/A')} ({prediction.get('confidence_score', 0)}%)\n",
        height=120,
    )

    if st.button("Save Journal Entry"):
        append_journal_entry(
            market=selected_market,
            bias=prediction.get("final_bias", "N/A"),
            confidence=prediction.get("confidence_score", 0),
            note=journal_note,
            provider=provider_label,
            source="TrendIQ",
        )
        st.success("Journal entry saved.")

    journal_df = load_journal_entries()
    if not journal_df.empty:
        safe_journal = sanitize_for_streamlit(journal_df)
        st.dataframe(safe_journal.tail(20).reset_index(drop=True), width='stretch')
    else:
        st.warning("No journal entries have been saved yet.")

with tab9:
    st.header("Prediction Accuracy Tracker")
    st.write(
        "Use the prediction history to monitor directional accuracy and horizon performance for TrendIQ signals. "
        "Pending outcomes are evaluated from price history when available."
    )

    prediction_log_df = load_prediction_entries_log()
    if st.button("Evaluate pending prediction outcomes"):
        with st.spinner("Evaluating prediction outcomes..."):
            prediction_log_df = evaluate_pending_predictions(provider=DATA_PROVIDERS.get(provider_label, "yfinance"))
            st.success("Pending predictions evaluated.")

    if prediction_log_df.empty:
        st.warning("No prediction history found yet. Enable auto-log or save predictions manually.")
    else:
        prediction_log_df = prediction_log_df.sort_values(by="timestamp", ascending=False)
        latest_predictions = sanitize_for_streamlit(prediction_log_df.head(120).reset_index(drop=True))

        metrics = {}
        for horizon in ["1h", "4h", "1d"]:
            correct_col = f"correct_{horizon}"
            if correct_col in prediction_log_df.columns:
                values = prediction_log_df[prediction_log_df[correct_col].notna()][correct_col]
                metrics[f"accuracy_{horizon}"] = (
                    f"{values.mean() * 100:.1f}% ({len(values)} evaluated)"
                    if len(values) > 0
                    else "Pending"
                )
            else:
                metrics[f"accuracy_{horizon}"] = "Pending"

        acc1, acc2, acc3 = st.columns(3)
        acc1.metric("1h Accuracy", metrics["accuracy_1h"])
        acc2.metric("4h Accuracy", metrics["accuracy_4h"])
        acc3.metric("1d Accuracy", metrics["accuracy_1d"])

        market_counts = (
            prediction_log_df.groupby("market")["timestamp"].count().sort_values(ascending=False).reset_index()
        )
        if not market_counts.empty:
            st.subheader("Prediction Volume by Market")
            st.dataframe(market_counts.rename(columns={"timestamp": "count"}), width='stretch')

        st.subheader("Recent Predictions")
        st.dataframe(latest_predictions, width='stretch')

        if "return_1d_pct" in prediction_log_df.columns:
            avg_returns = prediction_log_df.groupby("market")["return_1d_pct"].mean().dropna().reset_index()
            if not avg_returns.empty:
                avg_returns.columns = ["Market", "Avg 1d Return (%)"]
                st.subheader("Average 1d Return by Market")
                st.dataframe(sanitize_for_streamlit(avg_returns), width='stretch')

with tab8:
    st.header("Backtesting")
    st.write(
        "Run a simple moving-average crossover backtest on the selected market history. "
        "This helps evaluate the signal generation logic against past price action."
    )

    fast_period = st.slider("Fast MA period", min_value=5, max_value=20, value=10)
    slow_period = st.slider("Slow MA period", min_value=fast_period + 5, max_value=60, value=30)
    initial_capital = st.number_input("Initial capital", value=10000.0, step=1000.0)

    backtest_result = backtest_moving_average_crossover(
        data,
        fast_period=fast_period,
        slow_period=slow_period,
        initial_capital=initial_capital,
    )

    st.metric("Total Return", f"{backtest_result.get('total_return', 0)}%")
    st.metric("Win Rate", f"{backtest_result.get('win_rate', 0)}%")
    st.write(backtest_result.get("summary", "Backtest summary not available."))

    if not backtest_result.get("equity_curve", pd.DataFrame()).empty:
        equity_plot = create_equity_curve_chart(backtest_result["equity_curve"])
        st.plotly_chart(equity_plot, use_container_width=True)

    if backtest_result.get("trades"):
        trade_df = pd.DataFrame(backtest_result["trades"])
        st.dataframe(sanitize_for_streamlit(trade_df), width='stretch')

st.divider()

st.caption(
    "TrendIQ Markets | Educational market analytics only | "
    "Free data may be delayed and may differ from broker prices."
)
