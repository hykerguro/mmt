from confctl import config, util
from litter.adapter import adapt
from . import APP_NAME
from .webapi import PixivWebAPI

util.default_arg_config_loggers()
adapt(
    PixivWebAPI(config.get("pixiv_webapi/token")),
    APP_NAME,
    APP_NAME,
    host=config.get("redis/host"),
    port=config.get("redis/port"),
    bg=False
)
