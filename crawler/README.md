# crawler

Crawler web externe générique autonome en Python 3.11+.

## Objectif
Ce projet crawl un site comme un visiteur externe depuis une URL de départ, sans accès backend/base de données.

## Installation
```bash
pip install -r requirements.txt
playwright install chromium
```

## Exécution
```bash
python -m crawler.cli crawl --start-url https://www.2dolist.fr --allowed-domain www.2dolist.fr
python -m crawler.cli crawl --start-url https://www.2dolist.fr --allowed-domain www.2dolist.fr --max-pages 500 --max-depth 5
python -m crawler.cli crawl --start-url https://www.2dolist.fr --allowed-domain www.2dolist.fr --mode http
python -m crawler.cli crawl --start-url https://www.2dolist.fr --allowed-domain www.2dolist.fr --mode browser
```

## Rapports
Les exports CSV/JSON sont générés dans `reports/` : pages, links, resources, issues, seo, slugs, crawl.json.

## Limites connues
- Détection JS très complexe non exhaustive.
- Vérification du status code des liens individuels non systématique.
