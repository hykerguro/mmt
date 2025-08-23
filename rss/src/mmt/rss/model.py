import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import TypeVar, Mapping, overload

T = TypeVar('T')


@overload
def regulate(obj: datetime) -> str: ...


@overload
def regulate(obj: T) -> T: ...


def regulate(obj):
    if isinstance(obj, Mapping):
        result = {}
        for k, v in obj.items():
            if v is not None:
                result[k] = regulate(v)
        return result
    elif isinstance(obj, (list, tuple)):
        return [regulate(x) for x in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj


@dataclass
class BaseModel:
    def as_dict(self) -> dict:
        return regulate(asdict(self))

    def json(self, indent: int = 4, ensure_ascii: bool = False, default=str, **kwargs) -> str:
        return json.dumps(self.as_dict(), indent=indent, ensure_ascii=ensure_ascii, default=default, **kwargs)


@dataclass
class Author(BaseModel):
    name: str | None = None
    url: str | None = None
    avatar: str | None = None


@dataclass
class Attachment(BaseModel):
    url: str
    mime_type: str | None = None
    title: str | None = None
    size_in_bytes: int | None = None
    duration_in_seconds: int | None = None


@dataclass
class Item(BaseModel):
    id: str

    url: str | None = None
    external_url: str | None = None
    title: str | None = None
    content_html: str | None = None
    content_text: str | None = None
    summary: str | None = None
    image: str | None = None
    banner_image: str | None = None
    date_published: datetime | None = None
    date_modified: datetime | None = None
    authors: list[Author] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    language: str | None = None
    attachments: list[Attachment] = field(default_factory=list)


@dataclass
class Hub(BaseModel):
    type: str
    url: str


@dataclass
class Feed(BaseModel):
    title: str
    version: str = "https://jsonfeed.org/version/1.1"
    home_page_url: str | None = None
    feed_url: str | None = None
    description: str | None = None
    user_comment: str | None = None
    next_url: str | None = None
    icon: str | None = None
    favicon: str | None = None
    authors: list[Author] = field(default_factory=list)
    language: str | None = None
    expired: bool | None = None
    hubs: list[Hub] = field(default_factory=list)
    items: list[Item] = field(default_factory=list)
