import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from modules.market_data import (
    MARKET_SYMBOLS,
    get_market_data,
    get_latest_snapshot,
    get_market_info
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


@st.cache_data(ttl=60)
def cached_market_data(symbol: str, period: str, interval: str):
    return get_market_data(symbol, period, interval)


@st.cache_data(ttl=120)
def cached_snapshot():
    return get_latest_snapshot(MARKET_SYMBOLS)


def format_number(value, decimals=2):
    try:
        return f"{float(value):,.{decimals}f}"
    except Exception:
        return "N/A"


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
            name="Price"
        )
    )

    if "EMA20" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df[time_col],
                y=df["EMA20"],
                mode="lines",
                name="EMA 20"
            )
        )

    if "EMA50" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df[time_col],
                y=df["EMA50"],
                mode="lines",
                name="EMA 50"
            )
        )

    if "EMA200" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df[time_col],
                y=df["EMA200"],
                mode="lines",
                name="EMA 200"
            )
        )

    fig.update_layout(
        title=f"{market_name} Price Chart",
        height=650,
        xaxis_rangeslider_visible=False,
        margin=dict(l=20, r=20, t=50, b=20)
    )

    return fig


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
    data = cached_market_data(symbol, period, interval)
    snapshot_df = cached_snapshot()

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
    f"Data source: **yfinance free market data**"
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
        st.dataframe(
            regime_table.style.format({
                "Price": "{:,.2f}",
                "% Change": "{:.2f}%"
            }),
            use_container_width=True
        )
    else:
        st.warning("No global market snapshot available.")


with tab2:
    st.header("Market Chart")

    fig = create_candlestick_chart(data, selected_market)
    st.plotly_chart(fig, use_container_width=True)

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

    st.dataframe(level_df, use_container_width=True)

    st.subheader("Prediction Explanation")

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

    st.dataframe(rr_df, use_container_width=True)

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

    st.dataframe(summary_df, use_container_width=True)


st.divider()

st.caption(
    "TrendIQ Markets | Educational market analytics only | "
    "Free data may be delayed and may differ from broker prices."
)
