import re

from bs4 import BeautifulSoup
from loguru import logger
from requests import Session


class ZodgameAgent:
    base_url = 'https://zodgame.xyz'
    uid: str
    name: str

    def __init__(self, cookies: str | None = None, proxies: dict[str, str] | None = None):
        self.session = Session()
        self.session.headers["User-Agent"] = \
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0"
        if cookies is not None:
            self.authorize(cookies)

        if proxies is not None:
            self.session.proxies = proxies

    def http_get(self, url: str, *args, **kwargs) -> bytes | None:
        if not url.startswith('http'):
            url = self.base_url + "/" + url.lstrip('/')
        logger.debug(f">>> GET {url}")
        resp = self.session.get(url)
        logger.debug(f"<<< {resp.status_code}")
        resp.raise_for_status()
        return resp.content

    def http_post(self, url: str, body: bytes | dict | None = None):
        pass

    def authorize(self, cookies: str):
        for kv in cookies.split(";"):
            k, v = kv.strip().split("=")
            self.session.cookies.set(k, v)
            if k == "qhMq_2132_st_t":
                self.uid, _ = v.split("%", maxsplit=1)

    def health_check(self) -> bool:
        if self.uid is None:
            return False
        resp = self.http_get(f"home.php?mod=space&uid={self.uid}")
        return f"(UID: {self.uid})" in resp.decode("utf-8")

    def get_forum_threads(self, thread_url: str) -> list[dict]:
        resp = self.http_get(thread_url)
        soup = BeautifulSoup(resp, "lxml")
        posts = soup.find("ul", id="waterfall").find_all("li")
        result = []
        for post in posts:
            title = post.find("a")["title"].strip()
            author = post.find("div", class_="auth").a.text.strip()
            url = self.base_url + "/" + post.a["href"].strip()
            tid = re.search(r'tid=(\d+)', url).group(1)
            image_url = post.find("img")["src"].strip()
            if not image_url.startswith("http"):
                image_url = "https://zodgame.xyz/" + image_url

            result.append(dict(id=tid, title=title, link=url, image=image_url, author=author))
        return result
