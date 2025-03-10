from argparse import ArgumentParser

from loguru import logger

import litter
from confctl import config
from heartbeat.agent import beat_bg
from .model import initialize_database
from ntfy.api import publish as notify


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('module', type=str, nargs='+', help='模块')
    parser.add_argument('--once', action='store_true', help='执行一次')
    parser.add_argument("-c", "--config_path", type=str, nargs="*", default='./config.json', help='配置文件路径')
    return parser.parse_args()


def init_config_and_logger(args):
    for conf in args.config_path:
        config.load_config(conf, update=True)
    for conf in config.get("pixiv_fav/logs", []):
        print(f"log conf: {conf}")
        logger.add(**conf)
    logger.debug(f"配置文件已加载：{config._root_config}")


@litter.subscribe("pixiv_fav.archive_fav.done")
def done_inform(message):
    data = message.json()
    lines = [(f'{ill["title"]}\n\ttags: ' + ','.join(ill["tags"])) for ill in data["diff_illusts"]]
    notify(topic="mmt_done", message='\n'.join(lines), title=message.channel, tags=["done"])


@logger.catch
def main():
    args = parse_args()

    init_config_and_logger(args)

    initialize_database(config.get("db_url"))
    logger.debug(f"数据库已配置")

    host, port = config.get("redis/host"), config.get("redis/port")
    litter.connect(host, port, "pixiv_fav")

    logger.debug(f"ntfy通知已配置")

    from .archiver import PixivFavArchiver

    if args.once:
        logger.info("只执行一次")
        if "fav" in args.module:
            PixivFavArchiver().archive_fav()
        if "follow" in args.module:
            PixivFavArchiver().archive_follow()
    else:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger

        cron_expr = config.get("pixiv_fav/cron")
        scheduler = BlockingScheduler()
        if "fav" in args.module:
            scheduler.add_job(
                PixivFavArchiver().archive_fav,
                CronTrigger.from_crontab(cron_expr),
            )
        if "follow" in args.module:
            scheduler.add_job(
                PixivFavArchiver().archive_follow,
                CronTrigger.from_crontab(cron_expr),
            )
        logger.info(f"定时执行：{cron_expr}")
        beat_bg()
        scheduler.start()


main()
