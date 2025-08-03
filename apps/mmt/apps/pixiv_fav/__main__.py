from argparse import ArgumentParser

from loguru import logger

import litter
from confctl import config, util
from .model import initialize_database

parser = ArgumentParser()
parser.add_argument('module', type=str, nargs='+', help='模块')
parser.add_argument('--once', action='store_true', help='执行一次')
parser.add_argument("-c", "--config_path", type=str, nargs="*", default='./config.json', help='配置文件路径')
args = parser.parse_args()
util.init_config(args)
util.init_loguru_loggers("pixiv_fav/logs")

initialize_database(config.get("db_url"))
logger.debug(f"数据库已配置")

host, port = config.get("redis/host"), config.get("redis/port")
litter.connect(host, port, app_name="pixiv_fav")

logger.debug(f"ntfy通知已配置")

from .archiver import PixivFavArchiver

if args.once:
    logger.info("只执行一次")
    if "fav" in args.module:
        PixivFavArchiver().archive_fav()
    if "follow" in args.module:
        PixivFavArchiver().archive_follow()
    exit(0)

from mmt.tools.schd.api import add_job
from . import agent

cron_expr = config.get("pixiv_fav/cron")

if "fav" in args.module:
    add_job("pixiv_fav.archive.fav", {}, "cron", crontab=cron_expr, replace_existing=True,
            id="pixiv_fav.archive.fav")
if "follow" in args.module:
    add_job("pixiv_fav.archive.follow", {}, "cron", crontab=cron_expr, replace_existing=True,
            id="pixiv_fav.archive.follow")

logger.info(f"定时执行：{cron_expr}")

agent.serve(host, port)
