from crawler_app.crawler.normalize import normalize_url

def test_normalize():
    assert normalize_url('https://Example.com/a/')=='https://example.com/a'
