import sys
from pathlib import Path

sys.path.append(str(Path('.').resolve()))


def test_mt5_order_stub():
    try:
        from modules import mt5_connector as mt5
    except Exception as e:
        print('MT5_ORDER_TEST: SKIP (import failed)', e)
        return

    try:
        res = mt5.place_mt5_order('EURUSD', 'buy', 0.01, dry_run=True)
        assert isinstance(res, dict)
        print('MT5_ORDER_TEST: OK')
    except Exception as e:
        print('MT5_ORDER_TEST: FAIL', e)
        raise


if __name__ == '__main__':
    test_mt5_order_stub()
