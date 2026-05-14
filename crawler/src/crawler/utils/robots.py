from urllib import robotparser


def can_fetch(url: str, user_agent: str) -> bool:
    parsed = __import__('urllib.parse').parse.urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = robotparser.RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
        return rp.can_fetch(user_agent, url)
    except Exception:
        return True
