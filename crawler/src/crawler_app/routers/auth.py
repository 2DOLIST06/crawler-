from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeSerializer
from crawler_app.config import settings

templates=Jinja2Templates(directory='src/crawler_app/templates')
router=APIRouter()
ser=URLSafeSerializer(settings.app_secret_key, salt='auth')

def is_auth(req:Request)->bool:
    tok=req.cookies.get('session')
    if not tok: return False
    try:return ser.loads(tok).get('u')==settings.admin_username
    except Exception:return False

@router.get('/login')
def login_page(request:Request): return templates.TemplateResponse('login.html',{'request':request})
@router.post('/login')
def login(username:str=Form(), password:str=Form()):
    if username==settings.admin_username and password==settings.admin_password:
        resp=RedirectResponse('/',302); resp.set_cookie('session',ser.dumps({'u':username}),httponly=True); return resp
    return RedirectResponse('/login',302)
@router.get('/logout')
def logout(): resp=RedirectResponse('/login',302); resp.delete_cookie('session'); return resp
