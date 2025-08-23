from datetime import datetime
from zoneinfo import ZoneInfo

from loguru import logger

from mmt.api.zodgame import ZodgameApi
from mmt.rss.feed import FeedSupplier, feed_supplier
from mmt.rss.model import Feed, Item

TZ = ZoneInfo("Asia/Shanghai")

__all__ = [
    "ZodHs2CardFeedSupplier"
]


@feed_supplier("zod_hs2_card")
class ZodHs2CardFeedSupplier(FeedSupplier):
    channel: str

    def __init__(self):
        self.api = ZodgameApi.api()

    def feed(self) -> Feed:
        f = Feed("zodgame HS2存档专区", language="zh-cn", expired=False)
        threads = self.api.get_forum_threads(
            "https://zodgame.xyz/forum.php?mod=forumdisplay&fid=108&filter=lastpost&orderby=lastpost")
        logger.debug("threads: {}".format(threads))
        for thread in threads:
            thread_url = thread["link"]
            f.items.append(Item(
                id=thread_url,
                title=thread["title"],
                url=self._url_adapt(thread_url),
                external_url=thread_url,
                content_html='<img src="{}" /><h1>{}</h1><h1>{}</h1>'.format(
                    self._url_adapt(thread["image"]), thread["title"], thread["author"]),
                image=self._url_adapt(thread["image"]),
                date_published=datetime.now(TZ)
            ))

        return f

    def resolve(self, url: str) -> bytes:
        return self.api.http_get(url)
