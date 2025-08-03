import re
import time

import litter
from .model import initialize_database, LtMessage


class LitterMonitor:
    def __init__(self, host: str, port: int, app_name: str = "LitterMonitor",
                 *, db_url: str | None = None, pattern: str = "*",
                 exclude_channels: list[str] | None = None
                 ):
        self.host = host
        self.port = port
        self.app_name = app_name
        self.pattern = pattern
        self.exclude_channels = [] if exclude_channels is None else [
            re.compile(channel.replace('.', r'\.').replace('*', '[a-zA-Z0-9]*') + r'$')
            for channel in exclude_channels
        ]

        litter.connect(self.host, self.port, app_name=self.app_name)
        self.sub_entity = litter.agent._redis_client.pubsub()
        self.sub_entity.psubscribe(self.app_name, pattern)

        if db_url:
            initialize_database(db_url)
            self.db_ready = True
        else:
            self.db_ready = False

    def message_handler(self, message: litter.Message):
        if any(pat.match(message.channel) for pat in self.exclude_channels):
            return
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        if self.db_ready:
            LtMessage.create(
                type=message.type,
                data=message.data,
                channel=message.channel,
                pattern=message.pattern,
            )

        print("Channel:", message.channel)
        try:
            o = message.data_obj
        except:
            print(message)
        else:
            # headers
            print(*(f"{k}: {v}" for k, v in message.headers.items()), sep="\n")

            # body
            try:
                print(message.json())
            except:
                print(message.data)
        print()

    def run(self):
        for message in self.sub_entity.listen():
            self.message_handler(litter.Message.from_redis_message(message))
