from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from crawler_app.config import settings
from crawler_app.crawler.fetchers.http_fetcher import HttpFetcher
from crawler_app.crawler.normalize import normalize_url
from crawler_app.crawler.parsers.html_parser import parse_html
from crawler_app.models import CrawledPage, Link

TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"}
PAGINATION_PARAMS = {"page"}
FILTER_PARAMS = {"region", "department", "category", "subcategory"}
SORTING_DISPLAY_PARAMS = {"sort", "display", "view", "map"}
BOOKING_PARAMS = {"price", "date", "adults", "children", "gift"}


def classify_parameter(param: str) -> str:
    p = (param or "").lower()
    if p in TRACKING_PARAMS:
        return "tracking"
    if p in PAGINATION_PARAMS:
        return "pagination"
    if p in FILTER_PARAMS:
        return "filter"
    if p in SORTING_DISPLAY_PARAMS:
        return "sorting_display"
    if p in BOOKING_PARAMS:
        return "booking_or_availability"
    return "unknown"


def _strip_params(url: str, keys: set[str]) -> str:
    u = urlparse(url)
    qs = parse_qs(u.query, keep_blank_values=True)
    kept = {k: v for k, v in qs.items() if k not in keys}
    return normalize_url(urlunparse((u.scheme, u.netloc, u.path, "", urlencode(kept, doseq=True), "")))


def _has_param(url: str) -> bool:
    return "?" in (url or "")


async def generate_parameter_urls_report(db, run_id: int, domain: str, max_generated_parameter_tests: int = 200):
    pages = db.query(CrawledPage).filter_by(run_id=run_id).all()
    links = db.query(Link).filter_by(run_id=run_id).all()

    found_in = defaultdict(set)
    sitemap_sources = defaultdict(set)

    for p in pages:
        if _has_param(p.final_url):
            found_in[normalize_url(p.final_url)].add("crawled")
        if _has_param(p.canonical or ""):
            found_in[normalize_url(p.canonical, p.final_url)].add("canonical")
    for l in links:
        if _has_param(l.normalized_url):
            found_in[normalize_url(l.normalized_url)].add("html_link")
        if (l.source_url or "").endswith(".xml") and _has_param(l.normalized_url):
            found_in[normalize_url(l.normalized_url)].add("sitemap")
            sitemap_sources[normalize_url(l.normalized_url)].add(l.source_url)

    important_urls = [normalize_url(p.final_url) for p in pages if p.status_code == 200 and not _has_param(p.final_url)][:50]
    generated = []
    for u in important_urls:
        generated.extend([f"{u}?utm_source=test", f"{u}?fbclid=test", f"{u}?gclid=test", f"{u}?sort=price"])
        if any(seg in urlparse(u).path for seg in ["categorie", "department", "region"]):
            generated.append(f"{u}?page=2")
    for u in generated[:max_generated_parameter_tests]:
        found_in[normalize_url(u)].add("generated_test")

    fetcher = HttpFetcher()
    items = []
    try:
        for u, origins in found_in.items():
            fr = await fetcher.fetch(u)
            parsed_q = parse_qs(urlparse(u).query)
            params = sorted(parsed_q.keys())
            types = sorted({classify_parameter(p) for p in params})
            ptype = types[0] if len(types) == 1 else "mixed"
            parsed = parse_html(fr.get("text") or "") if "html" in (fr.get("content_type") or "") else {}
            canonical = normalize_url(parsed.get("canonical") or "", fr["final_url"]) if parsed.get("canonical") else None
            robots_meta = parsed.get("robots_meta") or ""
            in_sitemap = "sitemap" in origins
            verdict, severity, reason = "ok", "ok", "Conforme aux règles définies."

            if in_sitemap:
                verdict, severity, reason = "error", "error", "URL avec paramètres présente dans sitemap."
            elif "tracking" in types:
                clean = _strip_params(fr["final_url"], TRACKING_PARAMS)
                if canonical and canonical != clean:
                    verdict, severity, reason = "error", "error", "Tracking URL sans canonical vers URL propre."
                elif "noindex" in robots_meta.lower():
                    verdict, severity, reason = "warning", "warning", "Tracking URL en noindex; acceptable mais à surveiller."
            elif "pagination" in types:
                if canonical and "page=1" in canonical:
                    verdict, severity, reason = "warning", "warning", "Canonical paginée vers page 1."
                elif "index,follow" in robots_meta.lower() or robots_meta.strip() == "":
                    verdict, severity, reason = "warning", "warning", "Pagination indexable; noindex,follow recommandé."
            elif "sorting_display" in types or "booking_or_availability" in types:
                clean = _strip_params(fr["final_url"], SORTING_DISPLAY_PARAMS | BOOKING_PARAMS)
                if canonical == normalize_url(fr["final_url"]):
                    verdict, severity, reason = "warning", "warning", "Self canonical sur URL paramétrée."
                    if "index,follow" in robots_meta.lower() or robots_meta.strip() == "":
                        verdict, severity, reason = "error", "error", "Self canonical + index,follow sur URL paramétrée."
                elif canonical and canonical != clean:
                    verdict, severity, reason = "warning", "warning", "Canonical inattendue pour tri/affichage/réservation."
            elif "filter" in types:
                if not canonical:
                    verdict, severity, reason = "error", "error", "Canonical absente sur URL de filtre."
                elif canonical == normalize_url(fr["final_url"]):
                    verdict, severity, reason = "unknown", "warning", "URL propre équivalente non confirmée."
            elif "unknown" in types:
                verdict, severity, reason = "unknown", "warning", "Paramètre inconnu: audit manuel recommandé."

            items.append({
                "url": u,
                "final_url": fr.get("final_url"),
                "status": fr.get("status_code"),
                "parameter_type": ptype,
                "parameters": params,
                "found_in": sorted(origins),
                "in_sitemap": in_sitemap,
                "sitemaps": sorted(sitemap_sources.get(u, set())),
                "canonical": canonical,
                "robots_meta": robots_meta,
                "robots_txt_blocked": False,
                "verdict": verdict,
                "severity": severity,
                "reason": reason,
            })
    finally:
        fetcher.close()

    summary = {
        "tested_urls": len(items),
        "urls_with_parameters_found": len(found_in),
        "sitemap_parameter_urls": sum(1 for i in items if i["in_sitemap"]),
        "errors": sum(1 for i in items if i["severity"] == "error"),
        "warnings": sum(1 for i in items if i["severity"] == "warning"),
        "ok": sum(1 for i in items if i["severity"] == "ok"),
        "unknown": sum(1 for i in items if i["verdict"] == "unknown"),
    }

    payload = {"mission": "parameter_urls_seo_audit", "domain": domain, "summary": summary, "items": items}
    base = Path(settings.exports_dir) / f"run_{run_id}_parameter_urls"
    base.mkdir(parents=True, exist_ok=True)
    (base / "parameter_urls_seo_audit.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    headers = ["url", "final_url", "status", "parameter_type", "parameters", "found_in", "in_sitemap", "canonical", "robots_meta", "robots_txt_blocked", "verdict", "severity", "reason"]
    with (base / "parameter_urls_seo_audit.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for item in items:
            row = item.copy()
            row["parameters"] = ",".join(item["parameters"])
            row["found_in"] = ",".join(item["found_in"])
            w.writerow({k: row.get(k) for k in headers})

