from crawler_app.crawler.analyzers.slugs import SlugAnalyzer


def test_slug_helicoptere_not_suspicious():
    assert SlugAnalyzer().analyze_page({'final_url':'https://a.com/categorie/helicoptere'}) == []


def test_slug_helicopter_suspicious():
    assert SlugAnalyzer().analyze_page({'final_url':'https://a.com/categorie/helicopter'})


def test_slug_tandem_skydiving_not_suspicious_without_exact_segment():
    assert SlugAnalyzer().analyze_page({'final_url':'https://a.com/activities/tandem-skydiving-near-los-angeles'}) == []


def test_slug_skydiving_suspicious_when_exact_segment():
    assert SlugAnalyzer().analyze_page({'final_url':'https://a.com/categorie/skydiving'})
