from playwright.async_api import async_playwright
from .base import BaseFetcher, FetchResult
class BrowserFetcher(BaseFetcher):
    async def fetch(self,url:str)->FetchResult:
        async with async_playwright() as p:
            b=await p.chromium.launch()
            pg=await b.new_page()
            r=await pg.goto(url, wait_until='domcontentloaded')
            text=await pg.content(); final=pg.url
            await b.close()
        return FetchResult(requested_url=url,final_url=final,status_code=r.status if r else 0,content_type='text/html',text=text,error=None,redirect_chain=[])
