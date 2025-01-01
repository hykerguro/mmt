import asyncio

import telethon.tl.patched
from loguru import logger
from telethon import TelegramClient, events
from telethon.tl.types import User

import litter
from confctl import config
from heartbeat.agent import beat_bg

_lp = litter.publish
__all__ = [
    "send_message",
    "get_me",
    "get_client"
]

client: TelegramClient | None = None
loop: asyncio.AbstractEventLoop | None = None
me: User | None = None


def get_client():
    global client
    if client is None:
        _init_client(config.get("tg"))
    return client


def _get_loop():
    global loop
    if loop is None:
        loop = get_client().loop
    return loop


def get_me(force: bool = False) -> User:
    global me
    if force or me is None:
        me = _get_loop().run_until_complete(client.get_me())
    return me


def _init_client(tg_conf: dict[str, int | str]) -> TelegramClient:
    global client, me, loop
    tg_conf = tg_conf.copy()
    bot_token = tg_conf.pop("bot_token", None)
    client = TelegramClient(**tg_conf).start(bot_token=bot_token)
    loop = client.loop
    get_me(force=True)
    return client


async def send_message(*args, **kwargs):
    try:
        logger.info(f"发送Telegram消息：{args=}, {kwargs=}")
        result = await client.send_message(*args, **kwargs)
    except Exception as e:
        logger.error(f"发送Telegram消息失败：{e}")
        _lp("tg.send_message.fail", {"args": args, **kwargs, "exception": e})
        raise e
    else:
        _lp("tg.send_message.done", {"args": args, **kwargs, "result": result})


async def send_file(entity, file, *args, **kwargs):
    # if isinstance(file, list) and all(isinstance(e, str) for e in file):
    #     logger.info(f"all str file: {file}")
    #     fhs = []
    #     for url in file:
    #         r = await client.upload_file(url)
    #         fhs.append(r)
    #         logger.info(f"{url} uploaded")
    #
    #     logger.info(f"{len(file)} files uploaded: {fhs}")
    #     message = await client.send_file(entity, fhs, *args, **kwargs)
    #     logger.info(f"album sent: {message.to_dict()}")
    #     return

    try:
        logger.info(f"发送Telegram消息：{entity=}, {file=}, {args=}, {kwargs=}")
        result = await client.send_file(entity, file, *args, **kwargs)
    except Exception as e:
        logger.error(f"发送Telegram消息失败：{e}")
        _lp("tg.send_message.fail", {"args": args, **kwargs, "exception": e})
        raise e
    else:
        _lp("tg.send_message.done", {"args": args, **kwargs, "result": result})


@logger.catch
async def _dispatcher(event: events.NewMessage.Event):
    message: telethon.tl.patched.Message = event.message
    dm = message.to_dict()
    litter.publish("tg.message.receive", dm)


async def _my_message_handler(event: events.NewMessage.Event):
    logger.debug(str(type(event)))
    message: telethon.custom.Message = event.message
    await get_client().send_message(message.peer_id, "1", reply_to=message)


@litter.subscribe("tg.send_message")
def _ltcmd_send_message(message: litter.Message):
    asyncio.run_coroutine_threadsafe(send_message(**message.json()), _get_loop())


@litter.subscribe("tg.send_file")
def _ltcmd_send_file(message: litter.Message):
    asyncio.run_coroutine_threadsafe(send_file(**message.json()), _get_loop())


if __name__ == '__main__':
    # 配置
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("-c", "--config", help="config file")
    args = parser.parse_args()
    config.load_config(args.config)

    # liiter初始化
    host, port = config.get("redis/host"), config.get("redis/port")
    litter.listen_bg(host, port)
    litter.connect(host, port, app_name="tg")
    beat_bg()

    # telethon初始化
    _init_client(config.get("tg"))
    logger.info(f"Current user: {get_me().username}")
    client.add_event_handler(_dispatcher, events.NewMessage(incoming=True))
    client.add_event_handler(_my_message_handler, events.NewMessage(chats=me.id))
    client.run_until_disconnected()
