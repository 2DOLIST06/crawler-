from crawler.models import ResourceRecord


def summarize_resources(resources: list[ResourceRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in resources:
        counts[r.resource_type] = counts.get(r.resource_type, 0) + 1
    return counts
