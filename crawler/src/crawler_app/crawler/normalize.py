from urllib.parse import urljoin, urlparse, urlunparse

def normalize_url(url: str, base_url: str | None = None) -> str:
    if base_url:
        url = urljoin(base_url, url)
    p = urlparse(url)
    scheme = p.scheme or "https"
    netloc = p.netloc.lower()
    path = p.path or "/"
    return urlunparse((scheme, netloc, path.rstrip("/") or "/", "", p.query, ""))
