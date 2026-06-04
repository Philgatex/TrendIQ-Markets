import sys
from pathlib import Path

sys.path.append(str(Path('.').resolve()))


def test_sanitize_for_streamlit_nested_data():
    from app import sanitize_for_streamlit
    import pandas as pd

    df = pd.DataFrame({
        'Datetime': ['2025-01-01', '2025-01-02'],
        'Price': ['100', '101'],
        'Meta': [{'test': 1}, ['a', 'b']],
    })

    sanitized = sanitize_for_streamlit(df)
    assert 'Datetime' in sanitized.columns
    assert sanitized['Price'].dtype.kind in {'f', 'i'}
    assert sanitized['Meta'].dtype == object
    assert sanitized['Meta'].iloc[0].startswith('{')
    print('DATAFRAME_TEST: nested data OK')


if __name__ == '__main__':
    test_sanitize_for_streamlit_nested_data()
