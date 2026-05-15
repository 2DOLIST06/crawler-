from crawler_app.crawler.normalize import normalize_url

def test_normalize():
    assert normalize_url('https://Example.com/a/')=='https://example.com/a'


def test_normalize_without_scheme_uses_https_and_host():
    assert normalize_url('www.example.com/a') == 'https://www.example.com/a'


def test_normalize_protocol_relative_url():
    assert normalize_url('//Example.com/b/') == 'https://example.com/b'
