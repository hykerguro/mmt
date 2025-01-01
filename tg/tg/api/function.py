import litter


def send_message(entity, message: str = '', **kwargs):
    resp = litter.request("tg.send_message", {"entity": entity, "message": message, **kwargs})
    return resp.body


def send_file(entity, file: str | bytes | list[str | bytes], **kwargs):
    resp = litter.request("tg.send_file", {"entity": entity, "file": file, **kwargs})
    return resp.body


def get_handler(condition, callback):
    def _hander(message: litter.Message):
        message = message.json()
        if condition(message):
            callback(message)

    return _hander
