from typing import Any

import litter
from litter.model import Response
from .model import TgApiException


def _extract(resp: Response):
    if resp.success:
        return resp.body
    else:
        raise TgApiException(f"{resp.exception_type}: {resp.exception_message}")


def send_message(entity, message: str = '', **kwargs) -> dict[str, Any]:
    return _extract(litter.request("tg.send_message", {"entity": entity, "message": message, **kwargs}))


def send_file(entity, file: str | bytes | list[str | bytes], **kwargs) -> dict[str, Any]:
    return _extract(litter.request("tg.send_file", {"entity": entity, "file": file, **kwargs}))


def get_handler(condition, callback):
    def _hander(message: litter.Message):
        message = message.json()
        if condition(message):
            callback(message)

    return _hander
