from playwright.sync_api import sync_playwright

from crawler.fetchers.base import BaseFetcher
from crawler.models import FetchResult


class BrowserFetcher(BaseFetcher):
    def __init__(self, timeout: float, user_agent: str):
        self.timeout = timeout
        self.play = sync_playwright().start()
        self.browser = self.play.chromium.launch(headless=True)
        self.context = self.browser.new_context(user_agent=user_agent)

    def fetch(self, url: str) -> FetchResult:
        page = self.context.new_page()
        try:
            response = page.goto(url, wait_until="networkidle", timeout=int(self.timeout * 1000))
            html = page.content()
            status_code = response.status if response else None
            final_url = page.url
            return FetchResult(
                requested_url=url,
                final_url=final_url,
                status_code=status_code,
                content_type=response.header_value("content-type") if response else None,
                html=html,
            )
        except Exception as exc:
            return FetchResult(requested_url=url, final_url=url, error=str(exc))
        finally:
            page.close()

    def close(self) -> None:
        self.context.close()
        self.browser.close()
        self.play.stop()
