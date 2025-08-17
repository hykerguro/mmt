from telethon.tl import types

from mmt.api.tg import TelegramApi
from . import client, me, sleep_util_complete


class TelegramAgent(TelegramApi):
    def send_message(self, message) -> types.Message:
        return sleep_util_complete(client().send_message(me().id, message))
