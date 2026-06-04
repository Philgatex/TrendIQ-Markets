from modules.news_engine import fetch_market_news, get_economic_calendar


def test_fetch_market_news_returns_list():
    news = fetch_market_news(page_size=2)
    assert isinstance(news, list)
    assert len(news) <= 2
    if news:
        assert "title" in news[0]
        assert "source" in news[0]


def test_get_economic_calendar_returns_events():
    events = get_economic_calendar(days=3)
    assert isinstance(events, list)
    assert len(events) >= 1
    assert "event" in events[0]
    assert "impact" in events[0]
