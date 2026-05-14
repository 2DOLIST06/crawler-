from crawler.models import IssueRecord, PageRecord


def analyze_page_seo(page: PageRecord) -> list[IssueRecord]:
    issues = []
    def add(t,s,d): issues.append(IssueRecord(issue_type=t,severity=s,url=page.normalized_url,source_url=page.normalized_url,details=d))
    if not page.title: add("title_missing","high","Title manquant")
    elif page.title_length < 20: add("title_too_short","medium","Title trop court")
    elif page.title_length > 65: add("title_too_long","medium","Title trop long")
    if not page.meta_description: add("meta_description_missing","high","Meta description manquante")
    elif page.meta_description_length < 70: add("meta_description_too_short","low","Meta description trop courte")
    elif page.meta_description_length > 160: add("meta_description_too_long","low","Meta description trop longue")
    if not page.canonical: add("canonical_missing","medium","Canonical manquante")
    if "noindex" in page.robots_meta.lower(): add("robots_noindex","medium","Balise robots noindex")
    if page.h1_count == 0: add("h1_missing","medium","H1 manquant")
    if page.h1_count > 1: add("multiple_h1","low","Plusieurs H1")
    if page.status_code and page.status_code >= 400: add("http_error","high",f"Status {page.status_code}")
    if page.redirect_chain: add("redirection","low","URL redirigée")
    if page.content_type and "html" not in page.content_type.lower(): add("non_html","low","Contenu non HTML")
    return issues
