import httpx

from crawler.fetchers.base import BaseFetcher
from crawler.models import FetchResult


class HttpFetcher(BaseFetcher):
    def __init__(self, timeout: float, user_agent: str):
        self.client = httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": user_agent})

    def fetch(self, url: str) -> FetchResult:
        try:
            resp = self.client.get(url)
            return FetchResult(
                requested_url=url,
                final_url=str(resp.url),
                status_code=resp.status_code,
                content_type=resp.headers.get("content-type"),
                html=resp.text,
                redirect_chain=[str(r.url) for r in resp.history],
            )
        except Exception as exc:
            return FetchResult(requested_url=url, final_url=url, error=str(exc))

    def close(self) -> None:
        self.client.close()
