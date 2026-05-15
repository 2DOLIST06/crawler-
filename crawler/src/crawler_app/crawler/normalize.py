from urllib.parse import urljoin, urlparse, urlunparse


def _ensure_absolute_url(url: str) -> str:
    value = (url or "").strip()
    if not value:
        return value
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc:
        return value
    if value.startswith("//"):
        return f"https:{value}"
    return f"https://{value}"


def normalize_url(url: str, base_url: str | None = None) -> str:
    if base_url:
        url = urljoin(base_url, url)
    url = _ensure_absolute_url(url)
    p = urlparse(url)
    scheme = p.scheme or "https"
    netloc = p.netloc.lower()
    path = p.path or "/"
    return urlunparse((scheme, netloc, path.rstrip("/") or "/", "", p.query, ""))
