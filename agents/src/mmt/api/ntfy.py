from .framework import api


@api("mmt.agent.ntfy")
class NtfyApi:
    def publish(self, topic: str, message: str, **kwargs) -> None:
        ...
