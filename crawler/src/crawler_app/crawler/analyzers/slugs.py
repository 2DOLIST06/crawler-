from .base import BaseAnalyzer
SUSPECT=["airplane","helicopter","glider","paragliding","skydiving","hot-air-balloon","flight-simulator","airplane-flying-lesson","flying-lesson","activities","activity","gift","near","booking","voucher"]
class SlugAnalyzer(BaseAnalyzer):
    name="slugs"
    def __init__(self, words=None): self.words=words or SUSPECT
    def analyze_page(self, p):
        u=(p.get("final_url") or "").lower();return [("suspicious_slug","warning") for w in self.words if w in u]
