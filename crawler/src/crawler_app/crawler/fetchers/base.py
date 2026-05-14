class FetchResult(dict):
    pass
class BaseFetcher:
    async def fetch(self, url:str)->FetchResult: raise NotImplementedError
