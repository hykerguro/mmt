from pathlib import Path

from confctl import config
from mmt.agent.pixiv import PixivWebAPI

config.load_config("config/dev.yaml")

api = PixivWebAPI(
    config.get("pixiv_webapi/php_session_id"),
    config.get("pixiv_webapi/csrf_token"),
    debug=True
)

# r = api.download("https://i.pximg.net/img-original/img/2026/01/17/03/37/04/140023587_p0.jpg")
# print(len(r))
#
# api.save_img("https://i.pximg.net/img-original/img/2026/01/17/03/37/04/140023587_p0.jpg", "tmp.jpg")

meta = api.ugoira_meta(139535466)
api.save_img(meta["originalSrc"], Path("temp.gif"))
