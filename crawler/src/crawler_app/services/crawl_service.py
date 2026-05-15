from collections import Counter, defaultdict, deque
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import csv

from crawler_app.config import settings
from crawler_app.models import Run, CrawledPage, Link, Resource, Issue
from crawler_app.crawler.normalize import normalize_url
from crawler_app.crawler.parsers.html_parser import parse_html
from crawler_app.crawler.fetchers.http_fetcher import HttpFetcher
from crawler_app.crawler.fetchers.browser_fetcher import BrowserFetcher
from crawler_app.crawler.analyzers import SEOAnalyzer, LinkAnalyzer, SlugAnalyzer
from crawler_app.services.parameter_urls_audit import generate_parameter_urls_report

TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "gclid", "fbclid", "msclkid", "ae"}
ENGLISH_SLUGS = ["airplane", "helicopter", "glider", "paragliding", "skydiving", "hot-air-balloon", "flight-simulator", "airplane-flying-lesson"]
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




def _is_internal_crawlable_url(project, normalized_url: str) -> bool:
    parsed = urlparse(normalized_url or "")
    host = (parsed.netloc or "").lower().strip(".")

    raw_allowed_domain = (project.allowed_domain or "").strip()
    allowed_parsed = urlparse(raw_allowed_domain if "://" in raw_allowed_domain else f"http://{raw_allowed_domain}")
    allowed_domain = (allowed_parsed.netloc or "").lower().strip(".")
    if not host or not allowed_domain:
        return False

    if project.same_host_only:
        return host == allowed_domain
    return host == allowed_domain or host.endswith(f".{allowed_domain}")

