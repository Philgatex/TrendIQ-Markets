import csv
import os
from datetime import datetime
from typing import Dict, List

import pandas as pd

JOURNAL_COLUMNS = [
    "timestamp",
    "market",
    "bias",
    "confidence",
    "note",
    "provider",
    "source",
]


def get_journal_path() -> str:
    path = os.environ.get("TRENDIQ_JOURNAL_PATH", "trendiq_journal.csv")
    return os.path.abspath(path)


def ensure_journal_file(path: str) -> None:
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=JOURNAL_COLUMNS)
            writer.writeheader()


def load_journal_entries() -> pd.DataFrame:
    path = get_journal_path()
    if not os.path.exists(path):
        return pd.DataFrame(columns=JOURNAL_COLUMNS)

    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame(columns=JOURNAL_COLUMNS)


def append_journal_entry(
    market: str,
    bias: str,
    confidence: float,
    note: str,
    provider: str = "unknown",
    source: str = "TrendIQ",
) -> None:
    path = get_journal_path()
    ensure_journal_file(path)

    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "market": market,
        "bias": bias,
        "confidence": confidence,
        "note": note,
        "provider": provider,
        "source": source,
    }

    with open(path, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=JOURNAL_COLUMNS)
        writer.writerow(entry)
