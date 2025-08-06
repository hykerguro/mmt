from . import APP_NAME

from confctl import config, util
util.default_arg_config_loggers()

from litter.adapter import adapt
from .webapi import PixivWebAPI

adapt(
    PixivWebAPI(config.get("pixiv_webapi/token")),
    APP_NAME,
    bg=False
)