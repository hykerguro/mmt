import math

from loguru import logger
from requests import post

from confctl import config, util

__all__ = [
    "listen_litter"
]

URL: str | None = None

MESSAGE_MAX_LEN = 2000

def init():
    global URL
    URL = config.get("ntfy/url")
    return URL


def publish(topic: str, message: str, **kwargs) -> None:
    def _publish(topic, message, **kwargs):
        data = {"topic": topic, "message": message, **kwargs}
        logger.debug(f"发送ntfy通知：{data}")
        resp = post(URL or init(), json=data)
        if resp.status_code != 200:
            logger.error(f"发送ntfy通知失败：{resp.status_code=}; {resp.text=}; {data=}")

    if len(message) > MESSAGE_MAX_LEN:
        num_part = math.ceil(len(message) / MESSAGE_MAX_LEN)
        logger.warning(f"Message too long: {len(message)} characters, seperated to {num_part} messages")
        for part in range(num_part):
            part_message = message[part * MESSAGE_MAX_LEN:(part + 1) * MESSAGE_MAX_LEN]
            _publish(topic, f"Part {part + 1}/{num_part}\n{part_message}", **kwargs)
        return
    else:
        _publish(topic, message, **kwargs)



def listen_litter(bg: bool = False):
    """
    需要从confctl.config中读取redis的host和port
    调用前确认已经初始化config
    :param bg: 是否以后台方式运行
    :return:
    """
    from litter import subscribe, Message, listen, listen_bg, connect
    host, port = config.get("redis/host"), config.get("redis/port")
    connect(host, port, "ntfy")

    @subscribe("ntfy.publish")
    def _publish(message: Message):
        data = message.json()
        if "topic" in data and "message" in data:
            publish(**data)
        else:
            raise ValueError(f"ntfy消息必须包含'topic'和'message'")
    
    try:
        from heartbeat.agent import beat_bg
        beat_bg("ntfy", host=host, port=port)
    except:
        pass
    (listen_bg if bg else listen)(host, port)


if __name__ == "__main__":
    util.default_arg_config_loggers("ntfy/logs")
    init()
    listen_litter(bg=False)
