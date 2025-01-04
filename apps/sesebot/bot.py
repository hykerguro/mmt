import random
from traceback import format_exc
from typing import Any

from apscheduler.schedulers.blocking import BlockingScheduler
from loguru import logger

import litter
import tg
from confctl import config, util
from heartbeat.agent import beat_bg
from pixiv_webapi import PixivWebAPI
from stashapi import StashAPI, GalleryFilterType, HierarchicalMultiCriterionInput, CriterionModifier, FindFilterType, \
    ImageFilterType, MultiCriterionInput, Image, Gallery

try:
    from .model import SetuEntity, ViewHistoryEntity, initialize_database, UserConfigEntity
except ImportError:
    from model import SetuEntity, ViewHistoryEntity, initialize_database, UserConfigEntity

papi: PixivWebAPI | None = None

SETU_KEYWORDS: list[str] | None = None


def get_random_real() -> tuple[Image, Gallery] | None:
    galleries = StashAPI.query_find_galleries(
        GalleryFilterType(tags=HierarchicalMultiCriterionInput(CriterionModifier.INCLUDES, value=[7], depth=0)),
        FindFilterType(per_page=1, sort=f"random_{random.randint(1, 2 << 31)}")
    ).galleries
    if len(galleries) == 0:
        return None
    logger.debug(f"Gallery: {galleries[0]}")
    images = StashAPI.query_find_images(
        ImageFilterType(galleries=MultiCriterionInput(CriterionModifier.INCLUDES_ALL, value=[galleries[0].id]))).images
    if len(images) == 0:
        return None
    image = random.choice(images)
    logger.debug(f"Image: {image}")
    return image, galleries[0]


def send_user_config(user_id: int):
    user_config = UserConfigEntity.get_or_default(user_id).config_data
    lines = [
        '你的配置:',
        'AI生成: {}'.format(["可以看", "不看", "只看"][user_config["ai_type"]]),
        'R18: {}'.format(["可以看", "不看", "只看"][user_config["r18"]]),
        '真人涩情: {}'.format(["可以看", "不看", "只看"][user_config["real"]])
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
        ],
        [
            {"type": "inline", "text": "不看真人涩情", "data": "real=1"},
            {"type": "inline", "text": "只看真人涩情", "data": "real=2"},
            {"type": "inline", "text": "我全都要", "data": "real=0"},
        ]
    ]

    if user_config["r18"] == 1 and user_config["real"] == 1:
        # 不看r18且不看真人涩情，sl生效
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
        ucf = UserConfigEntity.get_or_default(user_id).config_data
        real = ucf.get("real", 1)
        sel = random.random()
        logger.debug(f"User config: {ucf}; sel={sel}")

        if real == 2 or (real == 0 and sel < config.get("sesebot/flj/ratio", 0.1)):
            # 随机到真人涩图
            ret = get_random_real()

            if (ret is None or ViewHistoryEntity.select()
                    .where(ViewHistoryEntity.setu_source == "stash",
                           ViewHistoryEntity.setu_id == ret[0].id).first() is not None):
                tg.send_message(user_id, f"涩图被派蒙吃光了")
                tg.delete_message(user_id, prev_msg["id"])
                return
            setu, ginfo = ret
            url = setu.paths.thumbnail or setu.paths.image
            file = {
                "bytes": StashAPI.download_file(url),
                "name": setu.title
            }
            lines = [
                f'title: {setu.title}',
            ]
            try:
                lines.append("performs: " + ', '.join(p["name"] for p in ginfo.performers))
            except (AttributeError, KeyError):
                pass
            try:
                lines.append("tags: " + ", ".join('#' + x["name"] for x in ginfo.tags))
            except (AttributeError, KeyError):
                pass
            source = "stash"

        else:
            setu = SetuEntity.get_random(user_id, ucf)
            if setu is None:
                tg.send_message(user_id, f"涩图被派蒙吃光了")
                tg.delete_message(user_id, prev_msg["id"])
                return

            file = setu.preview_url
            page = setu.page if setu.page else f"https://www.pixiv.net/artworks/{setu.id}"
            lines = [
                f'title: [{setu.title}]({page})',
                f'artist: [{setu.artist_name}]({setu.artist_url})',
                "tags: " + ", ".join(('#' + x for x in setu.tags_data)),
            ]
            if setu.ai_type == '2':
                lines.append(f"#AI生成")
            source = "pixiv"

        logger.debug(f"Setu: {setu}, lines={lines}, source={source}")
        tg.send_file(user_id, file, caption='\n'.join(lines))
    except Exception as e:
        logger.error(format_exc())
        tg.send_message(user_id, f"涩图被派蒙没收了")
    else:
        ViewHistoryEntity.create(
            user_id=user_id,
            setu_id=setu.id,
            setu_source=source
        )
    finally:
        tg.delete_message(user_id, prev_msg["id"])


@litter.subscribe("tg.callbackquery.receive")
def handle_callback_query(message: litter.Message):
    query = message.json()
    logger.debug(f'Received callback query: {query}')

    data = query["data"].decode("utf-8")
    user_id = query["user_id"]
    ucf: dict[str, Any] = UserConfigEntity.get_or_default(user_id).config_data
    if data.startswith("ai_type="):
        ucf["ai_type"] = int(data.replace("ai_type=", ""))
    if data.startswith("r18="):
        ucf["r18"] = int(data.replace("r18=", ""))
    if data.startswith("sl="):
        ucf["sl"] = int(data.replace("sl=", ""))
    if data.startswith("real="):
        ucf["real"] = int(data.replace("real=", ""))
    UserConfigEntity.update_config(user_id, ucf)
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
    SETU_KEYWORDS = config.get("sesebot/keywords")

    initialize_database(config.get("db_url"))
    papi = PixivWebAPI(config.get("pixiv_webapi/token"))
    StashAPI.configure(config.get("stashapi/url"), config.get("stashapi/token"))

    host, port = config.get("redis/host"), config.get("redis/port")
    litter.listen_bg(host, port, "sesebot")
    beat_bg()

    BlockingScheduler().start()


if __name__ == '__main__':
    args = util.default_arg_config_loggers("sesebot/logs", extra_arguments=[
        ["--only-init-database", dict(action="store_true", help="只执行数据库初始化")]
    ])
    if args.only_init_database:
        initialize_database(config.get("db_url"))
        logger.info(f"数据库初始化完成")
    else:
        main()
