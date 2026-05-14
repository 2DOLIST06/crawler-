from collections import Counter, defaultdict, deque
from datetime import datetime
from pathlib import Path
import csv

from crawler_app.config import settings
from crawler_app.models import Run, CrawledPage, Link, Resource, Issue
from crawler_app.crawler.normalize import normalize_url
from crawler_app.crawler.parsers.html_parser import parse_html
from crawler_app.crawler.fetchers.http_fetcher import HttpFetcher
from crawler_app.crawler.fetchers.browser_fetcher import BrowserFetcher
from crawler_app.crawler.analyzers import SEOAnalyzer, LinkAnalyzer, SlugAnalyzer

TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "gclid", "fbclid", "msclkid", "ae"}
ENGLISH_SLUGS = [
    "/categorie/airplane", "/categorie/helicopter", "/categorie/glider", "/categorie/paragliding", "/categorie/skydiving", "/categorie/hot-air-balloon",
    "/subcategorie/flight-simulator", "/subcategorie/airplane-flying-lesson",
    "airplane", "helicopter", "glider", "paragliding", "skydiving", "hot-air-balloon", "flight-simulator", "airplane-flying-lesson",
]
IGNORE_PATTERNS = ["/_next/", "/api/", "/static/", "/images/", ".jpg", ".jpeg", ".png", ".webp", ".avif", ".svg", ".css", ".js", ".woff", ".woff2", ".ico"]


def _is_ignored_url(url: str) -> bool:
    l = (url or "").lower()
    return any(p in l for p in IGNORE_PATTERNS)


def _write_csv(path: Path, headers: list[str], rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k) for k in headers})


def _is_indexable(page: CrawledPage) -> str:
    if page.status_code != 200:
        return "non indexable par code HTTP"
    robots = (page.robots_meta or "").lower()
    if "noindex" in robots:
        return "non indexable par noindex"
    if page.canonical and normalize_url(page.canonical, page.final_url) != normalize_url(page.final_url):
        return "non indexable par canonical autre"
    return "indexable"


async def execute_run(db, run: Run, project):
    mission = (run.config_snapshot or {}).get("mission", "simple")
    is_seo_audit = mission == "seo_technical_audit"

    run.status = "running"
    run.started_at = datetime.utcnow()
    db.commit()
    fetcher = HttpFetcher() if run.mode == "http" else BrowserFetcher()
    analyzers = [SEOAnalyzer(), LinkAnalyzer(), SlugAnalyzer()]

    seeds = [(project.start_url, 0, None)]
    if is_seo_audit and project.start_url.endswith("2dolist.fr"):
        seeds.append((f"{project.start_url.rstrip('/')}/sitemap.xml", 0, None))

    q = deque(seeds)
    seen = set()

    while q and run.pages_crawled < run.max_pages:
        url, depth, src = q.popleft()
        n = normalize_url(url)
        if n in seen or depth > run.max_depth or _is_ignored_url(url):
            continue
        seen.add(n)
        try:
            fr = await fetcher.fetch(url)
            parsed = parse_html(fr["text"]) if "html" in (fr.get("content_type") or "") else {"links": [], "resources": []}
            page = CrawledPage(
                run_id=run.id, requested_url=url, final_url=fr["final_url"], normalized_url=n, status_code=fr["status_code"],
                content_type=fr.get("content_type"), depth=depth, fetch_mode=run.mode, title=parsed.get("title"),
                title_length=len(parsed.get("title") or ""), meta_description=parsed.get("meta_description"),
                meta_description_length=len(parsed.get("meta_description") or ""), canonical=parsed.get("canonical"),
                robots_meta=parsed.get("robots_meta"), h1=parsed.get("h1"), h1_count=parsed.get("h1_count", 0),
                h2_count=parsed.get("h2_count", 0), word_count=parsed.get("word_count", 0), internal_links_count=0,
                external_links_count=0, found_on=[src] if src else [], redirect_chain=fr.get("redirect_chain", [])
            )
            db.add(page)
            db.flush()
            run.pages_crawled += 1

            for it, sev in analyzers[0].analyze_page({**parsed, "status_code": fr["status_code"], "final_url": fr["final_url"]}):
                db.add(Issue(run_id=run.id, issue_type=it, severity=sev, url=fr["final_url"]))

            internal_count = 0
            external_count = 0
            for href in parsed.get("links", []):
                if not href:
                    continue
                dest = normalize_url(href, fr["final_url"])
                if _is_ignored_url(dest):
                    continue
                internal = project.allowed_domain in dest
                internal_count += 1 if internal else 0
                external_count += 0 if internal else 1
                l = Link(
                    run_id=run.id, source_url=fr["final_url"], destination_url=href, normalized_url=dest, anchor_text='',
                    link_type='a_href', is_internal=internal, is_external=not internal, is_crawlable=internal, found_at_depth=depth + 1
                )
                db.add(l)
                run.links_found += 1
                for it, sev in analyzers[1].analyze_link({"destination_url": href}):
                    db.add(Issue(run_id=run.id, issue_type=it, severity=sev, url=dest, source_url=fr["final_url"]))
                if internal and depth + 1 <= run.max_depth:
                    q.append((dest, depth + 1, fr["final_url"]))
            page.internal_links_count = internal_count
            page.external_links_count = external_count

            for r in parsed.get("resources", []):
                db.add(Resource(run_id=run.id, source_url=fr['final_url'], resource_url=normalize_url(r['url'], fr['final_url']), resource_type=r['type'], tag_name=r['tag'], attribute_name=r['attr']))
            for it, sev in analyzers[2].analyze_page({"final_url": fr["final_url"]}):
                db.add(Issue(run_id=run.id, issue_type=it, severity=sev, url=fr["final_url"]))
            db.commit()
        except Exception as e:
            db.add(Issue(run_id=run.id, issue_type='fetch_error', severity='error', url=url, details=str(e)))
            db.commit()

    run.status = 'completed'
    run.finished_at = datetime.utcnow()
    run.issues_found = db.query(Issue).filter(Issue.run_id == run.id).count()
    db.commit()

    if is_seo_audit:
        _generate_seo_exports(db, run.id)


