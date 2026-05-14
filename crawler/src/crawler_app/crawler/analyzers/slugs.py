from urllib.parse import urlparse
import re
from .base import BaseAnalyzer

SUSPECT=["airplane","helicopter","glider","paragliding","skydiving","hot-air-balloon","flight-simulator","airplane-flying-lesson","flying-lesson","activities","activity","gift","near","booking","voucher"]

class SlugAnalyzer(BaseAnalyzer):
    name="slugs"

    def __init__(self, words=None):
        self.words={w.lower() for w in (words or SUSPECT)}

    def _segments(self, url: str):
        parsed = urlparse(url or "")
        path = parsed.path or ""
        out = []
        for segment in path.split('/'):
            if not segment:
                continue
            tokens = [t for t in re.split(r"[^a-z0-9]+", segment.lower()) if t]
            if tokens:
                out.extend(tokens)
            else:
                out.append(segment.lower())
        return out

    def analyze_page(self, p):
        segments = self._segments((p.get("final_url") or ""))
        if any(seg in self.words for seg in segments):
            return [("suspicious_slug","warning")]
        return []
