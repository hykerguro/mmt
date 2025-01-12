import json
from datetime import datetime

import pytz
import requests.exceptions
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

import litter
from confctl import config, util
from heartbeat.agent import beat_bg
from pixiv_webapi.webapi import PixivWebAPI

try:
    from .model import SetuEntity, initialize_database
except ImportError:
    from model import SetuEntity, initialize_database

papi: PixivWebAPI | None = None

tz = pytz.timezone('Asia/Shanghai')


def illust2setudb(illust, phase: str, original_urls, meta) -> tuple[SetuEntity, bool]:
    url = None
    if "urls" in illust:
        if "1200x1200" in illust["urls"]:
            url = illust["urls"]["1200x1200"]  # from top_illust page
        elif "regular" in illust["urls"]:
            url = illust["urls"]["regular"]  # from illust page

    if url is None:
        illust = papi.illust(illust["id"])
        return illust2setudb(illust, phase, original_urls, meta)
    if illust["xRestrict"] == 2 or 'R18' in illust["tags"] or 'r18' in illust["tags"]:
        r18 = '2'
    else:
        r18 = illust["xRestrict"]

    if illust["aiType"] == 2 or "ai" in map(lambda s: s.lower(), illust["tags"]):
        ai_type = '2'
    else:
        ai_type = illust["aiType"]

    return SetuEntity.get_or_create(
        source="pixiv",
        phase=phase,
        id=illust["id"],
        page=f"https://www.pixiv.net/artworks/{illust['id']}",
        title=illust["title"],
        page_count=illust["pageCount"],
        preview_url=illust["urls"]["1200x1200"],
        original_url=json.dumps(original_urls, ensure_ascii=False),
        artist_name=illust["userName"],
        artist_url=f"https://www.pixiv.net/users/{illust['userId']}",
        create_time=datetime.fromisoformat(illust["createDate"]).astimezone(tz),
        r18=r18,  # 0-不确定；1-不是r18；2-是r18
        sl=illust["sl"],
        ai_type=ai_type,  # 0-不确定；1-不是AI生成；2-是AI生成
        real='1',
        tags=json.dumps(illust["tags"], ensure_ascii=False),
        meta=meta,
    )


def on_archive_fav(message: litter.Message):
    data = message.json()
    illust = data["illust"]
    logger.info(f"监听到新的 pixiv illust，准备入库 {illust['id']} {illust['title']}")

    original_urls = data["original_urls"]
    phase = {
        "pixiv_fav.archive_fav.partdone": "pixiv:fav",
        "pixiv_fav.archive_follow.partdone": "pixiv:follow",
    }[message.channel]
    setu, created = illust2setudb(illust, phase, original_urls, data)
    if created:
        logger.info(f"入库：{illust['id']} {illust['title']}")
        litter.publish("pixiv_scraper.store", {f: getattr(setu, f) for f in setu._meta.fields})
    else:
        logger.info(f"重复图片")


@logger.catch
def on_recommend():
    for mode in ("all", "r18"):
        logger.info(f"定时推荐: {mode}")
        data = papi.top_illust(mode)
        recommend_ids = data["page"]["recommend"]["ids"]
        infomap = {i["id"]: i for i in data["thumbnails"]["illust"]}
        illusts = [infomap[iid] for iid in recommend_ids if iid in infomap]
        phase = "pixiv:recommend_" + mode

        for illust in illusts:
            logger.info(f"定时推荐，准备入库 {illust['id']} {illust['title']}")
            try:
                pages = papi.illust_pages(illust["id"])
            except requests.exceptions.HTTPError as e:
                logger.error(f"{illust['id']} {illust['title']}入库失败：{e}")
                continue

            urls = [page["urls"]["original"] for page in pages]

            setu, created = illust2setudb(illust, phase, urls, {**illust, "original_urls": urls})
            if created:
                logger.info(f"入库{illust['id']} {illust['title']}")
                litter.publish("pixiv_scraper.store", {f: getattr(setu, f) for f in setu._meta.fields})
            else:
                logger.info(f"重复图片")


def main():
    global papi
    initialize_database(config.get("db_url"))
    papi = PixivWebAPI(config.get("pixiv_webapi/token"))

    host, port = config.get("redis/host"), config.get("redis/port")

    if bool(config.get("pixiv_scraper/on_fav", False)):
        logger.info("监听pixiv收藏")
        litter.subscribe("pixiv_fav.archive_fav.partdone", on_archive_fav)
    if bool(config.get("pixiv_scraper/on_follow", False)):
        logger.info("监听pixiv关注")
        litter.subscribe("pixiv_fav.archive_follow.partdone", on_archive_fav)

    litter.listen_bg(host, port, "pixiv_scraper")
    beat_bg()

    sc = BlockingScheduler()
    if config.get("pixiv_scraper/recommend_cron", None):
        sc.add_job(on_recommend, CronTrigger.from_crontab(config.get("pixiv_scraper/recommend_cron")),
                   next_run_time=datetime.now())
        logger.info("定时推荐")
    sc.start()


if __name__ == '__main__':
    util.default_arg_config_loggers("pixiv_scraper/logs")
    main()
