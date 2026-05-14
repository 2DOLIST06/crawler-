def indexable_vs_nonindexable(pages):
    idx=sum(1 for p in pages if (p.robots_meta or '').find('noindex')==-1 and (p.status_code or 0)<400)
    return {'indexable':idx,'non_indexable':len(pages)-idx}


def _chart_data_from_counts(counts: dict, empty_message: str):
    labels = [str(k) for k in counts.keys() if k is not None and str(k) != ""]
    data = [counts[k] for k in counts.keys() if k is not None and str(k) != ""]
    if not labels:
        return {"labels": [], "data": [], "empty_message": empty_message}
    return {"labels": labels, "data": data, "empty_message": ""}


def run_chart_stats(pages, issues):
    status_counts = {}
    depth_counts = {}
    for p in pages:
        code = p.status_code if p.status_code is not None else "unknown"
        status_counts[code] = status_counts.get(code, 0) + 1
        depth_counts[p.depth] = depth_counts.get(p.depth, 0) + 1

    type_counts = {}
    severity_counts = {}
    for i in issues:
        itype = i.issue_type or "unknown"
        sev = i.severity or "unknown"
        type_counts[itype] = type_counts.get(itype, 0) + 1
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    return {
        "status_codes": _chart_data_from_counts(status_counts, "Aucun status code à afficher."),
        "issues_by_type": _chart_data_from_counts(type_counts, "Aucune issue à afficher."),
        "issues_by_severity": _chart_data_from_counts(severity_counts, "Aucune sévérité à afficher."),
        "pages_by_depth": _chart_data_from_counts(depth_counts, "Aucune profondeur à afficher."),
    }