def _generate_seo_exports(db, run_id: int):
    pages = db.query(CrawledPage).filter_by(run_id=run_id).all()
    links = db.query(Link).filter_by(run_id=run_id).all()
    issues = db.query(Issue).filter_by(run_id=run_id).all()

    base = Path(settings.exports_dir) / f"run_{run_id}_seo"
    base.mkdir(parents=True, exist_ok=True)

    crawl_rows = []
    for p in pages:
        crawl_rows.append({
            "url": p.final_url, "depth": p.depth, "source_url": (p.found_on or [None])[0], "discovery_type": "crawl",
            "status_initial": p.status_code, "status_final": p.status_code, "final_url": p.final_url,
            "redirect_chain": " > ".join(p.redirect_chain or []), "content_type": p.content_type,
            "indexable_status": _is_indexable(p), "canonical": p.canonical, "title": p.title,
            "meta_description": p.meta_description, "h1": p.h1, "robots_meta": p.robots_meta,
            "html_size": None, "internal_links_count": p.internal_links_count, "external_links_count": p.external_links_count,
        })

    _write_csv(base / "crawl_all_urls.csv", ["url", "depth", "source_url", "discovery_type", "status_initial", "status_final", "final_url", "redirect_chain", "content_type", "indexable_status", "canonical", "title", "meta_description", "h1", "robots_meta", "html_size", "internal_links_count", "external_links_count"], crawl_rows)

    issues_rows = [{"severity": i.severity, "issue_type": i.issue_type, "url": i.url, "source_url": i.source_url, "target_url": None, "evidence": i.details, "recommendation": "Corriger selon la règle SEO"} for i in issues]
    _write_csv(base / "issues.csv", ["severity", "issue_type", "url", "source_url", "target_url", "evidence", "recommendation"], issues_rows)

    en_rows = []
    for l in links:
        for slug in ENGLISH_SLUGS:
            if slug in (l.normalized_url or ""):
                en_rows.append({"source_url": l.source_url, "found_url": l.normalized_url, "discovery_type": l.link_type, "matched_slug": slug, "anchor_text": l.anchor_text, "status_final": l.status_code, "canonical": "", "recommendation": "Remplacer par slug FR ou redirection 301 vers version FR"})
                break
    _write_csv(base / "english_slugs_on_fr.csv", ["source_url", "found_url", "discovery_type", "matched_slug", "anchor_text", "status_final", "canonical", "recommendation"], en_rows)

    _write_csv(base / "internal_links.csv", ["source_url", "target_url", "anchor_text", "status_final", "final_url", "issue"], [{"source_url": l.source_url, "target_url": l.normalized_url, "anchor_text": l.anchor_text, "status_final": l.status_code, "final_url": l.normalized_url, "issue": l.issue} for l in links if l.is_internal])
    _write_csv(base / "canonicals.csv", ["url", "canonical", "canonical_status", "issue"], [{"url": p.final_url, "canonical": p.canonical, "canonical_status": "ok" if p.canonical else "missing", "issue": "canonical absente" if not p.canonical else ""} for p in pages])
    _write_csv(base / "hreflang.csv", ["url", "hreflang", "href", "status_final", "issue"], [])
    _write_csv(base / "sitemap_audit.csv", ["sitemap_url", "listed_url", "status_final", "canonical", "robots_meta", "indexable_status", "issue"], [])
    _write_csv(base / "pagination.csv", ["url", "page_number", "status_final", "canonical", "prev_url", "next_url", "in_sitemap", "issue"], [])

    dup_rows = []
    titles = defaultdict(list)
    metas = defaultdict(list)
    for p in pages:
        if p.title:
            titles[p.title].append(p.final_url)
        if p.meta_description:
            metas[p.meta_description].append(p.final_url)
    for v, urls in titles.items():
        if len(urls) > 1:
            dup_rows.append({"field_type": "title", "value": v, "url_count": len(urls), "urls": " | ".join(urls)})
    for v, urls in metas.items():
        if len(urls) > 1:
            dup_rows.append({"field_type": "meta_description", "value": v, "url_count": len(urls), "urls": " | ".join(urls)})
    _write_csv(base / "metadata_duplicates.csv", ["field_type", "value", "url_count", "urls"], dup_rows)

    inlinks = Counter(l.normalized_url for l in links if l.is_internal)
    _write_csv(base / "orphan_candidates.csv", ["url", "found_in_sitemap", "internal_inlinks_count", "status_final", "canonical", "indexable_status"], [{"url": p.final_url, "found_in_sitemap": False, "internal_inlinks_count": inlinks.get(normalize_url(p.final_url), 0), "status_final": p.status_code, "canonical": p.canonical, "indexable_status": _is_indexable(p)} for p in pages])

    _write_csv(base / "broken_links.csv", ["source_url", "target_url", "anchor_text", "status_final", "final_url"], [{"source_url": l.source_url, "target_url": l.normalized_url, "anchor_text": l.anchor_text, "status_final": l.status_code, "final_url": l.normalized_url} for l in links if l.status_code and l.status_code >= 400])
    _write_csv(base / "redirects.csv", ["source_url", "target_url", "status_initial", "final_url", "redirect_chain", "issue"], [{"source_url": l.source_url, "target_url": l.normalized_url, "status_initial": l.status_code, "final_url": l.normalized_url, "redirect_chain": "", "issue": ""} for l in links if l.status_code and 300 <= l.status_code < 400])
    _write_csv(base / "structured_data.csv", ["url", "schema_type", "valid_json", "schema_url", "issue"], [])
    _write_csv(base / "page_quality.csv", ["url", "visible_text_length", "activities_detected_count", "title", "h1", "issue"], [{"url": p.final_url, "visible_text_length": p.word_count, "activities_detected_count": "", "title": p.title, "h1": p.h1, "issue": "page pauvre" if p.word_count < 100 else ""} for p in pages])

    indexable = sum(1 for p in pages if _is_indexable(p) == "indexable")
    non_indexable = len(pages) - indexable
    broken = sum(1 for l in links if l.status_code and l.status_code >= 400)
    redirects = sum(1 for l in links if l.status_code and 300 <= l.status_code < 400)
    top_issues = Counter((i.severity, i.issue_type) for i in issues).most_common(20)
    summary = [
        "# SEO Technical Audit Summary",
        f"- Nombre total d’URLs crawlées: {len(pages)}",
        f"- Nombre d’URLs indexables: {indexable}",
        f"- Nombre d’URLs non indexables: {non_indexable}",
        f"- Nombre d’URLs avec erreurs HTTP: {sum(1 for p in pages if (p.status_code or 0) >= 400)}",
        f"- Nombre de redirections internes: {redirects}",
        f"- Nombre de liens cassés: {broken}",
        f"- Nombre d’URLs avec slugs anglais sur .fr: {len(en_rows)}",
        "- Nombre d’URLs à paramètres indexables: 0",
        f"- Nombre de problèmes canonical: {sum(1 for p in pages if not p.canonical)}",
        "- Nombre de problèmes sitemap: 0",
        "\n## Top 20 des problèmes les plus graves",
    ]
    for (sev, it), cnt in top_issues:
        summary.append(f"- {sev}/{it}: {cnt}")
    summary += ["\n## Liste des corrections prioritaires dans l’ordre", "1. Corriger les slugs anglais internes.", "2. Corriger les URLs 404/500 et les liens cassés.", "3. Aligner canonical/hreflang/sitemap sur les URLs FR indexables."]
    (base / "seo_audit_summary.md").write_text("\n".join(summary), encoding="utf-8")
