import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from crawler_app.database import get_db
from crawler_app.models import Run, Project, CrawledPage, Link, Issue, Resource
from crawler_app.routers.auth import is_auth
from crawler_app.services.crawl_service import execute_run
from crawler_app.services.stats_service import run_chart_stats

templates=Jinja2Templates(directory='src/crawler_app/templates')
router=APIRouter(prefix='/runs')

@router.post('/create/{project_id}')
def create_run(project_id:int,request:Request, mission:str=Form('simple'), mode:str=Form('http'), max_pages:int=Form(100), max_depth:int=Form(3), db:Session=Depends(get_db)):
    if not is_auth(request): return RedirectResponse('/login',302)
    run=Run(project_id=project_id,mode=mode,max_pages=max_pages,max_depth=max_depth,config_snapshot={'mission':mission,'mode':mode,'max_pages':max_pages,'max_depth':max_depth})
    db.add(run); db.commit(); db.refresh(run)
    asyncio.run(execute_run(db,run,db.get(Project,project_id)))
    return RedirectResponse(f'/runs/{run.id}',302)

@router.get('/{run_id}')
def run_detail(run_id:int, request:Request, status_code:str|None=Query(default=None), page_q:str|None=Query(default=None), severity:str|None=Query(default=None), issue_type:str|None=Query(default=None), db:Session=Depends(get_db)):
    if not is_auth(request): return RedirectResponse('/login',302)
    run=db.get(Run,run_id)
    pages_q=db.query(CrawledPage).filter_by(run_id=run_id)
    issues_q=db.query(Issue).filter_by(run_id=run_id)
    links=db.query(Link).filter_by(run_id=run_id).all()
    resources=db.query(Resource).filter_by(run_id=run_id).all()

    if status_code:
        if status_code == "unknown":
            pages_q = pages_q.filter(CrawledPage.status_code.is_(None))
        else:
            pages_q = pages_q.filter(CrawledPage.status_code == int(status_code))
    if page_q:
        pages_q = pages_q.filter(CrawledPage.final_url.ilike(f"%{page_q}%"))

    if severity:
        issues_q = issues_q.filter(Issue.severity == severity)
    if issue_type:
        issues_q = issues_q.filter(Issue.issue_type == issue_type)

    pages = pages_q.all()
    issues = issues_q.all()
    all_pages = db.query(CrawledPage).filter_by(run_id=run_id).all()
    all_issues = db.query(Issue).filter_by(run_id=run_id).all()

    chart_stats = run_chart_stats(all_pages, all_issues)
    status_options = sorted({str(p.status_code) if p.status_code is not None else "unknown" for p in all_pages})
    severity_options = sorted({i.severity for i in all_issues if i.severity})
    issue_type_options = sorted({i.issue_type for i in all_issues if i.issue_type})
    duration = None
    if run and run.started_at and run.finished_at:
        duration = str(run.finished_at - run.started_at)

    return templates.TemplateResponse('run_detail.html',{'request':request,'run':run,'pages':pages,'links':links,'issues':issues,'resources':resources,'chart_stats':chart_stats,'status_options':status_options,'severity_options':severity_options,'issue_type_options':issue_type_options,'filters':{'status_code':status_code or '', 'page_q':page_q or '', 'severity':severity or '', 'issue_type':issue_type or ''},'duration':duration})
