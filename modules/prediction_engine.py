import pandas as pd

from .indicators import detect_support_resistance


def normalize_probabilities(bullish_score: float, bearish_score: float, sideways_score: float) -> dict:
    total = bullish_score + bearish_score + sideways_score

    if total <= 0:
        return {
            "bullish_probability": 33.3,
            "bearish_probability": 33.3,
            "sideways_probability": 33.4
        }

    bullish = round((bullish_score / total) * 100, 1)
    bearish = round((bearish_score / total) * 100, 1)
    sideways = round(100 - bullish - bearish, 1)

    return {
        "bullish_probability": bullish,
        "bearish_probability": bearish,
        "sideways_probability": sideways
    }


def generate_prediction(df: pd.DataFrame, regime: dict, market_type: str = "index") -> dict:
    if df is None or df.empty or len(df) < 50:
        return {
            "final_bias": "No Data",
            "confidence_score": 0,
            "bullish_probability": 0,
            "bearish_probability": 0,
            "sideways_probability": 0,
            "explanations": ["Not enough data to generate prediction."],
            "levels": {}
        }

    latest = df.iloc[-1]

    close = float(latest["Close"])
    ema20 = float(latest["EMA20"])
    ema50 = float(latest["EMA50"])
    ema200 = float(latest["EMA200"])
    rsi = float(latest["RSI14"])
    macd = float(latest["MACD"])
    macd_signal = float(latest["MACD_SIGNAL"])
    atr = float(latest["ATR14"])

    bullish_score = 1
    bearish_score = 1
    sideways_score = 1

    explanations = []

    if close > ema20:
        bullish_score += 1
        explanations.append("Price is above EMA 20.")
    else:
        bearish_score += 1
        explanations.append("Price is below EMA 20.")

    if close > ema50:
        bullish_score += 2
        explanations.append("Price is above EMA 50.")
    else:
        bearish_score += 2
        explanations.append("Price is below EMA 50.")

    if ema20 > ema50:
        bullish_score += 2
        explanations.append("EMA 20 is above EMA 50.")
    else:
        bearish_score += 2
        explanations.append("EMA 20 is below EMA 50.")

    if ema50 > ema200:
        bullish_score += 1
        explanations.append("EMA 50 is above EMA 200.")
    else:
        bearish_score += 1
        explanations.append("EMA 50 is below EMA 200.")

    if 50 <= rsi <= 70:
        bullish_score += 1
        explanations.append("RSI supports bullish momentum.")
    elif rsi < 45:
        bearish_score += 1
        explanations.append("RSI shows bearish momentum.")
    elif rsi > 75:
        bearish_score += 0.5
        sideways_score += 1
        explanations.append("RSI is overbought; pullback risk is elevated.")
    else:
        sideways_score += 1
        explanations.append("RSI is neutral.")

    if macd > macd_signal:
        bullish_score += 1
        explanations.append("MACD is bullish.")
    else:
        bearish_score += 1
        explanations.append("MACD is bearish.")

    levels = detect_support_resistance(df)

    support = levels.get("support")
    resistance = levels.get("resistance")

    if support and resistance:
        distance_to_support = abs(close - support)
        distance_to_resistance = abs(resistance - close)

        if distance_to_support < distance_to_resistance:
            bullish_score += 0.5
            explanations.append("Price is closer to support than resistance.")
        elif distance_to_resistance < distance_to_support:
            bearish_score += 0.5
            explanations.append("Price is closer to resistance than support.")

    market_regime = regime.get("market_regime", "Mixed / Cautious")

    if market_type in ["index", "crypto"]:
        if market_regime == "Risk-On":
            bullish_score += 2
            explanations.append("Global market regime is risk-on, supportive for indices and crypto.")
        elif market_regime == "Risk-Off":
            bearish_score += 2
            explanations.append("Global market regime is risk-off, pressuring indices and crypto.")
        else:
            sideways_score += 1
            explanations.append("Global market regime is mixed/cautious.")

    elif market_type == "commodity":
        if market_regime == "Risk-Off":
            if close > ema20:
                bullish_score += 1
                explanations.append("Risk-off regime can support defensive commodities like gold.")
            else:
                sideways_score += 1
        else:
            sideways_score += 1

    elif market_type == "forex":
        sideways_score += 1
        explanations.append("Forex prediction requires dollar strength and rate-differential confirmation.")

    atr_pct = (atr / close) * 100 if close != 0 else 0

    if atr_pct > 2:
        sideways_score += 1
        explanations.append("High volatility reduces directional certainty.")

    probabilities = normalize_probabilities(
        bullish_score,
        bearish_score,
        sideways_score
    )

    bullish_probability = probabilities["bullish_probability"]
    bearish_probability = probabilities["bearish_probability"]
    sideways_probability = probabilities["sideways_probability"]

    max_probability = max(
        bullish_probability,
        bearish_probability,
        sideways_probability
    )

    if max_probability < 45:
        final_bias = "Sideways / Cautious"
    elif bullish_probability == max_probability:
        final_bias = "Bullish"
    elif bearish_probability == max_probability:
        final_bias = "Bearish"
    else:
        final_bias = "Sideways / Cautious"

    confidence_score = round(max_probability, 1)

    if support and resistance:
        buy_confirmation = round(resistance + (atr * 0.2), 4)
        sell_confirmation = round(support - (atr * 0.2), 4)
        bullish_invalidation = round(support - (atr * 0.3), 4)
        bearish_invalidation = round(resistance + (atr * 0.3), 4)
    else:
        buy_confirmation = round(close + atr, 4)
        sell_confirmation = round(close - atr, 4)
        bullish_invalidation = round(close - atr, 4)
        bearish_invalidation = round(close + atr, 4)

    trade_levels = {
        "current_price": round(close, 4),
        "support": round(support, 4) if support else None,
        "resistance": round(resistance, 4) if resistance else None,
        "buy_confirmation": buy_confirmation,
        "sell_confirmation": sell_confirmation,
        "bullish_invalidation": bullish_invalidation,
        "bearish_invalidation": bearish_invalidation,
        "tp1_bullish": round(close + atr, 4),
        "tp2_bullish": round(close + (2 * atr), 4),
        "tp1_bearish": round(close - atr, 4),
        "tp2_bearish": round(close - (2 * atr), 4)
    }

    return {
        "final_bias": final_bias,
        "confidence_score": confidence_score,
        "bullish_probability": bullish_probability,
        "bearish_probability": bearish_probability,
        "sideways_probability": sideways_probability,
        "explanations": explanations,
        "levels": trade_levels
    }
