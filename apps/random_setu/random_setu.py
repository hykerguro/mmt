from apscheduler.schedulers.blocking import BlockingScheduler
from loguru import logger
from peewee import fn

import litter
# from tg import send_file, TgApiException, send_message
import tg
from confctl import config, util
from heartbeat.agent import beat_bg
from litter.model import LitterRequestTimeoutException
from pixiv_webapi import PixivWebAPI

try:
    from .model import Setu, ViewHistory, initialize_database
except ImportError:
    from model import Setu, ViewHistory, initialize_database

papi: PixivWebAPI | None = None

SETU_KEYWORDS: list[str] | None = None


def get_random_recommend(userId: str):
    recent_setus = Setu.select().order_by(Setu.income_time.desc()).limit(100)
    viewed = ViewHistory.select(ViewHistory.setuId).where(ViewHistory.userId == userId)
    setu = recent_setus.where(Setu.id.not_in(viewed)).order_by(fn.Rand()).limit(1).first()
    return setu


@litter.subscribe("tg.message.receive")
def handle_message(message: litter.Message):
    msg = message.json()
    if any(kw in msg["message"] for kw in SETU_KEYWORDS):
        userId = msg["peer_id"]["user_id"]
        logger.info(f"收到来自{userId}的消息：{msg['message']}")

        prev_msg = tg.send_message(userId, "小派蒙正在搜索涩图 ...")

        setu = get_random_recommend(userId)
        if setu is None:
            tg.send_message(userId, f"涩图被派蒙吃光了")
            tg.delete_message(userId, prev_msg["id"])
            return

        logger.debug(f"发送setu: {setu}")
        url = setu.preview_url
        page = setu.page if setu.page else f"https://www.pixiv.net/artworks/{setu.id}"
        lines = [
            f'title: [{setu.title}]({page})',
            f'artist: [{setu.artist_name}]({setu.artist_url})',
            "tags: " + ", ".join(('#' + x for x in setu.tags_data)),
        ]
        if setu.ai_type == '2':
            lines.append(f"#AI生成")

        # 点击Button发送原图
        try:
            tg.send_file(userId, url, caption='\n'.join(lines))
        except (LitterRequestTimeoutException, tg.TgApiException) as e:
            logger.error(e)
            tg.send_message(userId, f"涩图被派蒙没收了")
        else:
            ViewHistory.create(
                userId=userId,
                setuId=setu.id,
            )
        finally:
            tg.delete_message(userId, prev_msg["id"])


def main():
    global papi, SETU_KEYWORDS
    SETU_KEYWORDS = config.get("random_setu/keywords")

    initialize_database(config.get("db_url"))
    papi = PixivWebAPI(config.get("pixiv_webapi/token"))

    host, port = config.get("redis/host"), config.get("redis/port")
    litter.listen_bg(host, port, "random_setu")
    beat_bg()

    BlockingScheduler().start()


if __name__ == '__main__':
    util.default_arg_config_loggers("random_setu/logs")
    main()
