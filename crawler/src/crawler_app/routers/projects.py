from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from crawler_app.database import get_db
from crawler_app.models import Project, Run
from crawler_app.routers.auth import is_auth

templates = Jinja2Templates(directory='src/crawler_app/templates')
router = APIRouter(prefix='/projects')


@router.get('')
def list_projects(request: Request, db: Session = Depends(get_db)):
    if not is_auth(request):
        return RedirectResponse('/login', 302)
    projects = db.query(Project).order_by(Project.created_at.desc(), Project.id.desc()).all()
    return templates.TemplateResponse('projects.html', {'request': request, 'projects': projects})


@router.post('')
def create_project(
    request: Request,
    name: str = Form(),
    start_url: str = Form(),
    allowed_domain: str = Form(),
    same_host_only: bool = Form(False),
    default_max_pages: int = Form(500),
    default_max_depth: int = Form(5),
    default_mode: str = Form('http'),
    db: Session = Depends(get_db),
):
    if not is_auth(request):
        return RedirectResponse('/login', 302)
    p = Project(
        name=name,
        start_url=start_url,
        allowed_domain=allowed_domain,
        same_host_only=same_host_only,
        default_max_pages=default_max_pages,
        default_max_depth=default_max_depth,
        default_mode=default_mode,
    )
    db.add(p)
    db.commit()
    return RedirectResponse('/projects', 302)


@router.get('/{project_id}')
def detail(project_id: int, request: Request, db: Session = Depends(get_db)):
    if not is_auth(request):
        return RedirectResponse('/login', 302)
    p = db.get(Project, project_id)
    runs = db.query(Run).filter(Run.project_id == project_id).order_by(Run.id.desc()).all()
    latest_run = runs[0] if runs else None
    return templates.TemplateResponse(
        'project_detail.html',
        {'request': request, 'project': p, 'runs': runs, 'latest_run': latest_run},
    )
