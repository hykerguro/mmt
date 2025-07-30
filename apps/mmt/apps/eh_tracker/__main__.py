from argparse import ArgumentParser

import litter

parser = ArgumentParser()
parser.add_argument('module', type=str, nargs='*', help='模块')
parser.add_argument('--once', action='store_true', help='执行一次')
parser.add_argument("-c", "--config_path", type=str, nargs="*", default='./config.json', help='配置文件路径')
args = parser.parse_args()
from confctl import config

for conf in args.config_path:
    config.load_config(conf, update=True)

from loguru import logger

for conf in config.get("eh_tracker/logs", []):
    print(f"log conf: {conf}")
    logger.add(**conf)
logger.debug(f"配置文件已加载：{config._root_config}")

import service
from model import initialize_database


def init_ntfy_inform(args):
    from ntfy.api import publish as notify

    @litter.subscribe("eh_tracker.track.updated")
    def updated_inform(message):
        data = message.json()
        notify(topic="mmt_updated", message='\n'.join(data["diffs"]), title=message.channel, tags=["updated"])


def track():
    updated_galleries = []
    for update in service.iter_all_galleries_update():
        if update is not None:
            gallery, diffs = update
            updated_galleries.append(gallery)
            logger.info(f"有更新： {gallery}")
            litter.publish("eh_tracker.track.updated", {
                "gid": gallery.gid, "token": gallery.token, "diffs": diffs})


def main():
    initialize_database(config.get("db_url"))
    logger.debug(f"数据库已配置")

    init_ntfy_inform(args)
    litter.connect(config.get("redis/host"), config.get("redis/port"), "eh_tracker")
    logger.debug(f"ntfy通知已配置")

    from eh_api import refresh_ds
    refresh_ds()

    if args.once:
        logger.info("只执行一次")
        if "fav" in args.module:
            service.track_fav()
        else:
            track()
    else:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger

        cron_expr = config.get("eh_tracker/cron")
        scheduler = BlockingScheduler()
        scheduler.add_job(
            track,
            CronTrigger.from_crontab(cron_expr),
        )
        logger.info(f"定时执行：{cron_expr}")
        try:
            from heartbeat.agent import beat_bg
            beat_bg()
        except ImportError:
            pass
        scheduler.start()


logger.catch(main)()
