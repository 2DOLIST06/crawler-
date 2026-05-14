from bs4 import BeautifulSoup

def parse_html(html: str):
    s = BeautifulSoup(html, "html.parser")
    links = [a.get("href") for a in s.select("a[href]")]
    resources=[]
    for tag, attr, typ in [("img","src","image"),("script","src","script"),("link","href","style")]:
        for el in s.find_all(tag):
            if el.get(attr): resources.append({"url":el.get(attr),"tag":tag,"attr":attr,"type":typ})
    title = s.title.text.strip() if s.title and s.title.text else None
    md = s.find("meta", attrs={"name":"description"})
    canon = s.find("link", attrs={"rel":lambda v:v and 'canonical' in v})
    h1s=s.find_all('h1')
    return {"title":title,"meta_description":md.get('content') if md else None,"canonical":canon.get('href') if canon else None,"h1":h1s[0].get_text(strip=True) if h1s else None,"h1_count":len(h1s),"h2_count":len(s.find_all('h2')),"word_count":len(s.get_text(' ',strip=True).split()),"links":links,"resources":resources}
