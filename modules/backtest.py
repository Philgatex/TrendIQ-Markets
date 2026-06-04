import numpy as np
import pandas as pd


def backtest_moving_average_crossover(
    df: pd.DataFrame,
    fast_period: int = 10,
    slow_period: int = 30,
    initial_capital: float = 10000.0,
) -> dict:
    if df is None or df.empty or len(df) < slow_period + 2:
        return {
            "total_return": 0.0,
            "trades": [],
            "win_rate": 0.0,
            "equity_curve": pd.DataFrame(),
            "summary": "Not enough data for backtest.",
        }

    data = df.copy()
    data["fast_ma"] = data["Close"].rolling(window=fast_period).mean()
    data["slow_ma"] = data["Close"].rolling(window=slow_period).mean()
    data = data.dropna(subset=["fast_ma", "slow_ma"]).reset_index(drop=True)

    data["signal"] = np.where(data["fast_ma"] > data["slow_ma"], 1, 0)
    data["position"] = data["signal"].diff().fillna(0)

    cash = initial_capital
    position = 0
    shares = 0.0
    trades = []
    equity_curve = []

    for _, row in data.iterrows():
        if row["position"] == 1 and position == 0:
            shares = cash / row["Close"]
            cash = 0.0
            position = 1
            trades.append({
                "type": "entry",
                "price": float(row["Close"]),
                "date": str(row.get("Datetime", row.get("Date", ""))),
            })
        elif row["position"] == -1 and position == 1:
            cash = shares * row["Close"]
            trades.append({
                "type": "exit",
                "price": float(row["Close"]),
                "date": str(row.get("Datetime", row.get("Date", ""))),
                "pnl": round((row["Close"] - trades[-1]["price"]) * shares, 2) if trades else 0.0,
            })
            shares = 0.0
            position = 0

        equity = cash + (shares * row["Close"])
        equity_curve.append(
            {
                "Datetime": row.get("Datetime", row.get("Date", "")),
                "Equity": round(equity, 2),
            }
        )

    if position == 1 and shares > 0:
        closing_price = float(data.iloc[-1]["Close"])
        cash = shares * closing_price
        position = 0

    equity_df = pd.DataFrame(equity_curve)
    final_equity = float(equity_df["Equity"].iloc[-1]) if not equity_df.empty else initial_capital
    total_return = round(((final_equity - initial_capital) / initial_capital) * 100, 2)

    win_trades = [trade for trade in trades if trade["type"] == "exit" and trade.get("pnl", 0) > 0]
    exit_trades = [trade for trade in trades if trade["type"] == "exit"]
    win_rate = round(len(win_trades) / len(exit_trades) * 100, 1) if exit_trades else 0.0

    return {
        "total_return": total_return,
        "trades": trades,
        "win_rate": win_rate,
        "equity_curve": equity_df,
        "summary": f"Backtest using MA crossover ({fast_period}/{slow_period}).",
    }
