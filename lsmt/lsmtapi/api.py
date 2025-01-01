import math
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from loguru import logger
from tqdm import tqdm

from confctl import config

HOME = "https://www.06se.com"
_SESS = requests.Session()


def init_session():
    global _SESS
    _SESS = requests.Session()
    _SESS.headers["User-Agent"] = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/5"
                                   "37.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0")


def get_session():
    global _SESS
    if _SESS is None:
        init_session()
    return _SESS


def download(url_or_article_id: str | int):
    url_or_article_id = str(url_or_article_id)
    if url_or_article_id.isdigit():
        page_url = f"{HOME}/{url_or_article_id}.html"
    elif url_or_article_id.startswith(HOME):
        page_url = url_or_article_id
    else:
        raise ValueError(f"{url_or_article_id} is neither a valid url not a valid article id")
    download_dir = config.get("lsmt/download_dir")

    resp = get_session().get(page_url)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    title = soup.select(
        "body > main > div.content-wrap > div > article > div.article-header.theme-box.clearfix.relative > h1 > a"
    )[0].text.strip()
    logger.debug(f"Title parsed: {title}")

    imgparent = soup.select(
        "article img"
    )
    logger.debug(f"imgparent: {imgparent}")

    urls = [p["data-src"] for p in imgparent]
    logger.info(f"Found {len(urls)} images, start downloading...")
    logger.debug(f"urls: {urls}")

    ddir = (Path(download_dir) / title)
    ddir.mkdir(parents=True, exist_ok=True)
    for i, url in tqdm(enumerate(urls), total=len(urls)):
        with open(ddir / f"{title}_{str(i).rjust(math.ceil(math.log10(len(urls) + 1)), '0')}.jpg", "wb") as f:
            f.write(get_session().get(url).content)


if __name__ == '__main__':
    from confctl.util import get_argparser, init_config

    parser = get_argparser()
    parser.add_argument("articles", nargs="+", type=str)
    args = parser.parse_args()

    init_config(args)

    for article in args.articles:
        download(article)
