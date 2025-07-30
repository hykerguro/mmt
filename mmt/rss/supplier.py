from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MmtItem:
    id: str
    title: str
    description: str = ""
    link: str = ""
    image: str = ""
    author: str = ""
    pub_date: datetime = None


class Supplier(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    def description(self) -> str:
        return self.name

    @abstractmethod
    def supply(self) -> list[MmtItem]:
        pass

    @abstractmethod
    def resolve(self, url: str) -> bytes | None:
        pass
