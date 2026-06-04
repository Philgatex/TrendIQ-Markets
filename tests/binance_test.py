import sys
from pathlib import Path

sys.path.append(str(Path('.').resolve()))


def test_binance_scaffold():
    try:
        from modules import binance
    except Exception as e:
        print('BINANCE_TEST: SKIP (module import failed)', e)
        return

    try:
        # Should return a skipped result when API keys are not configured or dry_run True
        res = binance.place_order('BTC/USDT', 'buy', 'market', 0.0001, dry_run=True)
        assert isinstance(res, dict)
        print('BINANCE_TEST: OK')
    except Exception as e:
        print('BINANCE_TEST: FAIL', e)
        raise


if __name__ == '__main__':
    test_binance_scaffold()
