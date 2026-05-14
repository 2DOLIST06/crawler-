from crawler.analysis.slugs import detect_suspicious_slugs
from crawler.models import LinkRecord, PageRecord


def test_slug_detection():
    page = PageRecord(requested_url="u", final_url="u", normalized_url="https://x.com/booking", status_code=200, content_type="text/html", depth=0, fetch_mode="http", title="t", title_length=1, meta_description="m", meta_description_length=1, canonical="", robots_meta="", h1_list=[], h1_count=0, h2_list=[], h2_count=0, hreflang_list=[], internal_links_count=0, external_links_count=0, resource_links_count=0, word_count=0, found_on=[], redirect_chain=[], error=None)
    link = LinkRecord(source_url="https://x.com", destination_url="https://x.com/activity", normalized_url="https://x.com/activity", anchor_text="a", link_type="internal", is_internal=True, is_external=False, is_crawlable=True, rel="", target="", found_at_depth=0)
    hits = detect_suspicious_slugs([page], [link], ["booking", "activity"])
    assert len(hits) >= 2
