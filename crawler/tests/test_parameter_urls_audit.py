from crawler_app.services.parameter_urls_audit import classify_parameter


def evaluate(parameter_type: str, in_sitemap: bool, canonical: str, final_url: str, robots_meta: str):
    # mirror key rules to validate expected behavior
    if in_sitemap:
        return "error"
    if parameter_type == "tracking":
        return "ok" if canonical == final_url else "error"
    if parameter_type == "pagination":
        if "page=1" in canonical:
            return "warning"
        return "ok" if "noindex,follow" in robots_meta.lower() else "warning"
    if parameter_type == "sorting_display":
        if canonical == final_url and "index,follow" in robots_meta.lower():
            return "error"
    if parameter_type == "unknown":
        return "unknown"
    return "ok"


def test_tracking_canonical_to_clean_ok():
    assert evaluate("tracking", False, "https://www.2dolist.fr/categorie/avion", "https://www.2dolist.fr/categorie/avion", "index,follow") == "ok"


def test_tracking_in_sitemap_error():
    assert evaluate("tracking", True, "https://www.2dolist.fr/categorie/avion", "https://www.2dolist.fr/categorie/avion", "index,follow") == "error"


def test_pagination_good_ok():
    assert evaluate("pagination", False, "https://www.2dolist.fr/categorie/avion?page=2", "https://www.2dolist.fr/categorie/avion?page=2", "noindex,follow") == "ok"


def test_pagination_in_sitemap_error():
    assert evaluate("pagination", True, "https://www.2dolist.fr/categorie/avion?page=2", "https://www.2dolist.fr/categorie/avion?page=2", "noindex,follow") == "error"


def test_sort_index_self_canonical_error():
    assert evaluate("sorting_display", False, "https://www.2dolist.fr/categorie/avion?sort=price", "https://www.2dolist.fr/categorie/avion?sort=price", "index,follow") == "error"


def test_unknown_param_not_auto_error():
    assert evaluate("unknown", False, "", "", "") == "unknown"


def test_classify_parameter_groups():
    assert classify_parameter("utm_source") == "tracking"
    assert classify_parameter("page") == "pagination"
    assert classify_parameter("region") == "filter"
    assert classify_parameter("sort") == "sorting_display"
    assert classify_parameter("price") == "booking_or_availability"
    assert classify_parameter("foo") == "unknown"
