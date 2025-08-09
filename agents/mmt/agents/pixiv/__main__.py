from confctl import config, util
from . import APP_NAME

util.default_arg_config_loggers()

from litter.adapter import adapt
from .webapi import PixivWebAPI

adapt(
    PixivWebAPI(config.get("pixiv_webapi/php_session_id"), config.get("pixiv_webapi/csrf_token")),
    APP_NAME,
    bg=False
)

while True:
    pass
