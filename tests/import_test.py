import sys

sys.path.append('.')

def main():
    try:
        import modules.market_data as md
        import modules.indicators as ind
        import modules.prediction_engine as pe
        import modules.risk_engine as re
        import modules.sentiment_engine as se

        # Basic smoke checks
        assert hasattr(md, 'MARKET_SYMBOLS')
        assert hasattr(ind, 'add_indicators')
        assert hasattr(pe, 'generate_prediction')
        assert hasattr(re, 'generate_trade_plan')
        assert hasattr(se, 'build_market_regime')

        print('IMPORT_SMOKE_TEST: OK')
    except Exception as e:
        print('IMPORT_SMOKE_TEST: FAIL', e)
        raise


if __name__ == '__main__':
    main()
