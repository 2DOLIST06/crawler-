from abc import ABC, abstractmethod

from crawler.models import FetchResult


class BaseFetcher(ABC):
    @abstractmethod
    def fetch(self, url: str) -> FetchResult:
        raise NotImplementedError

    def close(self) -> None:
        return None
