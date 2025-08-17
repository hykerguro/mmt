from abc import abstractmethod, ABC

from .framework import ApiBase, api


@api("mmt.agent.tg")
class TelegramApi(ApiBase, ABC):
    @abstractmethod
    def send_message(self, message):
        ...
