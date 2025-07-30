import time

import litter
from .common import ConsoleAlert

__all__ = [
    "NtfyAlert"
]


class NtfyAlert(ConsoleAlert):
    def __init__(self, topic: str, host: str | None = None, port: int | None = None, app_name: str = None):
        self.host = host
        self.port = port
        self.topic = topic
        self.app_name = app_name or litter.get_appname()
        if host and port:
            litter.connect(host, port)
        from ntfy.api import TopicPublisher
        self.lp = TopicPublisher(topic)

    def _do_alert(self, message):
        self.lp.publish(message)
        self.last_alert = time.time()

    def __str__(self):
        return "NtfyAlert://{}/{}".format(f"{self.host}:{self.port}" if self.host and self.port else '', self.topic)
