import httpx
from .base import BaseFetcher, FetchResult
class HttpFetcher(BaseFetcher):
    async def fetch(self,url:str)->FetchResult:
        async with httpx.AsyncClient(follow_redirects=True,timeout=20) as c:
            r=await c.get(url)
        return FetchResult(requested_url=url,final_url=str(r.url),status_code=r.status_code,content_type=r.headers.get('content-type',''),text=r.text,error=None,redirect_chain=[str(h.url) for h in r.history])
