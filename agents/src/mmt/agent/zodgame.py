import re
from datetime import datetime
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from loguru import logger
from pathvalidate import sanitize_filename
from requests import Session

from litter.adapt import agent, FromConfig
from mmt.api.zodgame import ZodgameApi


def parse_datetime(s: str) -> datetime:
    formats = [
        "%Y-%m-%d %H:%M:%S",  # 2024-05-16 20:39:49
        "%Y-%m-%d %H:%M",  # 2026-08-16 00:36
        "%Y-%m-%d",  # 2024-05-16
        "%Y/%m/%d %H:%M:%S",  # 2024/05/16 20:39:49
        "%Y/%m/%d %H:%M",  # 2024/05/16 20:39
        "%Y/%m/%d",  # 2024/05/16
        "%Y.%m.%d %H:%M:%S",  # 2024.05.16 20:39:49
        "%Y.%m.%d %H:%M",  # 2024.05.16 20:39
        "%Y.%m.%d",  # 2024.05.16
    ]

    for fmt in formats:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析日期时间字符串: {s}")


@agent(
    "mmt.agent.zodgame",
    init_args=(FromConfig("zodgame/cookies"),),
    init_kwargs=dict(debug=FromConfig("zodgame/debug", False), dump_path=FromConfig("zodgame/dump_path", None))
)
class ZodgameAgent(ZodgameApi):
    base_url = 'https://zodgame.xyz'
    uid: str
    name: str

    def __init__(self, cookies: str | None = None, proxies: dict[str, str] | None = None,
                 *, debug: bool = False, dump_path: Path = Path('.')) -> None:
        self.session = Session()
        self.session.headers["User-Agent"] = \
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0"
        if cookies is not None:
            self.authorize(cookies)

        if proxies is not None:
            self.session.proxies = proxies
            logger.debug(f"proxy: {self.session.proxies}")

        self.debug = debug
        self.dump_path = None if dump_path is None else Path(dump_path)
        if self.debug:
            logger.info(f"debug mode: on, dump path: {self.dump_path}")

    def _request(self, method: str, url: str, *args, **kwargs) -> bytes:
        if not url.startswith('http'):
            url = self.base_url + "/" + url.lstrip('/')
        kwargs.setdefault("allow_redirects", True)
        logger.debug(f">>> {method.upper()} {url}")
        resp = self.session.request(method, url, *args, verify=False, **kwargs)
        logger.debug(f"<<< {resp.status_code}")
        resp.raise_for_status()
        if url.startswith(self.base_url) and self.debug:
            self.dump_path.mkdir(parents=True, exist_ok=True)
            tp = self.dump_path / f"{sanitize_filename(url[len(self.base_url) + 1:], replacement_text='_')}.html"
            tp.write_bytes(resp.content)
            logger.debug(f"Response dumped to {tp}")
        return resp.content

    def http_get(self, url, **kwargs) -> bytes:
        return self._request(method="GET", url=url, **kwargs)

    def http_post(self, url, **kwargs) -> bytes:
        return self._request(method="POST", url=url, **kwargs)

    def authorize(self, cookies: str) -> None:
        logger.info("Authorizing ZodgameAgent with cookies")
        for kv in cookies.split(";"):
            k, v = kv.strip().split("=")
            self.session.cookies.set(k, v)
            if k == "qhMq_2132_st_t":
                self.uid, _ = v.split("%", maxsplit=1)

    def health_check(self) -> tuple[bool, str]:
        info = self.home_space()
        return info is not None, info["name"]

    def get_forum_threads(self, thread_url: str) -> list[dict]:
        assert thread_url.startswith(f"{self.base_url}/forum.php")
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
                image_url = self.base_url + "/" + image_url

            result.append(dict(id=tid, title=title, link=url, image=image_url, author=author))
        return result

    def get_view_thread(self, tid: str | int) -> dict[str, Any]:
        url = f"/forum.php?mod=viewthread&tid={tid}"
        resp = self.http_get(url)

        o = {
            "tid": tid,
            "title": "",
            "type": {
                "id": "",
                "name": "",
            },
            "author": {
                "uid": "",
                "name": ""
            },
            "content": "",
            "content_html": "",
            "locked": {
                # "buyers": 0,
                # "price": 0,
                # "expire_at": None,
            },
            "datetime": None,  # datetime
            "posts": [
                # {
                #     "id": "",
                #     "content": "",
                #     "author": {
                #         "uid": "",
                #         "name": ""
                #     },
                #     "datetime": None, # datetime
                # }
            ]
        }
        soup = BeautifulSoup(resp, "lxml")
        o["title"] = soup.find("span", id="thread_subject").text.strip()
        type_a = soup.find("h1", class_="ts").a
        o["type"]["name"] = type_a.text.strip()[1:-1]
        o["type"]["id"] = type_a["href"].rsplit("=", maxsplit=1)[-1]
        postlist_divs = soup.select('div#postlist>div[id^="post_"]')
        posts = []
        for post_div in postlist_divs:
            post = dict()
            post["id"] = post_div["id"][5:]

            auth_i_a = post_div.select_one("div.authi:first-of-type>a")
            uid = auth_i_a["href"].strip().rsplit("=", maxsplit=1)[-1]
            name = auth_i_a.text.strip()
            post["author"] = dict(uid=uid, name=name)

            content = post_div.select_one("td.t_f")
            if content is None:
                content = post_div.select_one(".pct")
                locked = content.select_one(".locked").text.strip()
                locked = locked.replace("\n", "")
                groups = re.search(r'.+(\d+) *人购买.+(\d+) *瓶酱油.+截止日期为 *(.+)，到期', locked).groups()
                post["locked"] = dict(buyers=int(groups[0]), price=int(groups[1]), expire_at=parse_datetime(groups[2]))
            else:
                post["locked"] = None
            post["content"] = content.text.strip()
            post["content_html"] = str(content)

            dt_em_span = post_div.select_one("div.authi>em>span")
            if dt_em_span:
                dt_str = post_div.select_one("div.authi>em>span")["title"].strip()
            else:
                dt_str = post_div.select_one("div.authi>em").text.strip()[4:]
            post["datetime"] = parse_datetime(dt_str)

            posts.append(post)

        o["author"] = posts[0]["author"]
        o["content"] = posts[0]["content"]
        o["content_html"] = posts[0]["content_html"]
        o["datetime"] = posts[0]["datetime"]
        o["posts"] = posts[1:]
        return o

    def home_space(self, uid: str | int = None) -> dict[str, Any]:
        if uid is None:
            uid = self.uid
        url = f"/home.php?mod=space&uid={uid}"
        resp = self.http_get(url)
        soup = BeautifulSoup(resp, "lxml")
        return {
            "uid": uid,
            "name": soup.select_one("h2.mt").text.strip(),
            "avatar": soup.select_one("#uhd img")["src"]
        }

    def user_threads(self, uid: str | int) -> list[dict[str, Any]]:
        url = f"/home.php?mod=space&uid={uid}&do=thread&view=me&from=space&type=thread"
        resp = self.http_get(url)
        soup = BeautifulSoup(resp, "lxml")
        o = [
            # {
            #     "tid": "",
            #     "title": "",
            #     "field": {
            #         "fid": "",
            #         "name": "",
            #     },
            #     "reply": 0,
            #     "view": 0
            # }
        ]
        trs = soup.find("div", id="ct").find_all("tr")[1:]
        for tr in trs:
            t = {}
            ta = tr.select_one("th>a")
            t["tid"] = ta["href"].strip().rsplit("=", maxsplit=1)[-1]
            t["title"] = ta.text.strip()

            txg = tr.select_one(".xg1")
            t["field"] = {
                "fid": txg["href"].strip().rsplit("=", maxsplit=1)[-1],
                "name": txg.text.strip(),
            }

            td_num = tr.select_one(".num")
            t["reply"] = int(td_num.a.text.strip())
            t["view"] = int(td_num.em.text.strip())

            o.append(t)

        return o
