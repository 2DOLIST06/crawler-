from crawler.models import IssueRecord, LinkRecord, PageRecord


def detect_suspicious_slugs(pages: list[PageRecord], links: list[LinkRecord], keywords: list[str]) -> list[dict]:
    out = []
    lowered = [k.lower() for k in keywords]
    def scan(text, typ, url, src="", anchor=""):
        ltext = (text or "").lower()
        for k in lowered:
            if k in ltext:
                out.append({"type": typ, "url": url, "source_url": src, "anchor_text": anchor, "matched_keyword": k, "details": f"Keyword '{k}' détecté"})
    for p in pages:
        scan(p.normalized_url, "visited_url", p.normalized_url)
        scan(p.canonical, "canonical", p.normalized_url)
        for h in p.hreflang_list: scan(h, "hreflang", p.normalized_url)
    for l in links:
        scan(l.destination_url, "internal_link", l.destination_url, l.source_url, l.anchor_text)
    return out
