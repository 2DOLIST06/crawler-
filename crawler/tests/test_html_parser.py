from crawler.parsers.html_parser import parse_html


def test_parse_links_and_title():
    html = "<html><head><title>X</title></head><body><a href='/a'>A</a></body></html>"
    data = parse_html(html, "https://example.com")
    assert data["title"] == "X"
    assert data["links"][0]["href"] == "/a"
