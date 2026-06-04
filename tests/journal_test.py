import os
import tempfile

import pandas as pd

from modules.journal import append_journal_entry, load_journal_entries


def test_journal_append_and_load(tmp_path):
    journal_file = tmp_path / "journal.csv"
    os.environ["TRENDIQ_JOURNAL_PATH"] = str(journal_file)

    append_journal_entry(
        market="SPY",
        bias="Bullish",
        confidence=78.5,
        note="Trend support held, scheduling a long bias.",
        provider="Yahoo Finance",
        source="TrendIQ",
    )

    journal_df = load_journal_entries()
    assert not journal_df.empty
    assert journal_df.iloc[0]["market"] == "SPY"
    assert float(journal_df.iloc[0]["confidence"]) == 78.5
    assert "Trend support held" in journal_df.iloc[0]["note"]
