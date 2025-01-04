from typing import Any

from apscheduler.schedulers.blocking import BlockingScheduler
from loguru import logger

import litter
import tg
from confctl import config, util
from heartbeat.agent import beat_bg
from pixiv_webapi import PixivWebAPI

try:
    from .model import Setu, ViewHistory, initialize_database, UserConfig
except ImportError:
    from model import Setu, ViewHistory, initialize_database, UserConfig

papi: PixivWebAPI | None = None

SETU_KEYWORDS: list[str] | None = None


def send_user_config(user_id: int):
    user_config = UserConfig.get_or_default(user_id).config_data
    lines = [
        '你的配置：',
        'AI生成：{}'.format(["可以看", "不看", "只看"][user_config["ai_type"]]),
        'R18：{}'.format(["可以看", "不看", "只看"][user_config["r18"]]),
    ]
    buttons = [
        [
            {"type": "inline", "text": "不看AI", "data": "ai_type=1"},
            {"type": "inline", "text": "只看AI", "data": "ai_type=2"},
            {"type": "inline", "text": "我全都要", "data": "ai_type=0"},
        ],
        [
            {"type": "inline", "text": "不看R18", "data": "r18=1"},
            {"type": "inline", "text": "只看R18", "data": "r18=2"},
            {"type": "inline", "text": "我全都要", "data": "r18=0"},
        ]
    ]

    if user_config["r18"] == 1:
        # 只看非r18，sl生效
        lines.append('涩度：{}'.format(user_config["sl"]))
        buttons.append([
            {"type": "inline", "text": "不咋色", "data": "sl=2"},
            {"type": "inline", "text": "有点涩", "data": "sl=4"},
            {"type": "inline", "text": "好色哦", "data": "sl=6"},
        ])
    tg.send_message(user_id, "\n".join(lines), buttons=buttons)


def send_random_setu(user_id: int):
    prev_msg = tg.send_message(user_id, "小派蒙正在搜索涩图 ...")
    try:
        ucf = UserConfig.get_or_default(user_id).config_data
        setu = Setu.get_random(user_id, **ucf)
        logger.debug(f'Find setu for {user_id} with config {ucf}: {setu}')
        if setu is None:
            tg.send_message(user_id, f"涩图被派蒙吃光了")
            tg.delete_message(user_id, prev_msg["id"])
            return

        url = setu.preview_url
        page = setu.page if setu.page else f"https://www.pixiv.net/artworks/{setu.id}"
        lines = [
            f'title: [{setu.title}]({page})',
            f'artist: [{setu.artist_name}]({setu.artist_url})',
            "tags: " + ", ".join(('#' + x for x in setu.tags_data)),
        ]
        if setu.ai_type == '2':
            lines.append(f"#AI生成")

        # TODO: 点击Button发送原图
        tg.send_file(user_id, url, caption='\n'.join(lines))
    except Exception as e:
        logger.error(e)
        tg.send_message(user_id, f"涩图被派蒙没收了")
    else:
        ViewHistory.create(
            user_id=user_id,
            setu_id=setu.id,
        )
    finally:
        tg.delete_message(user_id, prev_msg["id"])


@litter.subscribe("tg.callbackquery.receive")
def handle_callback_query(message: litter.Message):
    query = message.json()
    logger.debug(f'Received callback query: {query}')

    data = query["data"].decode("utf-8")
    user_id = query["user_id"]
    ucf: dict[str, Any] = UserConfig.get_or_default(user_id).config_data
    if data.startswith("ai_type="):
        ucf["ai_type"] = int(data.replace("ai_type=", ""))
    if data.startswith("r18="):
        ucf["r18"] = int(data.replace("r18=", ""))
    if data.startswith("sl="):
        ucf["sl"] = int(data.replace("sl=", ""))
    UserConfig.update_config(user_id, ucf)
    tg.delete_message(user_id, query["msg_id"])
    send_user_config(user_id)


@litter.subscribe("tg.message.receive")
def handle_message(message: litter.Message):
    msg = message.json()
    user_id = int(msg["peer_id"]["user_id"])
    logger.info(f"收到来自{user_id}的消息：{msg['message']}")
    if any(kw in msg["message"] for kw in SETU_KEYWORDS):
        send_random_setu(user_id)
    elif "配置" in msg["message"]:
        send_user_config(user_id)


@logger.catch
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
    args = util.default_arg_config_loggers("random_setu/logs", extra_arguments=[
        ["--only-init-database", dict(action="store_true", help="只执行数据库初始化")]
    ])
    if args.only_init_database:
        initialize_database(config.get("db_url"))
        logger.info(f"数据库初始化完成")
    else:
        main()
