import asyncio
import time
from typing import Sequence, Mapping

import telethon
from telethon import TelegramClient
from telethon.tl.types import User

from confctl import config

_client: TelegramClient | None = None
_loop: asyncio.AbstractEventLoop | None = None
_me: User | None = None


def init_client() -> TelegramClient:
    global _client, _me, _loop
    tg_conf = config.get("tg/auth").copy()
    bot_token = tg_conf.pop("bot_token", None)
    _client = TelegramClient(**tg_conf).start(bot_token=bot_token)
    _loop = _client.loop
    _me = _loop.run_until_complete(_client.get_me())
    return _client


def me():
    return _me


def client():
    return _client


def loop():
    return _loop


def tlobjec2dict(obj):
    if isinstance(obj, Sequence):
        return [tlobjec2dict(x) for x in obj]
    elif isinstance(obj, Mapping):
        return {k: tlobjec2dict(v) for k, v in obj.items()}
    elif isinstance(obj, telethon.tl.TLObject):
        return obj.to_dict()
    return obj


def sleep_util_complete(coro, *, timeout=15, eps=0.05):
    assert _loop is not None, "init client before invoke"
    f = asyncio.run_coroutine_threadsafe(coro, _loop)
    t = 0
    while not f.done() and t < timeout:
        time.sleep(eps)
        t += eps

    if t < timeout:
        return tlobjec2dict(f.result())
    else:
        raise TimeoutError
