import json,csv,io
from pathlib import Path
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from crawler_app.config import settings
from crawler_app.database import get_db
from crawler_app.models import CrawledPage, Link, Resource, Issue
router=APIRouter(prefix='/exports')


def _save_export_file(run_id: int, kind: str, fmt: str, content: str) -> None:
    export_dir = Path(settings.exports_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    filename = f"run_{run_id}_{kind}.{fmt}"
    (export_dir / filename).write_text(content, encoding="utf-8")


@router.get('/run/{run_id}/{kind}.json')
def export_json(run_id:int,kind:str,db:Session=Depends(get_db)):
    model={'pages':CrawledPage,'links':Link,'resources':Resource,'issues':Issue}[kind]
    rows=[r.__dict__ for r in db.query(model).filter_by(run_id=run_id).all()]
    for r in rows: r.pop('_sa_instance_state',None)
    payload = json.dumps(rows, default=str, ensure_ascii=False, indent=2)
    _save_export_file(run_id, kind, "json", payload)
    return StreamingResponse(io.BytesIO(payload.encode("utf-8")),media_type='application/json')
@router.get('/run/{run_id}/{kind}.csv')
def export_csv(run_id:int,kind:str,db:Session=Depends(get_db)):
    model={'pages':CrawledPage,'links':Link,'resources':Resource,'issues':Issue}[kind]
    rows=[r.__dict__ for r in db.query(model).filter_by(run_id=run_id).all()]
    for r in rows: r.pop('_sa_instance_state',None)
    out=io.StringIO();
    if rows:
        w=csv.DictWriter(out,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    payload = out.getvalue()
    _save_export_file(run_id, kind, "csv", payload)
    return StreamingResponse(iter([payload]),media_type='text/csv')
