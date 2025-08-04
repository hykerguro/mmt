from confctl import config, util

util.default_arg_config_loggers()
APP_NAME = "agent.pixiv"

from litter.adapter import adapt
from .webapi import PixivWebAPI

adapt(
    PixivWebAPI(config.get("pixiv_webapi/token")),
    APP_NAME,
    bg=False
)