from pathlib import Path

import typer

from crawler.config import CrawlConfig
from crawler.engine.crawler import CrawlerEngine
from crawler.exporters.csv_exporter import export_csv
from crawler.exporters.json_exporter import export_json
from crawler.fetchers.browser_fetcher import BrowserFetcher
from crawler.fetchers.http_fetcher import HttpFetcher
from crawler.utils.logging import console

app = typer.Typer()


@app.command()
def crawl(start_url: str = typer.Option(...), allowed_domain: str = typer.Option(...), max_pages: int = 1000, max_depth: int = 5, mode: str = "http", output_dir: Path = Path("reports"), delay: float = 0.0, timeout: float = 15.0, respect_robots: bool = True, include_query_params: bool = False, user_agent: str = "GenericCrawler/0.1", same_host_only: bool = False, verbose: bool = False):
    config = CrawlConfig(start_url=start_url, allowed_domain=allowed_domain, max_pages=max_pages, max_depth=max_depth, mode=mode, output_dir=output_dir, delay=delay, timeout=timeout, respect_robots=respect_robots, include_query_params=include_query_params, user_agent=user_agent, same_host_only=same_host_only, verbose=verbose)
    output_dir.mkdir(parents=True, exist_ok=True)
    fetcher = HttpFetcher(timeout, user_agent) if mode == "http" else BrowserFetcher(timeout, user_agent)
    try:
        result = CrawlerEngine(config, fetcher).run()
    finally:
        fetcher.close()
    pages = [p.model_dump() for p in result["pages"]]
    links = [l.model_dump() for l in result["links"]]
    resources = [r.model_dump() for r in result["resources"]]
    issues = [i.model_dump() for i in result["issues"]]
    slugs = result["slugs"]
    seo_rows = [{"url": p["normalized_url"], "status_code": p["status_code"], "title": p["title"], "title_length": p["title_length"], "meta_description": p["meta_description"], "meta_description_length": p["meta_description_length"], "canonical": p["canonical"], "robots_meta": p["robots_meta"], "h1_count": p["h1_count"], "h1": " | ".join(p["h1_list"]), "h2_count": p["h2_count"], "indexability_status": "non_indexable" if "noindex" in p["robots_meta"].lower() else "indexable", "seo_issues": ""} for p in pages]
    export_csv(output_dir / "pages.csv", pages)
    export_csv(output_dir / "links.csv", links)
    export_csv(output_dir / "resources.csv", resources)
    export_csv(output_dir / "issues.csv", issues)
    export_csv(output_dir / "seo.csv", seo_rows)
    export_csv(output_dir / "slugs.csv", slugs)
    export_json(output_dir / "crawl.json", {"config": config.model_dump(mode='json'), "pages": pages, "links": links, "resources": resources, "issues": issues, "stats": result["stats"]})
    console.print(f"Exports générés dans {output_dir}")


if __name__ == "__main__":
    app()
