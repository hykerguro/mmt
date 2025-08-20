from .framework import ApiBase, api


@api("mmt.agent.zodgame")
class ZodgameApi(ApiBase):
    def http_get(self, url, **kwargs) -> bytes:
        ...

    def http_post(self, url, **kwargs) -> bytes:
        ...

    def get_forum_threads(self, thread_url: str) -> list[dict]:
        ...
