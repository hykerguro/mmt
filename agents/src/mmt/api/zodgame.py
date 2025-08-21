from typing import Any

from .framework import ApiBase, api


@api("mmt.agent.zodgame")
class ZodgameApi(ApiBase):
    def http_get(self, url, **kwargs) -> bytes:
        ...

    def http_post(self, url, **kwargs) -> bytes:
        ...

    def get_forum_threads(self, thread_url: str) -> list[dict]:
        ...

    def get_view_thread(self, tid: str | int) -> dict[str, Any]:
        ...

    def home_space(self, uid: str | int = None) -> dict[str, Any]:
        ...

    def user_threads(self, uid: str | int) -> list[dict[str, Any]]:
        ...
