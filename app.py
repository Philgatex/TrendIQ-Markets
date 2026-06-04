import os
import sys
# Ensure repo root is on path (helps Streamlit Cloud imports)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from streamlit.components.v1 import html as st_html
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Ensure repo root is on path (helps Streamlit Cloud imports)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.market_data import (
    DATA_PROVIDERS,
    MARKET_SYMBOLS,
    get_market_data,
    get_latest_snapshot,
    get_market_info,
    get_market_trend_summary
)

from modules.indicators import (
    add_indicators,
    get_indicator_summary,
    detect_support_resistance
)

from modules.sentiment_engine import build_market_regime
from modules.prediction_engine import generate_prediction
from modules.risk_engine import generate_trade_plan


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


@st.cache_data(ttl=60)
def cached_market_data(symbol: str, period: str, interval: str, provider: str):
    return get_market_data(symbol, period, interval, provider)


@st.cache_data(ttl=120)
def cached_snapshot():
    return get_latest_snapshot(MARKET_SYMBOLS)


def format_number(value, decimals=2):
    try:
        return f"{float(value):,.{decimals}f}"
    except Exception:
        return "N/A"


def sanitize_for_streamlit(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure DataFrame dtypes are safe for Streamlit/pyarrow rendering.

    - Convert numeric-like columns to numeric (coerce errors).
    - Convert object columns with mixed types to strings.
    - Preserve Datetime columns.
    """
    if df is None or df.empty:
        return df

    df = df.copy()

    for col in df.columns:
        try:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                continue
            # Try converting to numeric
            df[col] = pd.to_numeric(df[col], errors="ignore")
            # If still object with mixed types, cast to str
            if df[col].dtype == object:
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


st.title("TrendIQ Markets")
st.caption("Real-time multi-market analysis, prediction scoring, and risk planning dashboard.")

st.warning(
    "This tool provides educational market analysis only. "
    "It is not financial advice and does not guarantee profits. "
    "Free market data may be delayed and may differ from broker CFD prices."
)


st.sidebar.header("Dashboard Settings")

market_names = list(MARKET_SYMBOLS.keys())

selected_market = st.sidebar.selectbox(
    "Select Market",
    market_names,
    index=0
)

provider_label = st.sidebar.selectbox(
    "Data Provider",
    list(DATA_PROVIDERS.keys()),
    index=0,
    help="Select a live market data provider. Twelve Data requires a free API key set in TWELVE_DATA_API_KEY."
)

chart_mode = st.sidebar.selectbox(
    "Chart Mode",
    ["TrendIQ chart", "TradingView widget"],
    index=0,
    help="Use a built-in TrendIQ chart or the TradingView-style embedded widget."
)

if provider_label == "Twelve Data (free API)" and not os.environ.get("TWELVE_DATA_API_KEY"):
    st.sidebar.warning(
        "Twelve Data is selected but TWELVE_DATA_API_KEY is not configured. "
        "The app will fall back to Yahoo Finance until a free Twelve Data key is provided."
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

if manual_refresh:
    st.cache_data.clear()


market_info = get_market_info(selected_market)
symbol = market_info.get("symbol")
market_type = market_info.get("type", "index")


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
change_pct = (change / previous_close) * 100 if previous_close != 0 else 0


st.subheader("Selected Market Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Market", selected_market)
col2.metric("Current Price", format_number(latest_close))
col3.metric("Change", format_number(change), f"{change_pct:.2f}%")
col4.metric("Bias", prediction.get("final_bias", "N/A"))

st.caption(
    f"Symbol used: **{symbol}** | Market type: **{market_type}** | "
    f"Data provider: **{provider_label}**"
)


tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Global Market Regime",
    "Market Chart",
    "Prediction",
    "Risk Manager",
    "Technical Summary"
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

    sr = detect_support_resistance(data)

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


st.divider()

st.caption(
    "TrendIQ Markets | Educational market analytics only | "
    "Free data may be delayed and may differ from broker prices."
)
