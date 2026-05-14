from collections import deque
from datetime import datetime
from crawler_app.models import Run, CrawledPage, Link, Resource, Issue
from crawler_app.crawler.normalize import normalize_url
from crawler_app.crawler.parsers.html_parser import parse_html
from crawler_app.crawler.fetchers.http_fetcher import HttpFetcher
from crawler_app.crawler.fetchers.browser_fetcher import BrowserFetcher
from crawler_app.crawler.analyzers import SEOAnalyzer, LinkAnalyzer, SlugAnalyzer

async def execute_run(db, run: Run, project):
    run.status="running"; run.started_at=datetime.utcnow(); db.commit()
    fetcher = HttpFetcher() if run.mode=="http" else BrowserFetcher()
    analyzers=[SEOAnalyzer(),LinkAnalyzer(),SlugAnalyzer()]
    q=deque([(project.start_url,0,None)]); seen=set();
    while q and run.pages_crawled<run.max_pages:
        url,depth,src=q.popleft(); n=normalize_url(url)
        if n in seen or depth>run.max_depth: continue
        seen.add(n)
        try:
            fr=await fetcher.fetch(url)
            parsed=parse_html(fr['text']) if 'html' in fr['content_type'] else {"links":[],"resources":[]}
            page=CrawledPage(run_id=run.id,requested_url=url,final_url=fr['final_url'],normalized_url=n,status_code=fr['status_code'],content_type=fr['content_type'],depth=depth,fetch_mode=run.mode,title=parsed.get('title'),title_length=len(parsed.get('title') or ''),meta_description=parsed.get('meta_description'),meta_description_length=len(parsed.get('meta_description') or ''),canonical=parsed.get('canonical'),h1=parsed.get('h1'),h1_count=parsed.get('h1_count',0),h2_count=parsed.get('h2_count',0),word_count=parsed.get('word_count',0),found_on=[src] if src else [],redirect_chain=fr.get('redirect_chain',[]))
            db.add(page); db.flush(); run.pages_crawled+=1
            for it,sev in analyzers[0].analyze_page({**parsed,"status_code":fr['status_code'],"final_url":fr['final_url']}): db.add(Issue(run_id=run.id,issue_type=it,severity=sev,url=fr['final_url']))
            for href in parsed.get('links',[]):
                if not href: continue
                dest=normalize_url(href, fr['final_url'])
                internal=project.allowed_domain in dest
                l=Link(run_id=run.id,source_url=fr['final_url'],destination_url=href,normalized_url=dest,anchor_text='',link_type='internal' if internal else 'external',is_internal=internal,is_external=not internal,is_crawlable=internal,found_at_depth=depth+1)
                db.add(l); run.links_found+=1
                for it,sev in analyzers[1].analyze_link({"destination_url":href}): db.add(Issue(run_id=run.id,issue_type=it,severity=sev,url=dest,source_url=fr['final_url']))
                if internal: q.append((dest,depth+1,fr['final_url']))
            for r in parsed.get('resources',[]): db.add(Resource(run_id=run.id,source_url=fr['final_url'],resource_url=normalize_url(r['url'],fr['final_url']),resource_type=r['type'],tag_name=r['tag'],attribute_name=r['attr']))
            for it,sev in analyzers[2].analyze_page({"final_url":fr['final_url']}): db.add(Issue(run_id=run.id,issue_type=it,severity=sev,url=fr['final_url']))
            db.commit()
        except Exception as e:
            db.add(Issue(run_id=run.id,issue_type='fetch_error',severity='error',url=url,details=str(e)))
            db.commit()
    run.status='completed'; run.finished_at=datetime.utcnow(); run.issues_found=db.query(Issue).filter(Issue.run_id==run.id).count(); db.commit()
