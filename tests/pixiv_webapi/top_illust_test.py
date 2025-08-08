import json

from confctl import config, util
from pixiv_webapi import PixivWebAPI

util.default_arg_config_loggers("pixiv_webapi/logs")

api = PixivWebAPI(config.get("pixiv_webapi/php_session_id"), config.get("pixiv_webapi/csrf_token"))

result = api.top_illust()
with open("assets/pixiv_webapi_json/top_illust.json", "w", encoding='utf8') as f:
    json.dump(result, f, ensure_ascii=False, indent=4)
