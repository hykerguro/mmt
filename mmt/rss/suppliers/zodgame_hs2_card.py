from loguru import logger

from agents.zodgame import api
from ..supplier import Supplier, MmtItem


class HS2CardSupplier(Supplier):
    @property
    def name(self) -> str:
        return "HS2Card"

    def supply(self) -> list[MmtItem]:
        try:
            ret = api.get_forum_threads("forum.php?mod=forumdisplay&fid=108&filter=author&orderby=dateline")
            logger.debug(f"HS2Card supply: {ret}")
            return [MmtItem(**card) for card in ret]
        except Exception as e:
            logger.error(e)
            return []

    def resolve(self, url: str) -> bytes | None:
        return api.http_get(url)
