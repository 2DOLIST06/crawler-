from bs4 import BeautifulSoup

from crawler.models import ResourceRecord


def parse_html(html: str, source_url: str) -> dict:
    soup = BeautifulSoup(html or "", "html.parser")
    title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
    meta_desc = _meta(soup, "description")
    robots = _meta(soup, "robots")
    canonical = _link_rel(soup, "canonical")
    hreflangs = [link.get("href", "") for link in soup.select("link[rel='alternate'][hreflang]") if link.get("href")]
    h1 = [e.get_text(" ", strip=True) for e in soup.find_all("h1")]
    h2 = [e.get_text(" ", strip=True) for e in soup.find_all("h2")]
    links = []
    for a in soup.find_all("a"):
        links.append({"href": a.get("href", ""), "anchor_text": a.get_text(" ", strip=True), "rel": " ".join(a.get("rel", [])), "target": a.get("target", "")})
    resources = extract_resources(soup, source_url)
    words = len(soup.get_text(" ", strip=True).split())
    return {"title": title, "meta_description": meta_desc, "robots_meta": robots, "canonical": canonical, "hreflang_list": hreflangs, "h1_list": h1, "h2_list": h2, "links": links, "resources": resources, "word_count": words}


def extract_resources(soup: BeautifulSoup, source_url: str) -> list[ResourceRecord]:
    out = []
    for img in soup.find_all("img"):
        if img.get("src"): out.append(ResourceRecord(source_url=source_url, resource_url=img["src"], resource_type="image", tag_name="img", attribute_name="src"))
        if img.get("srcset"): out.append(ResourceRecord(source_url=source_url, resource_url=img["srcset"], resource_type="image_srcset", tag_name="img", attribute_name="srcset"))
    for s in soup.find_all("script"):
        if s.get("src"): out.append(ResourceRecord(source_url=source_url, resource_url=s["src"], resource_type="script", tag_name="script", attribute_name="src"))
    for l in soup.find_all("link"):
        rel = " ".join(l.get("rel", []))
        href = l.get("href")
        if not href: continue
        if "stylesheet" in rel: typ = "stylesheet"
        elif "preload" in rel: typ = "preload"
        elif "prefetch" in rel: typ = "prefetch"
        elif "canonical" in rel: typ = "canonical"
        elif "alternate" in rel and l.get("hreflang"): typ = "hreflang"
        else: continue
        out.append(ResourceRecord(source_url=source_url, resource_url=href, resource_type=typ, tag_name="link", attribute_name="href"))
    for prop in ["og:image", "twitter:image"]:
        for m in soup.find_all("meta", attrs={"property": prop}):
            if m.get("content"): out.append(ResourceRecord(source_url=source_url, resource_url=m["content"], resource_type=prop, tag_name="meta", attribute_name="content"))
    return out


def _meta(soup: BeautifulSoup, name: str) -> str:
    tag = soup.find("meta", attrs={"name": name})
    return tag.get("content", "").strip() if tag else ""


def _link_rel(soup: BeautifulSoup, rel: str) -> str:
    tag = soup.find("link", rel=rel)
    return tag.get("href", "").strip() if tag else ""
