from scripts import fetch_sentiment_weekly as weekly


def test_naaim_numeric_widget_without_date_is_never_written(monkeypatch):
    monkeypatch.setattr(weekly, "http_get", lambda _: '<div class="h1 text-center">-15.25</div>')
    assert weekly.fetch_naaim() is None


def test_naaim_out_of_range_is_rejected(monkeypatch):
    monkeypatch.setattr(weekly, "http_get", lambda _: '<div class="h1 text-center">250.0</div>')
    assert weekly.fetch_naaim() is None
