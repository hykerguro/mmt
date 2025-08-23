from abc import ABC, abstractmethod
from typing import Mapping, Sequence
from urllib.parse import urlencode

from loguru import logger

from litter.adapt import FromConfig, config
from mmt.rss.model import Feed

__all__ = (
    "FeedSupplier",
    "feed_supplier",
    "FEEDS"
)


class FeedSupplier(ABC):
    channel: str
    server_url: str

    @abstractmethod
    def feed(self) -> Feed:
        pass

    def _url_adapt(self, url: str) -> str:
        return f"{self.server_url}/resolve/{self.channel}?{urlencode(dict(url=url))}"


FEEDS = {}


def feed_supplier(channel: str, *, init_args: Sequence | None = None, init_kwargs: Mapping | None = None):
    def _inner(cls):
        if channel in FEEDS:
            raise Exception(f"channel {channel} already exists")
        args = [arg() for arg in init_args if isinstance(arg, FromConfig)] if init_args else []
        kwargs = {k: (v() if isinstance(v, FromConfig) else v) for k, v in init_kwargs.items()} if init_kwargs else {}
        FEEDS[channel] = cls(*args, **kwargs)
        FEEDS[channel].channel = channel
        FEEDS[channel].server_url = config.get("rss/server_url")
        logger.info(f"added channel {channel}")

    return _inner
