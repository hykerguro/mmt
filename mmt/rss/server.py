from datetime import datetime
from urllib.parse import quote

import pytz
from fastapi import FastAPI, Response, Query, HTTPException
from feedgen.feed import FeedGenerator
from loguru import logger

import litter
from confctl import config
from .suppliers.pixiv_follow import PixivFollowSupplier
from .suppliers.zodgame_hs2_card import HS2CardSupplier

config.load_config("config/dev.yaml")
litter.connect(config.get('redis/host'), config.get('redis/port'), app_name='rss_server')

SUPPLIER_POOL = {
    "pixiv_follow": PixivFollowSupplier(),
    "hs2_card": HS2CardSupplier(),
}

app = FastAPI()


@app.get("/resolve")
def resolve_url(
        channel: str = Query(..., description="Channel"),
        url: str = Query(..., description="URL to resolve")
) -> Response:
    if channel not in SUPPLIER_POOL:
        raise HTTPException(status_code=404, detail="Channel not found")
    logger.info(f"Resolving {url} for {channel}")
    result = SUPPLIER_POOL.get(channel).resolve(url)
    if result is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return Response(content=result, media_type="application/octet-stream")


@app.get("/rss")
def generate_rss(channel: str = Query(..., description="Channel")) -> Response:
    if channel not in SUPPLIER_POOL:
        raise HTTPException(status_code=404, detail="Channel not found")
    supplier = SUPPLIER_POOL.get(channel)

    fg = FeedGenerator()
    fg.load_extension("media")
    fg.id(f"mmt.rss.{channel}")
    fg.title(supplier.name)
    fg.link(href=f"https://{config.get("rss/host")}/rss?channel={channel}", rel="alternate")
    fg.description(supplier.description())
    fg.language("zh-cn")
    fg.lastBuildDate(datetime.now(pytz.timezone("Asia/Shanghai")))

    for item in supplier.supply():
        print(item)
        fe = fg.add_entry()
        fe.id(f'{channel}_{item.id}')
        fe.title(item.title)
        fe.link(href=item.link)
        fe.pubDate(item.pub_date)
        fe.description(item.description)
        # Media RSS 扩展
        me = fe.media
        me.content(
            url=f"/resolve?channel={channel}&url={quote(item.image)}",
            type='image/jpeg',
            medium="image"
        )

    rss_str = fg.rss_str(pretty=True)
    return Response(content=rss_str, media_type="application/xml")
