import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(
    page_title="TrendIQ Markets",
    page_icon="📈",
    layout="wide"
)

st.title("TrendIQ Markets")
st.subheader("Real-time multi-market analysis and prediction dashboard")

st.warning(
    "This platform provides educational market analysis only. "
    "It is not financial advice and does not guarantee profits."
)

markets = {
    "Nasdaq-100 / US100 Proxy": "QQQ",
    "S&P 500 Proxy": "SPY",
    "Dow Jones / US30 Proxy": "DIA",
    "Gold Proxy": "GC=F",
    "Crude Oil": "CL=F",
    "Bitcoin": "BTC-USD",
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X"
}

selected_market = st.selectbox("Select Market", list(markets.keys()))
ticker = markets[selected_market]

period = st.selectbox("Select Period", ["1d", "5d", "1mo", "3mo", "6mo"], index=1)
interval = st.selectbox("Select Interval", ["1m", "5m", "15m", "30m", "1h", "1d"], index=2)

data = yf.download(ticker, period=period, interval=interval, progress=False)

if data.empty:
    st.error("No market data available. Try another market, period, or interval.")
else:
    data = data.reset_index()

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [col[0] for col in data.columns]

    latest_close = float(data["Close"].iloc[-1])
    previous_close = float(data["Close"].iloc[-2]) if len(data) > 1 else latest_close
    change = latest_close - previous_close
    change_pct = (change / previous_close) * 100 if previous_close != 0 else 0

    col1, col2, col3 = st.columns(3)

    col1.metric("Current Price", f"{latest_close:,.2f}")
    col2.metric("Change", f"{change:,.2f}", f"{change_pct:.2f}%")
    col3.metric("Market", selected_market)

    data["EMA20"] = data["Close"].ewm(span=20, adjust=False).mean()
    data["EMA50"] = data["Close"].ewm(span=50, adjust=False).mean()

    delta = data["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    data["RSI"] = 100 - (100 / (1 + rs))

    latest_ema20 = float(data["EMA20"].iloc[-1])
    latest_ema50 = float(data["EMA50"].iloc[-1])
    latest_rsi = float(data["RSI"].iloc[-1]) if not pd.isna(data["RSI"].iloc[-1]) else 50

    bullish_score = 0
    bearish_score = 0

    if latest_close > latest_ema20:
        bullish_score += 1
    else:
        bearish_score += 1

    if latest_close > latest_ema50:
        bullish_score += 2
    else:
        bearish_score += 2

    if latest_ema20 > latest_ema50:
        bullish_score += 2
    else:
        bearish_score += 2

    if latest_rsi > 60:
        bullish_score += 1
    elif latest_rsi < 40:
        bearish_score += 1

    total_score = bullish_score + bearish_score

    bullish_probability = round((bullish_score / total_score) * 100, 1) if total_score else 50
    bearish_probability = round((bearish_score / total_score) * 100, 1) if total_score else 50
    sideways_probability = round(100 - abs(bullish_probability - bearish_probability), 1)

    if bullish_probability > bearish_probability:
        prediction = "Bullish"
    elif bearish_probability > bullish_probability:
        prediction = "Bearish"
    else:
        prediction = "Sideways"

    st.divider()

    st.subheader("Market Prediction")

    p1, p2, p3 = st.columns(3)

    p1.metric("Prediction", prediction)
    p2.metric("Bullish Probability", f"{bullish_probability}%")
    p3.metric("Bearish Probability", f"{bearish_probability}%")

    st.write(f"Sideways/uncertainty score: **{sideways_probability}%**")

    st.subheader("Price Chart")

    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=data[data.columns[0]],
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            name="Price"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=data[data.columns[0]],
            y=data["EMA20"],
            mode="lines",
            name="EMA 20"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=data[data.columns[0]],
            y=data["EMA50"],
            mode="lines",
            name="EMA 50"
        )
    )

    fig.update_layout(
        height=600,
        xaxis_rangeslider_visible=False,
        title=f"{selected_market} Price Chart"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Technical Summary")

    st.write(f"EMA 20: **{latest_ema20:,.2f}**")
    st.write(f"EMA 50: **{latest_ema50:,.2f}**")
    st.write(f"RSI 14: **{latest_rsi:.2f}**")

    st.info(
        "Next upgrade: add support/resistance detection, news sentiment, "
        "economic calendar, MT5 broker data, and backtesting."
    )
