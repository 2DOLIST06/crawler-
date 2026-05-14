import asyncio
from fastapi import APIRouter, BackgroundTasks, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from crawler_app.database import SessionLocal, get_db
from crawler_app.models import Run, Project, CrawledPage, Link, Issue, Resource
from crawler_app.routers.auth import is_auth
from crawler_app.services.crawl_service import execute_run
from crawler_app.services.stats_service import run_chart_stats

templates = Jinja2Templates(directory='src/crawler_app/templates')
router = APIRouter(prefix='/runs')

from urllib.parse import urlparse


def _is_english_url_on_fr(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    host = (parsed.netloc or '').lower()
    path = (parsed.path or '').lower()
    return host.endswith('.fr') and '/en' in f"{path}/"



ISSUE_TYPE_LABELS = {
    "missing_title": "Title manquant",
    "title_too_short": "Title trop court",
    "title_too_long": "Title trop long",
    "missing_meta_description": "Meta description manquante",
    "meta_description_too_short": "Meta description trop courte",
    "meta_description_too_long": "Meta description trop longue",
    "missing_h1": "H1 manquant",
    "multiple_h1": "H1 multiple",
    "missing_canonical": "Canonical absente",
    "suspicious_slug": "URL anglaise sur .fr",
    "english_slug_on_fr": "URL anglaise sur .fr",
    "broken_internal_link": "Lien interne cassé",
}

def _detect_discovery_type(issue_type: str, details: str) -> str:
    d=(details or '').lower(); t=(issue_type or '').lower()
    if 'sitemap' in d or 'sitemap' in t: return 'sitemap'
    if 'canonical' in d or 'canonical' in t: return 'canonical'
    if 'hreflang' in d or 'hreflang' in t: return 'hreflang'
    if 'prev' in d or 'next' in d: return 'prev_next'
    return 'a_href'

def get_issue_recommendation(issue_type: str, discovery_type: str, target_is_200: bool=False):
    t=(issue_type or '').lower()
    map_fixed={
    'missing_title':('contenu / template SEO','Ajouter une balise title unique et descriptive sur cette page.'),
    'title_too_short':('contenu / template SEO','Réécrire le title pour qu’il décrive clairement la page.'),
    'title_too_long':('contenu / template SEO','Raccourcir le title en gardant les mots importants au début.'),
    'missing_meta_description':('contenu / template SEO','Ajouter une meta description unique et utile pour cette page.'),
    'missing_h1':('template ou contenu de page','Ajouter un H1 unique visible sur cette page.'),
    'multiple_h1':('template ou contenu de page','Conserver un seul H1 principal et transformer les autres titres en H2.'),
    'missing_canonical':('template SEO','Ajouter une canonical absolue vers l’URL propre de la page.'),
    'broken_internal_link':('lien interne','Corriger ou supprimer le lien cassé sur la page source.'),
    'internal_redirect':('lien interne','Remplacer le lien par l’URL finale pour éviter une redirection inutile.'),
    }
    if t in {'suspicious_slug','english_slug_on_fr'}:
        if target_is_200: return ('redirection / routing','Ajouter une redirection 301 vers l’URL française équivalente.')
        by={'a_href':'Remplacer le lien interne par l’URL française équivalente.','sitemap':'Retirer l’URL anglaise du sitemap ou la remplacer par l’URL française.','canonical':'Corriger la canonical vers l’URL française.','hreflang':'Corriger le hreflang fr-FR vers l’URL française.'}
        return ('selon discovery_type', by.get(discovery_type,'Corriger la source de cette URL anglaise.'))
    return map_fixed.get(t, ('template / contenu','Corriger selon la règle SEO de ce type de problème.'))
def _map_fix_category(issue_type: str, discovery_type: str, likely_origin: str) -> str:
    t = (issue_type or '').lower()
    if discovery_type == 'sitemap' or 'sitemap' in t:
        return 'sitemap'
    if discovery_type == 'canonical' or 'canonical' in t:
        return 'canonical'
    if discovery_type == 'hreflang' or 'hreflang' in t:
        return 'hreflang'
    if discovery_type in {'a_href', 'prev_next'}:
        return 'maillage interne'
    if 'robots' in t or 'index' in t:
        return 'robots'
    if 'redirect' in t or 'redirection' in t:
        return 'redirection'
    if likely_origin in {'code', 'contenu'}:
        return likely_origin
    return 'code'


def _where_to_fix(discovery_type: str, target_status_code: int | None) -> str:
    if discovery_type == 'a_href':
        return 'Corriger le lien généré sur la page source. Vérifier le composant, le contenu CMS ou la fonction qui construit cette URL.'
    if discovery_type == 'sitemap':
        return 'Corriger la génération du sitemap pour ne plus inclure cette URL.'
    if discovery_type == 'canonical':
        return 'Corriger la balise canonical générée sur cette page.'
    if discovery_type == 'hreflang':
        return 'Corriger les balises hreflang générées pour cette page.'
    if target_status_code == 200:
        return "Ajouter ou corriger la redirection 301 vers l'URL française équivalente, ou empêcher cette route d'être servie en 200."
    return "Corriger à la source de génération de l'URL problématique (template, CMS, règle SEO ou routage)."


def _recommended_action(fix_category: str, discovery_type: str, is_english_200: bool) -> str:
    if is_english_200:
        return "Ajouter une redirection 301 de l'URL anglaise vers l'URL française."
    if discovery_type == 'sitemap':
        return 'Retirer cette URL du sitemap.'
    if discovery_type == 'canonical':
        return "Corriger la canonical pour pointer vers l'URL française propre."
    if discovery_type == 'hreflang':
        return 'Corriger hreflang fr-FR pour pointer vers la page française.'
    if discovery_type == 'a_href':
        return "Remplacer le lien interne par l'URL française."
    if fix_category == 'robots':
        return "Ajouter noindex ou canonical vers l'URL propre pour cette URL à paramètre."
    return 'Corriger ou supprimer le lien cassé.'


def _enrich_issue(issue, pages_by_url: dict, links_by_destination: dict):
    detail = issue.details or ''
    discovery_type = _detect_discovery_type(issue.issue_type or '', detail)
    link = links_by_destination.get(issue.url)
    source_url = issue.source_url or (link.source_url if link else None)
    target_page = pages_by_url.get(issue.url)
    target_status_code = target_page.status_code if target_page else None
    target_is_200 = target_status_code == 200
    where_to_fix, action = get_issue_recommendation(issue.issue_type or '', discovery_type, target_is_200)
    likely_origin = 'code'
    fix_category = _map_fix_category(issue.issue_type or '', discovery_type, likely_origin)
    recommended_fix = _recommended_action(fix_category, discovery_type, target_is_200)
    return {
        'raw': issue,
        'problem_summary': ISSUE_TYPE_LABELS.get(issue.issue_type, issue.issue_type),
        'source_url': source_url,
        'target_url': issue.url,
        'discovery_type': discovery_type,
        'evidence': detail,
        'priority': issue.severity,
        'where_to_fix': where_to_fix,
        'action_recommandee': action,
        'recommended_fix': recommended_fix,
        'fix_category': fix_category,
        'target_status_code': target_status_code,
        'target_is_200': target_is_200,
    }


def _build_action_plan(enriched_issues: list[dict]):
    groups = [
        ('code', 'Corrections code / templates'),
        ('contenu', 'Corrections contenus'),
        ('sitemap', 'Corrections sitemap'),
        ('redirection', 'Corrections redirections'),
        ('canonical', 'Corrections canonical'),
        ('hreflang', 'Corrections hreflang'),
        ('maillage interne', 'Corrections maillage interne'),
        ('robots', 'Corrections robots/indexabilité'),
    ]
    out=[]
    for key,label in groups:
        selected=[i for i in enriched_issues if i.get('fix_category')==key]
        urls = sorted({i.get('target_url') for i in selected if i.get('target_url')})
        default_action = 'Aucune action.'
        if selected:
            first = selected[0]
            default_action = (
                first.get('action_recommandee')
                or first.get('recommended_fix')
                or 'Aucune action.'
            )
        out.append({'key':key,'label':label,'count':len(selected),'urls':urls, 'action': default_action})
    return out


@router.get('')
def list_runs(request: Request, db: Session = Depends(get_db)):
    if not is_auth(request):
        return RedirectResponse('/login', 302)
    runs = db.query(Run).order_by(Run.id.desc()).all()
    return templates.TemplateResponse('runs.html', {'request': request, 'runs': runs})


def run_crawl_background(run_id: int):
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if not run:
            return
        project = db.get(Project, run.project_id)
        if not project:
            run.status = 'failed'
            run.error_message = 'Project not found.'
            db.commit()
            return
        run.status = 'running'
        run.error_message = None
        db.commit()
        asyncio.run(execute_run(db, run, project))
    except Exception as exc:
        run = db.get(Run, run_id)
        if run:
            run.status = 'failed'
            run.error_message = str(exc)
            db.commit()
    finally:
        db.close()


@router.post('/create/{project_id}')
def create_run(project_id: int, request: Request, background_tasks: BackgroundTasks, mission_type: str = Form(...), mode: str = Form('http'), max_pages: int = Form(100), max_depth: int = Form(3), delay: float = Form(0.2), respect_robots: bool = Form(False), db: Session = Depends(get_db)):
    if not is_auth(request):
        return RedirectResponse('/login', 302)
    run = Run(project_id=project_id, status='pending', mode=mode, mission_type=mission_type, max_pages=max_pages, max_depth=max_depth, config_snapshot={'mission_type': mission_type, 'mode': mode, 'max_pages': max_pages, 'max_depth': max_depth, 'delay': delay, 'respect_robots': respect_robots})
    db.add(run)
    db.commit()
    db.refresh(run)
    background_tasks.add_task(run_crawl_background, run.id)
    return RedirectResponse(f'/runs/{run.id}', status_code=303)


@router.get('/{run_id}')
def run_detail(run_id: int, request: Request, status_code: str | None = Query(default=None), page_q: str | None = Query(default=None), depth: str | None = Query(default=None), indexability: str | None = Query(default=None), severity: str | None = Query(default=None), issue_type: str | None = Query(default=None), issue_url_q: str | None = Query(default=None), db: Session = Depends(get_db)):
    if not is_auth(request):
        return RedirectResponse('/login', 302)
    run = db.get(Run, run_id)
    pages_q = db.query(CrawledPage).filter_by(run_id=run_id)
    issues_q = db.query(Issue).filter_by(run_id=run_id)
    links = db.query(Link).filter_by(run_id=run_id).all()
    resources = db.query(Resource).filter_by(run_id=run_id).all()
    pages_by_url = {p.final_url: p for p in db.query(CrawledPage).filter_by(run_id=run_id).all()}
    links_by_destination = {l.destination_url: l for l in links}

    if status_code:
        if status_code == 'unknown':
            pages_q = pages_q.filter(CrawledPage.status_code.is_(None))
        else:
            pages_q = pages_q.filter(CrawledPage.status_code == int(status_code))
    if page_q:
        pages_q = pages_q.filter(CrawledPage.final_url.ilike(f'%{page_q}%'))
    if depth:
        pages_q = pages_q.filter(CrawledPage.depth == int(depth))
    if indexability == 'indexable':
        pages_q = pages_q.filter((CrawledPage.robots_meta.is_(None)) | (~CrawledPage.robots_meta.ilike('%noindex%')))
    elif indexability == 'non_indexable':
        pages_q = pages_q.filter(CrawledPage.robots_meta.ilike('%noindex%'))

    if severity:
        issues_q = issues_q.filter(Issue.severity == severity)
    if issue_type:
        issues_q = issues_q.filter(Issue.issue_type == issue_type)
    if issue_url_q:
        issues_q = issues_q.filter(Issue.url.ilike(f'%{issue_url_q}%'))

    pages = pages_q.all()
    issues = issues_q.all()
    enriched_issues = [_enrich_issue(i, pages_by_url, links_by_destination) for i in issues]
    all_pages = db.query(CrawledPage).filter_by(run_id=run_id).all()
    all_issues = db.query(Issue).filter_by(run_id=run_id).all()

    chart_stats = run_chart_stats(all_pages, all_issues)
    status_options = sorted({str(p.status_code) if p.status_code is not None else 'unknown' for p in all_pages})
    depth_options = sorted({p.depth for p in all_pages})
    severity_options = sorted({i.severity for i in all_issues if i.severity})
    issue_type_options = sorted({i.issue_type for i in all_issues if i.issue_type})

    duration = None
    if run and run.started_at and run.finished_at:
        duration = str(run.finished_at - run.started_at)

    pages_200 = sum(1 for p in all_pages if p.status_code == 200)
    errors_4xx_5xx = sum(1 for p in all_pages if p.status_code and p.status_code >= 400)
    redirects = sum(1 for p in all_pages if p.status_code and 300 <= p.status_code < 400)
    indexable = sum(1 for p in all_pages if not (p.robots_meta and 'noindex' in p.robots_meta.lower()))
    non_indexable = len(all_pages) - indexable

    sev_counts = {k: 0 for k in ['critical', 'high', 'medium', 'low']}
    for i in all_issues:
        s = (i.severity or '').lower()
        if s in sev_counts:
            sev_counts[s] += 1

    all_enriched = [_enrich_issue(i, pages_by_url, links_by_destination) for i in all_issues]
    priority_rows = [i for i in all_enriched if (i.get('priority') or '').lower() in {'critical','high'}][:20]
    if not priority_rows:
        priority_rows = [i for i in all_enriched if (i.get('priority') or '').lower() == 'medium'][:20]

    english_rows = [i for i in all_enriched if (i['raw'].issue_type or '').lower() in {'suspicious_slug','english_slug_on_fr'}]
    english_counts = {
        'total': len(english_rows),
        'a_href': sum(1 for i in english_rows if i['discovery_type']=='a_href'),
        'sitemap': sum(1 for i in english_rows if i['discovery_type']=='sitemap'),
        'canonical': sum(1 for i in english_rows if i['discovery_type']=='canonical'),
        'hreflang': sum(1 for i in english_rows if i['discovery_type']=='hreflang'),
        'is_200': sum(1 for i in english_rows if i['target_is_200']),
    }
    return templates.TemplateResponse('run_detail.html', {'request': request, 'run': run, 'pages': pages, 'links': links, 'issues': issues, 'resources': resources, 'chart_stats': chart_stats, 'status_options': status_options, 'depth_options': depth_options, 'severity_options': severity_options, 'issue_type_options': issue_type_options, 'filters': {'status_code': status_code or '', 'page_q': page_q or '', 'depth': depth or '', 'indexability': indexability or '', 'severity': severity or '', 'issue_type': issue_type or '', 'issue_url_q': issue_url_q or ''}, 'duration': duration, 'stats': {'pages_200': pages_200, 'errors_4xx_5xx': errors_4xx_5xx, 'redirects': redirects, 'indexable': indexable, 'non_indexable': non_indexable, 'critical': sev_counts['critical'], 'high': sev_counts['high'], 'medium': sev_counts['medium'], 'low': sev_counts['low']}, 'enriched_issues': enriched_issues, 'action_plan': _build_action_plan(enriched_issues), 'priority_rows': priority_rows, 'english_counts': english_counts, 'all_enriched': all_enriched})
