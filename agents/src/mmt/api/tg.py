from typing import Any, overload

from .framework import ApiBase, api


@api("mmt.agent.tg")
class TelegramApi(ApiBase):
    def send_message(self, message):
        ...

    @overload
    def download_media(self, document: dict[str, Any], file: str) -> None:
        ...

    @overload
    def download_media(self, document: dict[str, Any], file: None = None) -> None:
        ...

    def download_media(self, document: dict[str, Any], file: str | None = None) -> None:
        ...

    def get_message(self, *args, **kwargs) -> list[dict]:
        ...
