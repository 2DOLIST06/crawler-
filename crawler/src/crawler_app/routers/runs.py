import asyncio
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from crawler_app.database import get_db
from crawler_app.models import Run, Project, CrawledPage, Link, Issue, Resource
from crawler_app.routers.auth import is_auth
from crawler_app.services.crawl_service import execute_run

templates=Jinja2Templates(directory='src/crawler_app/templates')
router=APIRouter(prefix='/runs')
@router.post('/create/{project_id}')
def create_run(project_id:int,request:Request, mode:str=Form('http'), max_pages:int=Form(100), max_depth:int=Form(3), db:Session=Depends(get_db)):
    if not is_auth(request): return RedirectResponse('/login',302)
    run=Run(project_id=project_id,mode=mode,max_pages=max_pages,max_depth=max_depth,config_snapshot={'mode':mode,'max_pages':max_pages,'max_depth':max_depth})
    db.add(run); db.commit(); db.refresh(run)
    asyncio.run(execute_run(db,run,db.get(Project,project_id)))
    return RedirectResponse(f'/runs/{run.id}',302)
@router.get('/{run_id}')
def run_detail(run_id:int, request:Request, db:Session=Depends(get_db)):
    if not is_auth(request): return RedirectResponse('/login',302)
    run=db.get(Run,run_id)
    return templates.TemplateResponse('run_detail.html',{'request':request,'run':run,'pages':db.query(CrawledPage).filter_by(run_id=run_id).all(),'links':db.query(Link).filter_by(run_id=run_id).all(),'issues':db.query(Issue).filter_by(run_id=run_id).all(),'resources':db.query(Resource).filter_by(run_id=run_id).all()})
