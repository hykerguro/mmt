from litter.adapt import api
from . import APP_NAME


@api(APP_NAME)
def http_get(url: str, *args, **kwargs) -> bytes | None:
    ...


@api(APP_NAME)
def get_forum_threads(thread_url: str) -> list[dict]:
    ...
