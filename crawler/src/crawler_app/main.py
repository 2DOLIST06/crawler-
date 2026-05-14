from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from crawler_app.database import Base, engine
from crawler_app.routers import auth, dashboard, projects, runs, exports

Base.metadata.create_all(bind=engine)
app=FastAPI(title='crawler')
app.mount('/static', StaticFiles(directory='src/crawler_app/static'), name='static')
for r in [auth.router,dashboard.router,projects.router,runs.router,exports.router]: app.include_router(r)