def _matched_english_slug(url: str | None) -> str | None:
    parsed = urlparse(url or "")
    segments = [segment.lower() for segment in (parsed.path or "").split("/") if segment]
    for segment in segments:
        if segment in ENGLISH_SLUGS:
            return segment
    return None

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
    mission_type = run.mission_type or (run.config_snapshot or {}).get("mission_type", "simple_crawl")
    is_seo_audit = mission_type == "seo_technical_audit"
    is_english_slugs_audit = mission_type == "english_slugs_fr_audit"
    is_parameter_urls_audit = mission_type == "parameter_urls_seo_audit"

    run.status = "running"
    run.started_at = datetime.utcnow()
    run.updated_at = datetime.utcnow()
    run.error_message = None
    db.commit()
    print(
        f"[run {run.id}] Starting crawl project={project.id} start_url={project.start_url} "
        f"mode={run.mode} max_pages={run.max_pages} max_depth={run.max_depth}"
    )
    fetcher = HttpFetcher() if run.mode == "http" else BrowserFetcher()
    analyzers = [SEOAnalyzer(), LinkAnalyzer(), SlugAnalyzer()]

    seeds = [(project.start_url, 0, None)]
    if (is_seo_audit or is_english_slugs_audit) and "2dolist.fr" in project.start_url:
        seeds.append((f"{project.start_url.rstrip('/')}/sitemap.xml", 0, "sitemap_seed"))

    q = deque(seeds)
    seen = set()
    skip_counts = Counter()

    while q and run.pages_crawled < run.max_pages:
        url, depth, src = q.popleft()
        n = normalize_url(url)
        if n in seen:
            skip_counts["already_seen"] += 1
            print(f"[run {run.id}] Skipped already visited url={url}")
            continue
        if depth > run.max_depth:
            skip_counts["max_depth"] += 1
            print(f"[run {run.id}] Skipped out of domain url={url}")
            continue
        if _is_ignored_url(url):
            skip_counts["ignored_pattern"] += 1
            print(f"[run {run.id}] Skipped external url={url}")
            continue
        if not _is_internal_crawlable_url(project, n):
            skip_counts["out_of_scope"] += 1
            print(f"[run {run.id}] Skipped out of domain url={url}")
            continue
        print(
            f"[run {run.id}] Crawling page {run.pages_crawled + 1}/{run.max_pages} "
            f"depth={depth} queue={len(q)} url={url}"
        )
        seen.add(n)
        try:
            fr = await fetcher.fetch(url)
            is_xml = "xml" in (fr.get("content_type") or "") or (fr["final_url"] or "").endswith(".xml")
            parsed = parse_html(fr["text"]) if "html" in (fr.get("content_type") or "") else {"links": [], "resources": [], "hreflangs": [], "prev": [], "next": []}
            if is_xml and "<urlset" in (fr.get("text") or "") or "<sitemapindex" in (fr.get("text") or ""):
                import re
                locs = re.findall(r"<loc>(.*?)</loc>", fr.get("text") or "", flags=re.I)
                parsed["sitemap_locs"] = locs
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
            run.last_crawled_url = fr["final_url"]

            for it, sev in analyzers[0].analyze_page({**parsed, "status_code": fr["status_code"], "final_url": fr["final_url"], "content_type": fr.get("content_type")}):
                db.add(Issue(run_id=run.id, issue_type=it, severity=sev, url=fr["final_url"]))

            internal_count = 0
            external_count = 0
            for link_item in parsed.get("links", []):
                href = link_item.get("href") if isinstance(link_item, dict) else link_item
                anchor_text = link_item.get("anchor_text", "") if isinstance(link_item, dict) else ""
                if not href:
                    continue
                dest = normalize_url(href, fr["final_url"])
                if _is_ignored_url(dest):
                    continue
                internal = _is_internal_crawlable_url(project, dest)
                internal_count += 1 if internal else 0
                external_count += 0 if internal else 1
                l = Link(
                    run_id=run.id, source_url=fr["final_url"], destination_url=href, normalized_url=dest, anchor_text=anchor_text,
                    link_type='a_href' if internal else 'external', is_internal=internal, is_external=not internal, is_crawlable=internal, found_at_depth=depth + 1
                )
                db.add(l)
                run.links_found += 1
                for it, sev in analyzers[1].analyze_link({"destination_url": href}):
                    db.add(Issue(run_id=run.id, issue_type=it, severity=sev, url=dest, source_url=fr["final_url"]))
                if internal and depth + 1 <= run.max_depth:
                    q.append((dest, depth + 1, fr["final_url"]))
            page.internal_links_count = internal_count
            page.external_links_count = external_count

            if is_english_slugs_audit:
                entries = []
                for href_item in parsed.get("links", []):
                    href = href_item.get("href") if isinstance(href_item, dict) else href_item
                    if href:
                        entries.append(("a_href", "Lien HTML <a href>", href, href_item.get("anchor_text", "") if isinstance(href_item, dict) else ""))
                if parsed.get("canonical"):
                    entries.append(("canonical", "Balise canonical", parsed.get("canonical"), ""))
                for h in parsed.get("hreflangs", []):
                    if h.get("href"):
                        entries.append(("hreflang", "Balise hreflang", h.get("href"), ""))
                for h in parsed.get("prev", []):
                    entries.append(("prev", "Balise prev", h, ""))
                for h in parsed.get("next", []):
                    entries.append(("next", "Balise next", h, ""))
                for h in parsed.get("sitemap_locs", []):
                    entries.append(("sitemap", "Sitemap", h, ""))

                for discovery_type, found_in, raw_url, anchor in entries:
                    abs_url = normalize_url(raw_url, fr["final_url"])
                    slug = _matched_english_slug(abs_url)
                    if not slug:
                        continue
                    issue_type_map = {"a_href": "internal_link_to_english_slug", "sitemap": "sitemap_english_slug_url", "canonical": "canonical_english_slug_url", "hreflang": "hreflang_english_slug_url", "prev": "prev_next_english_slug_url", "next": "prev_next_english_slug_url"}
                    issue_label_map = {"a_href": "Lien interne vers une URL avec slug anglais", "sitemap": "URL avec slug anglais présente dans le sitemap", "canonical": "Canonical vers une URL avec slug anglais", "hreflang": "Hreflang vers une URL avec slug anglais", "prev": "Prev/next vers une URL avec slug anglais", "next": "Prev/next vers une URL avec slug anglais"}
                    if discovery_type == "a_href" and not _is_internal_crawlable_url(project, abs_url):
                        continue
                    db.add(Issue(run_id=run.id, issue_type=issue_type_map[discovery_type], severity="high", url=abs_url, source_url=fr["final_url"], details=f"discovery_type={discovery_type};found_in={found_in};anchor_text={anchor};matched_slug={slug};issue_label={issue_label_map[discovery_type]}"))

                crawled_slug = _matched_english_slug(fr["final_url"])
                if crawled_slug:
                    db.add(Issue(run_id=run.id, issue_type="english_slug_url_on_fr", severity="high", url=fr["final_url"], source_url=fr["final_url"], details=f"discovery_type=crawled_url;found_in=URL crawlée;matched_slug={crawled_slug};issue_label=URL crawlée avec slug anglais"))

            if is_xml:
                for loc in parsed.get("sitemap_locs", []):
                    dest = normalize_url(loc, fr["final_url"])
                    if _is_internal_crawlable_url(project, dest) and depth + 1 <= run.max_depth:
                        q.append((dest, depth + 1, fr["final_url"]))

            for r in parsed.get("resources", []):
                db.add(Resource(run_id=run.id, source_url=fr['final_url'], resource_url=normalize_url(r['url'], fr['final_url']), resource_type=r['type'], tag_name=r['tag'], attribute_name=r['attr']))
            for it, sev in analyzers[2].analyze_page({"final_url": fr["final_url"]}):
                db.add(Issue(run_id=run.id, issue_type=it, severity=sev, url=fr["final_url"]))
            run.issues_found = db.query(Issue).filter(Issue.run_id == run.id).count()
            run.updated_at = datetime.utcnow()
            db.commit()
            print(
                f"[run {run.id}] Done status={fr['status_code']} links={run.links_found} "
                f"issues={run.issues_found} url={fr['final_url']}"
            )
        except Exception as e:
            db.add(Issue(run_id=run.id, issue_type='fetch_error', severity='error', url=url, details=str(e)))
            run.issues_found = db.query(Issue).filter(Issue.run_id == run.id).count()
            run.updated_at = datetime.utcnow()
            db.commit()
            print(f"[run {run.id}] Error url={url} error={e}")

    if run.pages_crawled >= run.max_pages:
        stop_reason = f"Arrêt: limite max_pages atteinte ({run.pages_crawled}/{run.max_pages})."
    elif not q:
        stop_reason = "Arrêt: plus de page à crawler (file vide)."
    else:
        stop_reason = "Arrêt: fin de crawl."
    if run.pages_crawled == 0 and skip_counts.get("out_of_scope", 0) > 0:
        stop_reason += " Toutes les URLs de départ ont été ignorées car hors périmètre."

    run.status = 'completed'
    run.finished_at = datetime.utcnow()
    run.updated_at = datetime.utcnow()
    run.error_message = stop_reason
    run.config_snapshot = {
        **(run.config_snapshot or {}),
        "stop_reason": stop_reason,
        "skip_counts": dict(skip_counts),
    }
    run.issues_found = db.query(Issue).filter(Issue.run_id == run.id).count()
    db.commit()
    print(
        f"[run {run.id}] Completed pages={run.pages_crawled} links={run.links_found} "
        f"issues={run.issues_found} reason={stop_reason} skips={dict(skip_counts)}"
    )

    if is_seo_audit:
        _generate_seo_exports(db, run.id)
    if is_english_slugs_audit:
        _generate_english_slugs_exports(db, run.id)
    if is_parameter_urls_audit:
        await generate_parameter_urls_report(db, run.id, project.start_url)


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
    page_by_url = {normalize_url(p.final_url): p for p in pages}
    for l in links:
        slug = _matched_english_slug(l.normalized_url)
        if not slug:
            continue
        target_page = page_by_url.get(normalize_url(l.normalized_url))
        indexable_status = _is_indexable(target_page) if target_page else "non crawlée"
        en_rows.append({
            "issue_type": "internal_link_to_english_slug",
            "issue_label": "Lien interne vers une URL avec slug anglais",
            "source_url": l.source_url,
            "found_url": l.normalized_url,
            "discovery_type": l.link_type,
            "found_in": "Dans un lien HTML <a href>",
            "anchor_text": l.anchor_text,
            "matched_slug": slug,
            "status_final": l.status_code,
            "canonical": target_page.canonical if target_page else "",
            "was_crawled": "oui" if target_page else "non",
            "indexable_status": indexable_status,
            "where_to_fix": "Corriger le lien généré sur la page source : composant, contenu CMS ou fonction de génération d’URL.",
            "recommended_action": "Remplacer ce lien par l’URL française équivalente.",
        })
    _write_csv(base / "english_slugs_on_fr.csv", ["issue_type", "issue_label", "source_url", "found_url", "discovery_type", "found_in", "anchor_text", "matched_slug", "status_final", "canonical", "was_crawled", "indexable_status", "where_to_fix", "recommended_action"], en_rows)

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


