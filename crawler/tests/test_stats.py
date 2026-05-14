from types import SimpleNamespace
from crawler_app.services.stats_service import indexable_vs_nonindexable, run_chart_stats

def test_stats():
    pages=[SimpleNamespace(robots_meta='',status_code=200),SimpleNamespace(robots_meta='noindex',status_code=200)]
    assert indexable_vs_nonindexable(pages)['indexable']==1


def test_chart_stats_labels_not_undefined():
    pages=[SimpleNamespace(status_code=200, depth=0), SimpleNamespace(status_code=None, depth=1)]
    issues=[SimpleNamespace(issue_type='broken_link', severity='high')]
    stats = run_chart_stats(pages, issues)
    for cfg in stats.values():
        assert all(label != 'undefined' for label in cfg['labels'])
