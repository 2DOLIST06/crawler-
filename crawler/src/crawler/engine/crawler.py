import time
from collections import deque

from crawler.analysis.links import analyze_links
from crawler.analysis.seo import analyze_page_seo
from crawler.analysis.slugs import detect_suspicious_slugs
from crawler.config import CrawlConfig
from crawler.models import LinkRecord, PageRecord
from crawler.normalize import is_internal_url, normalize_url
from crawler.parsers.html_parser import parse_html
from crawler.utils.logging import console
from crawler.utils.robots import can_fetch


class CrawlerEngine:
    def __init__(self, config: CrawlConfig, fetcher):
        self.config = config
        self.fetcher = fetcher

    def run(self) -> dict:
        q = deque([(self.config.start_url, 0, "")])
        visited = set()
        found_on: dict[str, set[str]] = {}
        pages: list[PageRecord] = []
        links: list[LinkRecord] = []
        resources = []
        issues = []
        while q and len(pages) < self.config.max_pages:
            url, depth, source = q.popleft()
            nurl = normalize_url(url, include_query_params=self.config.include_query_params)
            if not nurl or nurl in visited or depth > self.config.max_depth:
                continue
            if self.config.respect_robots and not can_fetch(nurl, self.config.user_agent):
                continue
            visited.add(nurl)
            found_on.setdefault(nurl, set()).add(source)
            console.log(f"Crawl {nurl} depth={depth} done={len(pages)} queue={len(q)}")
            result = self.fetcher.fetch(nurl)
            parsed = parse_html(result.html, nurl)
            page = PageRecord(requested_url=result.requested_url, final_url=result.final_url, normalized_url=nurl, status_code=result.status_code, content_type=result.content_type, depth=depth, fetch_mode=self.config.mode, title=parsed['title'], title_length=len(parsed['title']), meta_description=parsed['meta_description'], meta_description_length=len(parsed['meta_description']), canonical=parsed['canonical'], robots_meta=parsed['robots_meta'], h1_list=parsed['h1_list'], h1_count=len(parsed['h1_list']), h2_list=parsed['h2_list'], h2_count=len(parsed['h2_list']), hreflang_list=parsed['hreflang_list'], internal_links_count=0, external_links_count=0, resource_links_count=len(parsed['resources']), word_count=parsed['word_count'], found_on=sorted(x for x in found_on[nurl] if x), redirect_chain=result.redirect_chain, error=result.error)
            internal_count = external_count = 0
            for lk in parsed['links']:
                dest = lk['href']
                ndest = normalize_url(dest, base_url=nurl, include_query_params=self.config.include_query_params)
                if not dest:
                    link_type = "ignored"; is_internal=False; is_external=False; is_crawlable=False
                elif ndest and is_internal_url(ndest, self.config.allowed_domain, self.config.same_host_only):
                    link_type = "internal"; is_internal=True; is_external=False; is_crawlable=True; internal_count += 1
                    if ndest not in visited and depth + 1 <= self.config.max_depth:
                        q.append((ndest, depth + 1, nurl))
                elif ndest:
                    link_type = "external"; is_internal=False; is_external=True; is_crawlable=False; external_count += 1
                else:
                    link_type = "ignored"; is_internal=False; is_external=False; is_crawlable=False
                links.append(LinkRecord(source_url=nurl, destination_url=dest, normalized_url=ndest, anchor_text=lk['anchor_text'], link_type=link_type, is_internal=is_internal, is_external=is_external, is_crawlable=is_crawlable, rel=lk['rel'], target=lk['target'], found_at_depth=depth))
            page.internal_links_count = internal_count
            page.external_links_count = external_count
            pages.append(page)
            resources.extend(parsed['resources'])
            issues.extend(analyze_page_seo(page))
            if self.config.delay:
                time.sleep(self.config.delay)
        issues.extend(analyze_links(links))
        slug_hits = detect_suspicious_slugs(pages, links, self.config.suspect_keywords)
        stats = {"pages": len(pages), "links": len(links), "resources": len(resources), "issues": len(issues), "slug_hits": len(slug_hits)}
        return {"pages": pages, "links": links, "resources": resources, "issues": issues, "slugs": slug_hits, "stats": stats}
