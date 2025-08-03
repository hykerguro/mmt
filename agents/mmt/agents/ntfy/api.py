import re

import litter

__all__ = [
    "publish",
    "logger_handler",
    "PublishTemplate",
    "TopicPublisher"
]


def publish(topic: str, message: str, **kwargs):
    litter.publish("ntfy.publish", {"topic": topic, "message": message, **kwargs})


class PublishTemplate:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def publish(self, **kwargs):
        param = self.kwargs.copy()
        param.update(kwargs)
        return publish(**param)


class TopicPublisher(PublishTemplate):
    def __init__(self, topic: str):
        super().__init__(topic=topic)

    def publish(self, message: str, **kwargs):
        super().publish(message=message, **kwargs)


def logger_handler(topic_or_ntfyurl: str, host: str | None = None, port: int | None = None,
                   password: str | None = None):
    if topic_or_ntfyurl.startswith("ntfy://"):
        if mat := re.match(r"ntfy://((?P<host>.+):(?P<port>.+))?/(?P<topic>.+)$", topic_or_ntfyurl):
            host = mat.group("host")
            port = mat.group("port")
            topic = mat.group("topic")
            return logger_handler(topic, host=host, port=port, password=password)
        else:
            raise ValueError(f"Invalid ntfyurl: {topic_or_ntfyurl}")

    if not (host and port):
        try:
            from confctl import config
            host, port = config.get("redis/host"), config.get("redis/port")
        except (ImportError, KeyError, ValueError):
            raise ValueError("either confctl.config configured or host and port are supplied")
        litter.connect(host, port, password=config.get("redis/password", None))

    def _handler(message):
        publish(topic=topic_or_ntfyurl, message=message)

    return _handler
