from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from crawler_app.database import get_db
from crawler_app.models import Project, Run
from crawler_app.routers.auth import is_auth

templates = Jinja2Templates(directory='src/crawler_app/templates')
router = APIRouter()


@router.get('/')
def home(request: Request, db: Session = Depends(get_db)):
    if not is_auth(request):
        return RedirectResponse('/login', 302)

    projects_count = db.query(Project).count()
    runs = db.query(Run).order_by(Run.started_at.desc().nullslast(), Run.id.desc()).all()
    runs_count = len(runs)
    latest_run = runs[0] if runs else None
    total_pages = sum(r.pages_crawled or 0 for r in runs)
    total_issues = sum(r.issues_found or 0 for r in runs)

    return templates.TemplateResponse(
        'dashboard.html',
        {
            'request': request,
            'projects_count': projects_count,
            'runs_count': runs_count,
            'latest_run': latest_run,
            'total_pages': total_pages,
            'total_issues': total_issues,
            'recent_runs': runs[:8],
        },
    )


@router.get('/missions')
def missions(request: Request):
    if not is_auth(request):
        return RedirectResponse('/login', 302)
    return templates.TemplateResponse('missions.html', {'request': request})




@router.get('/missions/simple-crawl')
def mission_simple_crawl(request: Request):
    if not is_auth(request):
        return RedirectResponse('/login', 302)
    return templates.TemplateResponse('mission_simple_crawl.html', {'request': request})


@router.get('/missions/seo-technical-audit')
def mission_seo_technical_audit(request: Request):
    if not is_auth(request):
        return RedirectResponse('/login', 302)
    return templates.TemplateResponse('mission_seo_technical_audit.html', {'request': request})

@router.get('/exports')
def exports_page(request: Request):
    if not is_auth(request):
        return RedirectResponse('/login', 302)
    return templates.TemplateResponse('exports.html', {'request': request})


@router.get('/missions/english-slugs-fr-audit')
def mission_english_slugs_fr_audit(request: Request):
    if not is_auth(request):
        return RedirectResponse('/login', 302)
    return templates.TemplateResponse('mission_english_slugs_fr_audit.html', {'request': request})



@router.get('/missions/parameter-urls-seo-audit')
def mission_parameter_urls_seo_audit(request: Request):
    if not is_auth(request):
        return RedirectResponse('/login', 302)
    return templates.TemplateResponse('mission_parameter_urls_seo_audit.html', {'request': request})


@router.get('/missions/internal-linking-audit')
def mission_internal_linking_audit(request: Request):
    if not is_auth(request):
        return RedirectResponse('/login', 302)
    return templates.TemplateResponse('mission_internal_linking_audit.html', {'request': request})
