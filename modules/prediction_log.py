import csv
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd

PREDICTION_LOG_COLUMNS = [
    "timestamp",
    "market",
    "symbol",
    "market_type",
    "provider",
    "period",
    "interval",
    "final_bias",
    "confidence_score",
    "bullish_probability",
    "bearish_probability",
    "sideways_probability",
    "current_price",
    "support",
    "resistance",
    "buy_confirmation",
    "sell_confirmation",
    "bullish_invalidation",
    "bearish_invalidation",
    "tp1_bullish",
    "tp2_bullish",
    "tp1_bearish",
    "tp2_bearish",
    "market_regime",
    "note",
    "return_1h_pct",
    "correct_1h",
    "return_4h_pct",
    "correct_4h",
    "return_1d_pct",
    "correct_1d",
]


def get_prediction_log_path() -> str:
    return os.path.abspath(os.environ.get("TRENDIQ_PREDICTION_LOG_PATH", "trendiq_predictions.csv"))


def ensure_prediction_log(path: Optional[str] = None) -> None:
    path = path or get_prediction_log_path()
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=PREDICTION_LOG_COLUMNS)
            writer.writeheader()


def append_prediction_entry(entry: Dict[str, Any], path: Optional[str] = None) -> None:
    path = path or get_prediction_log_path()
    ensure_prediction_log(path)

    normalized = {col: entry.get(col) for col in PREDICTION_LOG_COLUMNS}
    with open(path, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=PREDICTION_LOG_COLUMNS)
        writer.writerow(normalized)


def load_prediction_entries(path: Optional[str] = None) -> pd.DataFrame:
    path = path or get_prediction_log_path()
    if not os.path.exists(path):
        return pd.DataFrame(columns=PREDICTION_LOG_COLUMNS)

    try:
        df = pd.read_csv(path)
        for col in [
            "confidence_score",
            "bullish_probability",
            "bearish_probability",
            "sideways_probability",
            "current_price",
            "support",
            "resistance",
            "buy_confirmation",
            "sell_confirmation",
            "bullish_invalidation",
            "bearish_invalidation",
            "tp1_bullish",
            "tp2_bullish",
            "tp1_bearish",
            "tp2_bearish",
            "return_1h_pct",
            "return_4h_pct",
            "return_1d_pct",
        ]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame(columns=PREDICTION_LOG_COLUMNS)


def save_prediction_entries(df: pd.DataFrame, path: Optional[str] = None) -> None:
    path = path or get_prediction_log_path()
    ensure_prediction_log(path)
    df.to_csv(path, index=False)


def _find_price_at_or_after(timestamp: datetime, df: pd.DataFrame, horizon: timedelta) -> Optional[float]:
    if df is None or df.empty:
        return None

    target_time = timestamp + horizon
    df = df.copy()
    if "Datetime" not in df.columns and "datetime" in df.columns:
        df["Datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    if "Datetime" not in df.columns:
        return None

    df["Datetime"] = pd.to_datetime(df["Datetime"], errors="coerce")
    df = df.dropna(subset=["Datetime"]).sort_values("Datetime")
    candidate = df[df["Datetime"] >= target_time]
    if candidate.empty:
        return None
    return float(candidate.iloc[0]["Close"])


def evaluate_prediction_row(entry: pd.Series, history_df: pd.DataFrame) -> Dict[str, Any]:
    result = {
        "return_1h_pct": None,
        "correct_1h": None,
        "return_4h_pct": None,
        "correct_4h": None,
        "return_1d_pct": None,
        "correct_1d": None,
    }

    try:
        entry_time = pd.to_datetime(entry["timestamp"], errors="coerce")
        if pd.isna(entry_time):
            return result
        entry_price = float(entry["current_price"])
        final_bias = str(entry.get("final_bias", "")).lower()

        thresholds = {
            "bullish": 0.1,
            "bearish": -0.1,
            "sideways": 0.3,
        }

        for label, horizon in [("1h", timedelta(hours=1)), ("4h", timedelta(hours=4)), ("1d", timedelta(days=1))]:
            price_key = f"return_{label}_pct"
            correct_key = f"correct_{label}"
            target_price = _find_price_at_or_after(entry_time, history_df, horizon)
            if target_price is None:
                continue
            return_pct = round((target_price / entry_price - 1) * 100, 3)
            result[price_key] = return_pct

            if "sideways" in final_bias.lower():
                result[correct_key] = abs(return_pct) <= thresholds["sideways"]
            elif "bullish" in final_bias.lower():
                result[correct_key] = return_pct >= thresholds["bullish"]
            elif "bearish" in final_bias.lower():
                result[correct_key] = return_pct <= thresholds["bearish"]
            else:
                result[correct_key] = None
    except Exception:
        pass

    return result


def evaluate_pending_predictions(path: Optional[str] = None, provider: str = "yfinance") -> pd.DataFrame:
    path = path or get_prediction_log_path()
    df = load_prediction_entries(path)
    if df.empty:
        return df

    updated = False
    for index, row in df.iterrows():
        needs_evaluation = False
        for suffix in ["1h", "4h", "1d"]:
            if pd.isna(row.get(f"correct_{suffix}")):
                needs_evaluation = True
                break
        if not needs_evaluation:
            continue

        try:
            from .market_data import get_market_data

            history = get_market_data(
                row["symbol"],
                period="7d",
                interval="5m",
                provider=provider,
            )
            if history.empty:
                continue
            eval_results = evaluate_prediction_row(row, history)
            for key, value in eval_results.items():
                df.at[index, key] = value
            updated = True
        except Exception:
            continue

    if updated:
        save_prediction_entries(df, path)

    return df
