import pandas as pd

from modules.backtest import backtest_moving_average_crossover


def test_backtest_moving_average_crossover():
    dates = pd.date_range(start="2026-01-01", periods=40, freq="D")
    prices = [100 + i * 0.5 for i in range(40)]
    df = pd.DataFrame({"Datetime": dates, "Open": prices, "High": [p + 1 for p in prices], "Low": [p - 1 for p in prices], "Close": prices, "Volume": [1000] * 40})

    result = backtest_moving_average_crossover(df, fast_period=5, slow_period=10, initial_capital=10000.0)

    assert isinstance(result, dict)
    assert "total_return" in result
    assert "equity_curve" in result
    assert result["total_return"] >= 0.0
    assert isinstance(result["equity_curve"], pd.DataFrame)
