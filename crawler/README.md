# crawler

Plateforme web de crawl générique avec FastAPI, SQLAlchemy et des analyseurs SEO/links/slugs/resources extensibles.

L'application fonctionne en **deux modes** :

- **Mode local (gratuit)** : SQLite locale (`crawler.db`), aucun serveur externe obligatoire.
- **Mode serveur** : PostgreSQL via `DATABASE_URL` (ex: Render).

---

## 1) Mode local (Windows / Linux / macOS)

### Prérequis
- Python 3.11+
- (Optionnel mais recommandé) un environnement virtuel

### Installation
```bash
pip install -r requirements.txt
playwright install chromium
```

### Configuration SQLite locale
Par défaut, la configuration est déjà compatible local :
- `DATABASE_URL=sqlite:///./crawler.db`
- `EXPORTS_DIR=exports`

Vous pouvez créer un fichier `.env` à la racine du repo :
```env
DATABASE_URL=sqlite:///./crawler.db
EXPORTS_DIR=exports
APP_SECRET_KEY=change-me
ENVIRONMENT=development
# Optionnel en local: défaut admin/admin en mode development
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
```

### Démarrage de l'application
Depuis le dossier `crawler/` :
```bash
uvicorn crawler_app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Ouvrir l'interface dans le navigateur
- URL : **http://localhost:8000**
- Connexion : `/login` avec `ADMIN_USERNAME` / `ADMIN_PASSWORD`

### Données et exports en local
- Base locale : fichier `crawler.db` (créé automatiquement)
- Exports : dossier `exports/` (créé automatiquement lors d’un export CSV/JSON)

Aucune dépendance obligatoire à Render ou à une base PostgreSQL payante pour ce mode.

---

## 2) Mode serveur (Render + PostgreSQL)

### Principe
En production, configurez `DATABASE_URL` vers PostgreSQL (fournie par Render ou autre hébergeur).

Exemple :
```env
DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname
ENVIRONMENT=production
```

### Déploiement Render
Le repo contient déjà :
- `Dockerfile` compatible Render
- `render.yaml` pour provisionner le web service et la base PostgreSQL

Étapes générales :
1. Push du repo sur GitHub.
2. Créer un nouveau service Render avec `render.yaml`.
3. Vérifier les variables d’environnement (`DATABASE_URL`, `APP_SECRET_KEY`, etc.).
4. Déployer.

---

## Compatibilité base de données (SQLite + PostgreSQL)

La couche ORM utilise SQLAlchemy avec un schéma compatible SQLite et PostgreSQL.
Aucune fonctionnalité PostgreSQL-only n’est requise pour le fonctionnement courant.

---

## Architecture
Voir `src/crawler_app` :
- routers web
- moteur de crawl
- fetchers HTTP/Browser
- analyzers SEO/links/slugs/resources
- services
- templates Jinja2

## Utilisation
- Connexion via `/login`.
- Créer un projet avec URL de départ.
- Lancer un run (mode `http` ou `browser`).
- Consulter pages, liens, ressources, issues, graphiques.
- Export CSV/JSON depuis détail de run.

## Ajouter un analyzer
Créer une classe dans `src/crawler_app/crawler/analyzers/` héritée de `BaseAnalyzer` avec :
- `name`
- `analyze_page`
- `analyze_link`
- `analyze_resource`
puis l’enregistrer dans le service de crawl.


En mode `production`, définissez explicitement `ADMIN_USERNAME` et `ADMIN_PASSWORD` (pas de fallback implicite).


## Migrations (important)

Le schéma est versionné avec **Alembic**. Après un `git pull` (ou après l’ajout de nouvelles colonnes/tables), appliquez toujours les migrations avant de démarrer l’app :

```bash
alembic upgrade head
```

Ensuite lancez le serveur :

```bash
PYTHONPATH=src uvicorn crawler_app.main:app --reload --host 0.0.0.0 --port 8000
```

Cette étape garantit la compatibilité des bases existantes (SQLite locale et PostgreSQL) avec les nouveaux champs comme `runs.mission_type`.
