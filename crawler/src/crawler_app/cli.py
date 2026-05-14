import asyncio, typer
from crawler_app.database import SessionLocal
from crawler_app.models import Project, Run
from crawler_app.services.crawl_service import execute_run
app=typer.Typer()
@app.command()
def crawl(project_id:int):
    db=SessionLocal(); p=db.get(Project,project_id); r=Run(project_id=project_id,mode=p.default_mode,max_pages=p.default_max_pages,max_depth=p.default_max_depth,config_snapshot={})
    db.add(r); db.commit(); db.refresh(r); asyncio.run(execute_run(db,r,p)); typer.echo(f'Run {r.id}')
if __name__=='__main__': app()
