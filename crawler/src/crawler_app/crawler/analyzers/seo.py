from .base import BaseAnalyzer
class SEOAnalyzer(BaseAnalyzer):
    name="seo"
    def analyze_page(self, p):
        issues=[]
        url = (p.get("final_url") or "").lower()
        content_type = (p.get("content_type") or "").lower()
        is_xml = "xml" in content_type or url.endswith('.xml')
        if is_xml:
            if (p.get("status_code") or 0)>=400:
                issues.append(("http_error","error"))
            return issues
        if not p.get("title"): issues.append(("missing_title","warning"))
        if p.get("title") and len(p["title"])<20: issues.append(("title_too_short","info"))
        if p.get("title") and len(p["title"])>65: issues.append(("title_too_long","warning"))
        if not p.get("meta_description"): issues.append(("missing_meta_description","warning"))
        if not p.get("canonical"): issues.append(("missing_canonical","info"))
        if p.get("h1_count",0)==0: issues.append(("missing_h1","warning"))
        if p.get("h1_count",0)>1: issues.append(("multiple_h1","warning"))
        if (p.get("status_code") or 0)>=400: issues.append(("http_error","error"))
        return issues
