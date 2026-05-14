def indexable_vs_nonindexable(pages):
    idx=sum(1 for p in pages if (p.robots_meta or '').find('noindex')==-1 and (p.status_code or 0)<400)
    return {'indexable':idx,'non_indexable':len(pages)-idx}
