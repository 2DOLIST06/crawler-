from types import SimpleNamespace
from crawler_app.services.stats_service import indexable_vs_nonindexable

def test_stats():
    pages=[SimpleNamespace(robots_meta='',status_code=200),SimpleNamespace(robots_meta='noindex',status_code=200)]
    assert indexable_vs_nonindexable(pages)['indexable']==1
