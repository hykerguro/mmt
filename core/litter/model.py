import base64
import json
from datetime import datetime

__all__ = [
    "Message",
    "serialize",
    "deserialize",
    "RequestTimeoutException",
    "RemoteFunctionRaisedException"
]

from functools import cached_property
from pathlib import PurePath
import pytz
from typing import Any, TypeAlias

Json: TypeAlias = dict[str, Any] | list[dict[str, Any]]

tz = pytz.timezone("Asia/Shanghai")


class LitterException(Exception):
    pass


class RequestTimeoutException(LitterException):
    pass


class RemoteFunctionRaisedException(LitterException):
    def __init__(self, resp: "Response"):
        self.resp = resp
        super().__init__(resp.headers['litter-exception-type'] + ": " + resp.headers['litter-exception-message'])


class LitterJsonEncoder(json.JSONEncoder):
    DTM_PREFIX = "<\u200Blt-p:dtm>:"
    BASE64_PREFIX = "<\u200Blt-p:b64>:"

    def default(self, o):
        if isinstance(o, datetime):
            return self.DTM_PREFIX + o.isoformat()
        elif isinstance(o, bytes):
            return self.BASE64_PREFIX + base64.b64encode(o).decode()
        elif isinstance(o, PurePath):
            return str(o)
        elif isinstance(o, Exception):
            return f'{type(o)}: {o}'
        return super().default(o)


def serialize(obj) -> str:
    return json.dumps(obj, cls=LitterJsonEncoder, ensure_ascii=False)


def _obj_hook(d):
    for k, v in d.items():
        if isinstance(v, str):
            if v.startswith(LitterJsonEncoder.BASE64_PREFIX):
                d[k] = base64.b64decode(v[len(LitterJsonEncoder.BASE64_PREFIX):])
            elif v.startswith(LitterJsonEncoder.DTM_PREFIX):
                d[k] = datetime.fromisoformat(v[len(LitterJsonEncoder.DTM_PREFIX):]).astimezone(tz)
    return d


def deserialize(data: str, **kwargs) -> Json:
    return json.loads(data, object_hook=_obj_hook, **kwargs)


class Message:
    """
    {'type': 'psubscribe', 'pattern': None, 'channel': 'litter_agent_test_3:request', 'data': 3}
    """

    def __init__(self, data, *,
                 channel: str,
                 type: str = "message",
                 pattern: str | None = None,
                 ):
        self.type = type
        self.pattern = pattern
        self.channel = channel
        self.data = data
        self._json = None

    @classmethod
    def from_redis_message(cls, redis_message: dict) -> 'Message':
        return cls(**redis_message)

    @cached_property
    def data_obj(self):
        return deserialize(self.data)

    @property
    def body(self):
        return self.data_obj["body"]

    @property
    def headers(self):
        return self.data_obj.get("headers", {})

    def json(self) -> Json:
        return self.body

    @property
    def request_id(self) -> str | None:
        return self.headers.get("litter-request-id")

    def __str__(self):
        return str(dict(type=self.type, channel=self.channel, pattern=self.pattern, data=self.data))


class Response:
    def __init__(self, headers: dict[str, str] | None, body) -> None:
        self.headers = headers
        self.body = body

    def json(self):
        return deserialize(self.body)

    @classmethod
    def from_redis_response(self, data: str) -> 'Response':
        return Response(**deserialize(data))

    def serialize(self) -> str:
        return serialize({"headers": self.headers, "body": self.body})

    @property
    def request_id(self):
        return self.headers["litter-request-id"]

    @property
    def response_queue(self):
        return self.headers["litter-response-queue"]

    @property
    def success(self):
        return "litter-exception-type" not in self.headers

    @property
    def exception_type(self):
        return self.headers.get("litter-exception-type", None)

    @property
    def exception_message(self):
        return self.headers.get("litter-exception-message", None)

    def __str__(self):
        return str(dict(headers=self.headers, body=self.body))
