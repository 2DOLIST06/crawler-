from .base import BaseAnalyzer
class LinkAnalyzer(BaseAnalyzer):
    name="links"
    def analyze_link(self, l):
        issues=[]
        if not l.get("destination_url"): issues.append(("empty_link","warning"))
        if l.get("issue"): issues.append((l["issue"],"warning"))
        return issues
