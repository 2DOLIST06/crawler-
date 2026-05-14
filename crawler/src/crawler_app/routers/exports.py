import json,csv,io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from crawler_app.database import get_db
from crawler_app.models import CrawledPage, Link, Resource, Issue
router=APIRouter(prefix='/exports')
@router.get('/run/{run_id}/{kind}.json')
def export_json(run_id:int,kind:str,db:Session=Depends(get_db)):
    model={'pages':CrawledPage,'links':Link,'resources':Resource,'issues':Issue}[kind]
    rows=[r.__dict__ for r in db.query(model).filter_by(run_id=run_id).all()]
    for r in rows: r.pop('_sa_instance_state',None)
    return StreamingResponse(io.BytesIO(json.dumps(rows,default=str).encode()),media_type='application/json')
@router.get('/run/{run_id}/{kind}.csv')
def export_csv(run_id:int,kind:str,db:Session=Depends(get_db)):
    model={'pages':CrawledPage,'links':Link,'resources':Resource,'issues':Issue}[kind]
    rows=[r.__dict__ for r in db.query(model).filter_by(run_id=run_id).all()]
    for r in rows: r.pop('_sa_instance_state',None)
    out=io.StringIO();
    if rows:
        w=csv.DictWriter(out,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    return StreamingResponse(iter([out.getvalue()]),media_type='text/csv')
