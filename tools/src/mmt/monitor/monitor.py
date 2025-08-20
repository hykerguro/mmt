import json
import re
import time
from typing import Any

from loguru import logger

import litter
from .model import initialize_database, LtMessage


def truncate(s: str, length: int, postfix: str) -> str:
    assert length > len(postfix)
    return s if len(s) <= length else s[:length - len(postfix)] + postfix

class LitterMonitor:
    def __init__(self, redis_credentials: dict[str, Any], app_name: str = "LitterMonitor", *, db_url: str | None = None,
                 pattern: str = "*", exclude_channels: list[str] | None = None, data_truncate: int = 4000):
        super().__init__()
        self.redis_credentials = redis_credentials
        self.app_name = app_name
        self.pattern = pattern
        self.data_truncate = data_truncate
        self.exclude_channels = [] if exclude_channels is None else [
            re.compile(channel.replace('.', r'\.').replace('*', '[a-zA-Z0-9]*') + r'$')
            for channel in exclude_channels
        ]

        if db_url:
            initialize_database(db_url)
            self.db_ready = True
        else:
            self.db_ready = False

    def message_handler(self, message: litter.Message):
        if any(pat.match(message.channel) for pat in self.exclude_channels):
            return

        lines = [
            "",
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "Channel: " + message.channel
        ]

        try:
            message.data_obj()
        except:
            lines.append(str(message))
        else:
            # headers
            lines.append("\n".join(*(f"{k}: {v}" for k, v in message.headers.items())))

            # body
            try:
                lines.append(json.dumps(message.json(), indent=4, ensure_ascii=False))
            except:
                lines.append(str(message.data))
        text = truncate("\n".join(lines), self.data_truncate, "<truncated>")
        logger.info(text)

        if self.db_ready:
            LtMessage.create(
                type=message.type,
                data=text,
                channel=message.channel,
                pattern=message.pattern,
            )

    def run(self):
        litter.connect(app_name=self.app_name, **self.redis_credentials)
        self.sub_entity = litter.agent._redis_client.pubsub()
        self.sub_entity.psubscribe(self.app_name, self.pattern)

        while True:
            try:
                message = self.sub_entity.get_message(timeout=0.5)
                if message is None:
                    continue
                self.message_handler(litter.Message.from_redis_message(message))
            except KeyboardInterrupt:
                litter.disconnect()
                break
