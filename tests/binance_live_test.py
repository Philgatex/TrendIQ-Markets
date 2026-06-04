import os
import sys
from pathlib import Path

sys.path.append(str(Path('.').resolve()))


def test_binance_testnet_exchange():
    os.environ['BINANCE_TESTNET'] = 'true'
    try:
        from modules import binance

        ex = binance._get_ccxt_exchange(testnet=True)
        assert ex is not None
        api_urls = getattr(ex, 'urls', {})
        assert 'testnet.binance.vision' in str(api_urls)
        print('BINANCE_LIVE_TEST: testnet exchange OK')
    except Exception as e:
        print('BINANCE_LIVE_TEST: SKIP or FAIL', e)
        raise
    finally:
        os.environ.pop('BINANCE_TESTNET', None)


def test_binance_live_order_guard():
    os.environ.pop('BINANCE_ALLOW_LIVE_ORDERS', None)
    try:
        from modules import binance

        res = binance.place_order('BTC/USDT', 'buy', 'market', 0.0001, dry_run=False)
        assert isinstance(res, dict)
        assert res.get('skipped', False) is True
        assert 'Live Binance orders disabled' in res.get('reason', '')
        print('BINANCE_LIVE_TEST: live guard OK')
    except Exception as e:
        print('BINANCE_LIVE_TEST: FAIL', e)
        raise


if __name__ == '__main__':
    test_binance_testnet_exchange()
    test_binance_live_order_guard()
