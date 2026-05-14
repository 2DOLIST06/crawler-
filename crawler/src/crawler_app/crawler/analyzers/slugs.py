from urllib.parse import urlparse
from .base import BaseAnalyzer

SUSPECT = [
    "airplane",
    "helicopter",
    "glider",
    "paragliding",
    "skydiving",
    "hot-air-balloon",
    "flight-simulator",
    "airplane-flying-lesson",
]

class SlugAnalyzer(BaseAnalyzer):
    name="slugs"

    def __init__(self, words=None):
        self.words={w.lower() for w in (words or SUSPECT)}

    def _segments(self, url: str):
        parsed = urlparse(url or "")
        path = parsed.path or ""
        return [segment.lower() for segment in path.split('/') if segment]

    def analyze_page(self, p):
        segments = self._segments((p.get("final_url") or ""))
        if any(seg in self.words for seg in segments):
            return [("english_slug_url_on_fr","warning")]
        return []
