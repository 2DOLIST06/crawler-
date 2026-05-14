from crawler_app.crawler.parsers.html_parser import parse_html

def test_parse_html():
    d=parse_html('<html><title>T</title><a href="/x">x</a><h1>A</h1></html>')
    assert d['title']=='T' and len(d['links'])==1
