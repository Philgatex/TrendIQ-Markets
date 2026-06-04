import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path('.').resolve()))


def test_crypto_connector():
    try:
        from modules import crypto
    except Exception as e:
        print('PROVIDERS_TEST: SKIP crypto (missing module)', e)
        return

    try:
        df = crypto.get_crypto_history('BTC-USD', provider='ccxt', timeframe='15m', limit=10)
        assert isinstance(df, pd.DataFrame)
        print('PROVIDERS_TEST: crypto OK')
    except Exception as e:
        print('PROVIDERS_TEST: crypto FAIL', e)
        raise


def test_mt5_connector():
    try:
        from modules import mt5_connector as mt5
    except Exception as e:
        print('PROVIDERS_TEST: SKIP mt5 (missing module)', e)
        return

    try:
        connected = mt5.connect_mt5()
        # connect_mt5 returns False when MetaTrader5 package / terminal is unavailable
        print('PROVIDERS_TEST: mt5 OK (connected=' + str(bool(connected)) + ')')
    except Exception as e:
        print('PROVIDERS_TEST: mt5 FAIL', e)
        raise


if __name__ == '__main__':
    test_crypto_connector()
    test_mt5_connector()
