import math

from loguru import logger
from requests import post

from litter.adapt import agent, FromConfig
from mmt.api.ntfy import NtfyApi


@agent("mmt.agent.ntfy", init_args=(FromConfig("ntfy/url"),))
class NtfyAgent(NtfyApi):
    def __init__(self, server_url: str, max_len: int = 1250):
        self.server_url = server_url
        self.max_len = max_len

    def _publish(self, topic: str, message: str, **kwargs):
        data = {"topic": topic, "message": message, **kwargs}
        logger.debug(f"发送ntfy通知：{data}")
        resp = post(self.server_url, json=data)
        if resp.status_code != 200:
            logger.error(f"发送ntfy通知失败：{resp.status_code=}; {resp.text=}; {data=}")

    def _split_message(self, message: str) -> list[str]:
        if len(message) > self.max_len:
            num_part = math.ceil(len(message) / self.max_len)
            return [
                "Part {}/{}\n{}".format(
                    part + 1,
                    num_part,
                    message[part * self.max_len:(part + 1) * self.max_len]
                ) for part in range(num_part)
            ]
        else:
            return [message]

    def publish(self, topic: str, message: str, **kwargs):
        parts = self._split_message(message)
        if len(parts) > 1:
            logger.warning(f"消息过长（{len(message)}字符）拆分为{len(parts)}条发送")
        for part in parts:
            self._publish(topic, part, **kwargs)
