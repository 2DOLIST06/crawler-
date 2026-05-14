from crawler.models import IssueRecord, LinkRecord


def analyze_links(links: list[LinkRecord]) -> list[IssueRecord]:
    issues = []
    for l in links:
        if not l.destination_url:
            issues.append(IssueRecord(issue_type="empty_link", severity="low", url=l.source_url, source_url=l.source_url, details="Lien vide"))
        if l.link_type == "internal" and l.status_code:
            if l.status_code == 404:
                issues.append(IssueRecord(issue_type="internal_404", severity="high", url=l.normalized_url or l.destination_url, source_url=l.source_url, details="Lien interne 404"))
            elif l.status_code >= 500:
                issues.append(IssueRecord(issue_type="internal_500", severity="high", url=l.normalized_url or l.destination_url, source_url=l.source_url, details="Lien interne 500"))
            elif 300 <= l.status_code < 400:
                issues.append(IssueRecord(issue_type="internal_redirect", severity="medium", url=l.normalized_url or l.destination_url, source_url=l.source_url, details="Lien interne redirigé"))
    return issues
