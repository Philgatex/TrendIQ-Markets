import os
import signal
import sys
import time

from modules.market_data import MARKET_SYMBOLS
from modules.poller import start_global_poller, stop_global_poller


def main():
    interval = int(os.environ.get("TRENDIQ_POLLER_INTERVAL", "30"))
    snapshot_db = os.environ.get("TRENDIQ_SNAPSHOT_DB", "trendiq_snapshot.db")
    os.environ["TRENDIQ_SNAPSHOT_DB"] = snapshot_db

    print(f"Starting TrendIQ snapshot poller with interval={interval}s and DB={snapshot_db}")
    start_global_poller(interval=interval, symbols=MARKET_SYMBOLS)

    def shutdown(signum, frame):
        print("Stopping TrendIQ poller...")
        stop_global_poller()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
