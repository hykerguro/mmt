import asyncio
import time
from typing import Sequence, Mapping, TypeAlias

import telethon.tl.patched
from loguru import logger
from telethon import Button
from telethon import TelegramClient, events
from telethon.tl.types import User

import litter
from heartbeat.agent import beat_bg

__all__ = [
    "get_me",
    "get_client"
]

client: TelegramClient | None = None
loop: asyncio.AbstractEventLoop | None = None
me: User | None = None


class CoroTimeoutException(Exception):
    pass


def get_client():
    global client
    if client is None:
        _init_client(config.get("tg/auth"))
    return client


def get_me(force: bool = False) -> User:
    global me
    if force or me is None:
        me = _get_loop().run_until_complete(client.get_me())
    return me


def _get_loop():
    global loop
    if loop is None:
        loop = get_client().loop
    return loop


def _init_client(tg_conf: dict[str, int | str]) -> TelegramClient:
    global client, me, loop
    tg_conf = tg_conf.copy()
    bot_token = tg_conf.pop("bot_token", None)
    client = TelegramClient(**tg_conf).start(bot_token=bot_token)
    loop = client.loop
    get_me(force=True)
    return client


@logger.catch
async def message_dispatcher(event: events.NewMessage.Event):
    message: telethon.tl.patched.Message = event.message
    dm = message.to_dict()
    litter.publish("tg.message.receive", dm)


@logger.catch
async def callback_query_dispatcher(event: events.CallbackQuery.Event):
    query = event.query
    litter.publish("tg.callbackquery.receive", query.to_dict())


def _tlobjec2dict(obj):
    if isinstance(obj, Sequence):
        return [_tlobjec2dict(x) for x in obj]
    elif isinstance(obj, Mapping):
        return {k: _tlobjec2dict(v) for k, v in obj.items()}
    elif isinstance(obj, telethon.tl.TLObject):
        return obj.to_dict()


def sleep_util_complete(coro, *, timeout=5, eps=0.05):
    f = asyncio.run_coroutine_threadsafe(coro, _get_loop())
    t = 0
    while not f.done() and t < timeout:
        time.sleep(eps)
        t += eps

    if t < timeout:
        return _tlobjec2dict(f.result())
    else:
        raise CoroTimeoutException()


_BUTTON_EXPR: TypeAlias = dict[str, str]


def build_button(buttons: _BUTTON_EXPR | list[_BUTTON_EXPR] | list[list[_BUTTON_EXPR]]):
    """
    {
        "type": "text"/"url",
        "data": ...,
        other args: ...
    }
    :param buttons:
    :return:
    """
    if isinstance(buttons, dict):
        assert buttons["type"] in ("inline", "url")
        return getattr(Button, buttons["type"])(**{k: v for k, v in buttons.items() if k != "type"})
    elif isinstance(buttons, list):
        return [build_button(button) for button in buttons]


@litter.subscribe("tg.send_message")
def ltcmd_send_message(message: litter.Message):
    kwargs = message.json()
    if "buttons" in kwargs:
        kwargs["buttons"] = build_button(kwargs["buttons"])
    return sleep_util_complete(get_client().send_message(**kwargs))


@litter.subscribe("tg.send_file")
def ltcmd_send_file(message: litter.Message):
    kwargs = message.json()
    if "buttons" in kwargs:
        kwargs["buttons"] = build_button(kwargs["buttons"])
    return sleep_util_complete(get_client().send_file(**kwargs))


@litter.subscribe("tg.delete_message")
def ltcmd_delete_message(message: litter.Message):
    return sleep_util_complete(get_client().delete_messages(**message.json()))


if __name__ == '__main__':
    # 配置
    from confctl import config, util

    util.default_arg_config_loggers("tg/logs")

    # liiter初始化
    host, port = config.get("redis/host"), config.get("redis/port")
    litter.listen_bg(host, port, app_name="tg")
    beat_bg()

    # telethon初始化
    _init_client(config.get("tg/auth"))
    logger.info(f"Current user: {get_me().username}")
    client.add_event_handler(message_dispatcher, events.NewMessage(incoming=True))
    client.add_event_handler(callback_query_dispatcher, events.CallbackQuery())
    client.run_until_disconnected()
