from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from crawler_app.database import get_db
from crawler_app.models import Project, Run
from crawler_app.routers.auth import is_auth

templates=Jinja2Templates(directory='src/crawler_app/templates')
router=APIRouter()
@router.get('/')
def home(request:Request, db:Session=Depends(get_db)):
    if not is_auth(request): return RedirectResponse('/login',302)
    return templates.TemplateResponse('dashboard.html',{'request':request,'projects':db.query(Project).count(),'runs':db.query(Run).count()})
