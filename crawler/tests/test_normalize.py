from crawler.normalize import normalize_url


def test_normalize_relative_and_fragment():
    assert normalize_url("/a#frag", "https://Example.com") == "https://example.com/a"


def test_ignore_mailto():
    assert normalize_url("mailto:test@example.com") is None
