# crawler
Plateforme web de crawl générique avec FastAPI, PostgreSQL, SQLAlchemy et modules d'analyse extensibles.

## Architecture
Voir `src/crawler_app` : routers web, moteur de crawl, fetchers HTTP/Browser, analyzers SEO/links/slugs/resources, services, templates Jinja2.

## Lancer en local
1. `pip install -r requirements.txt`
2. `playwright install chromium`
3. Configurer `DATABASE_URL`, `APP_SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`.
4. `alembic upgrade head`
5. `uvicorn crawler_app.main:app --reload`

## Déploiement Render
- Utiliser `Dockerfile` et `render.yaml`.
- Render crée un web service + PostgreSQL.

## Utilisation
- Connexion via `/login`.
- Créer un projet avec URL de départ (ex: `https://www.2dolist.fr`).
- Lancer un run (mode http ou browser).
- Consulter pages, liens, ressources, issues, graphiques.
- Export CSV/JSON depuis détail de run.

## Ajouter un analyzer
Créer une classe dans `src/crawler_app/crawler/analyzers/` héritée de `BaseAnalyzer` avec `name`, `analyze_page`, `analyze_link`, `analyze_resource`, puis l’enregistrer dans le service de crawl.
