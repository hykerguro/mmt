import datetime
import json
from dataclasses import dataclass, field, asdict
from typing import Self, Sequence, Any, Iterator


class EhEntity:
    def __init__(self, *args, **kwargs) -> None:
        pass

    @classmethod
    def from_json(cls, json_str: str, path: Sequence[str | int] | None = None):
        entity = json.loads(json_str)
        if path is not None:
            for key in path:
                entity = entity[key]
        return cls.from_dict(entity)

    @classmethod
    def from_dict(cls, param: dict[str, Any] | str) -> Self:
        return cls(**{k: param.get(k, None) for k in cls.__init__.__annotations__.keys() if k != 'return'})

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class Image(EhEntity):
    token: str
    gid: int
    num: int
    url: str
    origin_url: str


@dataclass
class GalleryMetadata(EhEntity):
    gid: int
    token: str
    title: str
    title_jpn: str
    thumb: str
    eh_category: str
    uploader: str
    parent: str
    expunged: bool
    filecount: int
    favorites: int
    rating: float
    lang: str
    date: datetime.datetime | None = field(default=None)
    newer: list[tuple[str, datetime.datetime]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class Gallery(GalleryMetadata):
    id: int | None = field(default=None)
    images_iter: Iterator[Image] | None = field(default=None, repr=False)
