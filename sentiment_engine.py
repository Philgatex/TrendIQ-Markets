import pandas as pd


def classify_change(change_pct: float, market_type: str = "index") -> str:
    if pd.isna(change_pct):
        return "Neutral"

    if market_type == "bond":
        if change_pct > 0.2:
            return "Yield Rising"
        elif change_pct < -0.2:
            return "Yield Falling"
        return "Neutral"

    if change_pct > 0.25:
        return "Bullish"
    elif change_pct < -0.25:
        return "Bearish"

    return "Neutral"


def build_market_regime(snapshot_df: pd.DataFrame) -> dict:
    if snapshot_df is None or snapshot_df.empty:
        return {
            "market_regime": "No Data",
            "risk_on_probability": 0,
            "risk_off_probability": 0,
            "summary": "No market snapshot available.",
            "table": pd.DataFrame()
        }

    df = snapshot_df.copy()

    df["Signal"] = df.apply(
        lambda row: classify_change(row["% Change"], row["Type"]),
        axis=1
    )

    risk_on_score = 0
    risk_off_score = 0
    explanations = []

    us_indices = df[
        df["Market"].isin([
            "Nasdaq-100 / US100 Proxy",
            "S&P 500 / US500 Proxy",
            "Dow Jones / US30 Proxy",
            "Russell 2000 Proxy"
        ])
    ]

    global_indices = df[
        df["Market"].isin([
            "FTSE 100",
            "Nikkei 225",
            "Hang Seng",
            "DAX Germany"
        ])
    ]

    crypto = df[df["Type"] == "crypto"]
    commodities = df[df["Type"] == "commodity"]
    bonds = df[df["Type"] == "bond"]

    us_red_count = len(us_indices[us_indices["% Change"] < -0.25])
    us_green_count = len(us_indices[us_indices["% Change"] > 0.25])

    if us_red_count >= 3:
        risk_off_score += 3
        explanations.append("Most US indices are negative.")
    elif us_green_count >= 3:
        risk_on_score += 3
        explanations.append("Most US indices are positive.")

    global_red_count = len(global_indices[global_indices["% Change"] < -0.25])
    global_green_count = len(global_indices[global_indices["% Change"] > 0.25])

    if global_red_count >= 3:
        risk_off_score += 2
        explanations.append("Most global indices are negative.")
    elif global_green_count >= 3:
        risk_on_score += 2
        explanations.append("Most global indices are positive.")

    crypto_red_count = len(crypto[crypto["% Change"] < -0.5])
    crypto_green_count = len(crypto[crypto["% Change"] > 0.5])

    if crypto_red_count >= 1:
        risk_off_score += 1
        explanations.append("Crypto is under pressure.")
    elif crypto_green_count >= 1:
        risk_on_score += 1
        explanations.append("Crypto is supportive of risk appetite.")

    gold_row = commodities[commodities["Market"] == "Gold"]

    if not gold_row.empty:
        gold_change = float(gold_row["% Change"].iloc[0])

        if gold_change > 0.25 and us_red_count >= 2:
            risk_off_score += 2
            explanations.append("Gold is rising while stocks are weak, suggesting defensive demand.")
        elif gold_change < -0.25 and us_green_count >= 2:
            risk_on_score += 1
            explanations.append("Gold is weak while stocks are firm, supporting risk-on sentiment.")

    oil_row = commodities[commodities["Market"] == "WTI Crude Oil"]

    if not oil_row.empty:
        oil_change = float(oil_row["% Change"].iloc[0])
        oil_price = float(oil_row["Price"].iloc[0])

        if oil_price > 90 or oil_change > 1.0:
            risk_off_score += 1
            explanations.append("Oil is elevated, increasing inflation and risk pressure.")

    us10y = bonds[bonds["Market"] == "US 10Y Yield"]

    if not us10y.empty:
        y_change = float(us10y["% Change"].iloc[0])

        if y_change > 0.2:
            risk_off_score += 1
            explanations.append("US 10Y yield is rising, which can pressure growth stocks.")
        elif y_change < -0.2:
            risk_on_score += 1
            explanations.append("US 10Y yield is easing, which can support growth stocks.")

    total_score = risk_on_score + risk_off_score

    if total_score == 0:
        risk_on_probability = 50
        risk_off_probability = 50
    else:
        risk_on_probability = round((risk_on_score / total_score) * 100, 1)
        risk_off_probability = round((risk_off_score / total_score) * 100, 1)

    if risk_off_probability >= 65:
        market_regime = "Risk-Off"
    elif risk_on_probability >= 65:
        market_regime = "Risk-On"
    else:
        market_regime = "Mixed / Cautious"

    if not explanations:
        explanations.append("Market signals are mixed or neutral.")

    summary = " ".join(explanations)

    display_df = df[
        ["Market", "Symbol", "Type", "Price", "% Change", "Signal"]
    ].copy()

    return {
        "market_regime": market_regime,
        "risk_on_probability": risk_on_probability,
        "risk_off_probability": risk_off_probability,
        "summary": summary,
        "table": display_df
    }
