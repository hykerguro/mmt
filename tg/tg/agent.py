import asyncio
import time

import telethon.tl.patched
from loguru import logger
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
async def _dispatcher(event: events.NewMessage.Event):
    message: telethon.tl.patched.Message = event.message
    dm = message.to_dict()
    litter.publish("tg.message.receive", dm)


async def _my_message_handler(event: events.NewMessage.Event):
    logger.debug(str(type(event)))
    message: telethon.custom.Message = event.message
    await get_client().send_message(message.peer_id, "1", reply_to=message)


def sleep_util_complete(coro, *, timeout=5, eps=0.05):
    f = asyncio.run_coroutine_threadsafe(coro, _get_loop())
    t = 0
    while not f.done() and t < timeout:
        time.sleep(eps)
        t += eps

    if t < timeout:
        return f.result().to_dict()
    else:
        raise CoroTimeoutException()


@litter.subscribe("tg.send_message")
def ltcmd_send_message(message: litter.Message):
    return sleep_util_complete(get_client().send_message(**message.json()))


@litter.subscribe("tg.send_file")
def ltcmd_send_file(message: litter.Message):
    return sleep_util_complete(get_client().send_file(**message.json()))


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
    client.add_event_handler(_dispatcher, events.NewMessage(incoming=True))
    client.add_event_handler(_my_message_handler, events.NewMessage(chats=me.id))
    client.run_until_disconnected()
