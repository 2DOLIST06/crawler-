from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

IGNORED_SCHEMES = {"mailto", "tel", "javascript", "data"}


def normalize_url(url: str, base_url: str | None = None, include_query_params: bool = False) -> str | None:
    candidate = urljoin(base_url, url) if base_url else url
    parsed = urlparse(candidate)
    if parsed.scheme and parsed.scheme.lower() in IGNORED_SCHEMES:
        return None
    if parsed.scheme not in {"http", "https", ""}:
        return None
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    query = ""
    if include_query_params and parsed.query:
        query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)))
    return urlunparse((scheme, netloc, path, "", query, ""))


def is_internal_url(url: str, allowed_domain: str, same_host_only: bool = False) -> bool:
    host = urlparse(url).netloc.lower()
    allowed = allowed_domain.lower()
    if same_host_only:
        return host == allowed
    return host == allowed or host.endswith(f".{allowed}")
