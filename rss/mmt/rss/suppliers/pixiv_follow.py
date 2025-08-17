import datetime
from datetime import datetime

from loguru import logger

from mmt.agents import api
from mmt.rss import AbstractSupplier, MmtItem


class PixivFollowSupplier(AbstractSupplier):
    @property
    def name(self) -> str:
        return "Pixiv Follow"

    def supply(self) -> list[MmtItem]:
        try:
            ret = api.follow_latest_illust()
            logger.debug(f"Pixiv Follow supply: {ret}")
            return [MmtItem(
                id=illust['id'],
                title=illust['title'],
                description=illust['description'],
                link=f"https://www.pixiv.net/artworks/{illust['id']}",
                author=illust['userName'],
                image="/resolve?url=" + illust['url'],
                pub_date=datetime.strptime(illust['createDate'], '%Y-%m-%dT%H:%M:%S%z'),
            ) for illust in ret['thumbnails']['illust']]
        except Exception as e:
            logger.error(e)
            return []

    def resolve(self, url: str) -> bytes | None:
        return api.resolve(url)


supplier = PixivFollowSupplier()
