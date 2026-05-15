from types import SimpleNamespace

from crawler_app.services.crawl_service import _is_internal_crawlable_url, _is_excluded_conversion_url


def test_same_host_only_requires_exact_host():
    project = SimpleNamespace(allowed_domain="www.example.com", same_host_only=True)
    assert _is_internal_crawlable_url(project, "https://www.example.com/page")
    assert not _is_internal_crawlable_url(project, "https://blog.example.com/page")


def test_domain_mode_accepts_subdomains():
    project = SimpleNamespace(allowed_domain="example.com", same_host_only=False)
    assert _is_internal_crawlable_url(project, "https://example.com/page")
    assert _is_internal_crawlable_url(project, "https://www.example.com/page")


def test_allowed_domain_can_be_full_url_in_settings():
    project = SimpleNamespace(allowed_domain="https://example.com", same_host_only=False)
    assert _is_internal_crawlable_url(project, "https://shop.example.com/page")


def test_excluded_conversion_urls_are_detected():
    assert _is_excluded_conversion_url("https://example.com/order/checkout")
    assert _is_excluded_conversion_url("https://example.com/gift/card")
    assert not _is_excluded_conversion_url("https://example.com/blog/article")
