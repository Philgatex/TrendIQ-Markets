import os
from datetime import datetime, timedelta

import pandas as pd

from modules.prediction_log import (
    append_prediction_entry,
    evaluate_prediction_row,
    load_prediction_entries,
    get_prediction_log_path,
)


def test_prediction_log_append_and_load(tmp_path):
    log_file = tmp_path / "predictions.csv"
    os.environ["TRENDIQ_PREDICTION_LOG_PATH"] = str(log_file)

    append_prediction_entry(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "market": "BTC/USD",
            "symbol": "BTC-USD",
            "provider": "Yahoo Finance",
            "period": "1d",
            "interval": "1h",
            "final_bias": "Bullish",
            "confidence_score": 84.2,
            "current_price": 50000.0,
            "support": 49500.0,
            "resistance": 51000.0,
            "note": "Bullish breakout expected.",
        }
    )

    predictions_df = load_prediction_entries()
    assert not predictions_df.empty
    assert predictions_df.iloc[0]["market"] == "BTC/USD"
    assert float(predictions_df.iloc[0]["confidence_score"]) == 84.2
    assert "Bullish breakout expected" in predictions_df.iloc[0]["note"]
    assert os.path.basename(get_prediction_log_path()) == "predictions.csv"


def test_evaluate_prediction_row_with_history():
    timestamp = datetime.utcnow().replace(microsecond=0)
    history_rows = []
    for minutes in range(0, 1500, 5):
        row_time = timestamp + timedelta(minutes=minutes)
        history_rows.append({"Datetime": row_time, "Close": 100 + minutes * 0.05})
    history_df = pd.DataFrame(history_rows)

    entry = pd.Series(
        {
            "timestamp": timestamp.isoformat(),
            "current_price": 100.0,
            "final_bias": "Bullish",
        }
    )

    results = evaluate_prediction_row(entry, history_df)
    assert results["return_1h_pct"] is not None
    assert results["correct_1h"] is True
    assert results["return_4h_pct"] is not None
    assert results["correct_4h"] is True
    assert results["return_1d_pct"] is not None
    assert results["correct_1d"] is True
