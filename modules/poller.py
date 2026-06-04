import os
import threading
import time
from typing import Optional

from .market_data import get_latest_snapshot
from .snapshot_store import write_latest_snapshot, DEFAULT_DB_PATH

SNAPSHOT_PATH = os.environ.get("TRENDIQ_SNAPSHOT_DB", DEFAULT_DB_PATH)


class SnapshotPoller:
    def __init__(self, interval: int = 30, symbols=None):
        self.interval = max(5, int(interval))
        self.symbols = symbols
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _write_snapshot(self):
        try:
            df = get_latest_snapshot(self.symbols)
            write_latest_snapshot(df, path=SNAPSHOT_PATH)
        except Exception:
            # fail silently; poller should not crash the app
            pass

    def _run(self):
        while not self._stop.is_set():
            self._write_snapshot()
            # wait but allow quick stop
            for _ in range(int(self.interval)):
                if self._stop.is_set():
                    break
                time.sleep(1)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)


_GLOBAL_POLLER: Optional[SnapshotPoller] = None


def start_global_poller(interval: int = 30, symbols=None):
    global _GLOBAL_POLLER
    if _GLOBAL_POLLER is None:
        _GLOBAL_POLLER = SnapshotPoller(interval=interval, symbols=symbols)
        _GLOBAL_POLLER.start()


def stop_global_poller():
    global _GLOBAL_POLLER
    if _GLOBAL_POLLER is not None:
        _GLOBAL_POLLER.stop()
        _GLOBAL_POLLER = None
