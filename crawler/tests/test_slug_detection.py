from crawler_app.crawler.analyzers.slugs import SlugAnalyzer

def test_slug():
    assert SlugAnalyzer().analyze_page({'final_url':'https://a.com/booking'})