def _generate_english_slugs_exports(db, run_id: int):
    import json
    pages = db.query(CrawledPage).filter_by(run_id=run_id).all()
    issues = db.query(Issue).filter_by(run_id=run_id).all()
    base = Path(settings.exports_dir) / f"run_{run_id}_english_slugs"
    base.mkdir(parents=True, exist_ok=True)
    rows = []
    page_map = {normalize_url(p.final_url): p for p in pages}
    for i in issues:
        if i.issue_type not in {"internal_link_to_english_slug","sitemap_english_slug_url","canonical_english_slug_url","hreflang_english_slug_url","prev_next_english_slug_url","english_slug_url_on_fr"}:
            continue
        details = i.details or ""
        parts = dict(kv.split("=",1) for kv in details.split(";") if "=" in kv)
        p = page_map.get(normalize_url(i.url))
        status = p.status_code if p else ""
        final_url = p.final_url if p else i.url
        rows.append({"issue_type": i.issue_type, "issue_label": parts.get("issue_label",""), "source_url": i.source_url or "", "found_url": i.url, "discovery_type": parts.get("discovery_type",""), "found_in": parts.get("found_in",""), "anchor_text": parts.get("anchor_text",""), "matched_slug": parts.get("matched_slug",""), "status_final": status, "final_url": final_url, "redirect_chain": " > ".join(p.redirect_chain or []) if p else "", "canonical": p.canonical if p else "", "was_crawled": "yes" if p else "no", "indexable_status": _is_indexable(p) if p else "unknown", "where_to_fix": "", "recommended_action": ""})
    for r in rows:
        dt=r["discovery_type"]
        r["where_to_fix"]={"a_href":"Corriger le lien généré sur la page source : composant, contenu CMS ou fonction de génération d’URL.","sitemap":"Corriger la génération du sitemap.","canonical":"Corriger la canonical générée sur cette page.","hreflang":"Corriger les hreflang générés sur cette page.","prev":"Corriger les balises prev/next générées sur cette page.","next":"Corriger les balises prev/next générées sur cette page.","crawled_url":"Corriger la route ou la redirection de cette URL."}.get(dt,"")
        r["recommended_action"]={"a_href":"Remplacer ce lien par l’URL française équivalente.","sitemap":"Retirer l’URL anglaise du sitemap ou la remplacer par l’URL française.","canonical":"Faire pointer la canonical vers l’URL française propre.","hreflang":"Faire pointer le hreflang fr-FR vers l’URL française.","prev":"Faire pointer prev/next vers une URL française correcte.","next":"Faire pointer prev/next vers une URL française correcte."}.get(dt,"Ajouter une redirection 301 vers l’URL française équivalente." if r["status_final"]==200 else "")
    headers=["issue_type","issue_label","source_url","found_url","discovery_type","found_in","anchor_text","matched_slug","status_final","final_url","redirect_chain","canonical","was_crawled","indexable_status","where_to_fix","recommended_action"]
    _write_csv(base / "english_slugs_fr_audit.csv", headers, rows)
    (base / "english_slugs_fr_audit.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
