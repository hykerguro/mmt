import inspect
import re
from typing import Self, Any, Callable

from litter import publish, request


class ApiBase:
    app_name: str
    special_args: dict[str, Any]

    @classmethod
    def _patch(cls, method: Callable, *, ret: bool | None = None, headers: dict[str, Any] | None = None,
               timeout: int = 5):
        if ret is None:
            ret = inspect.signature(method).return_annotation is not None

        if ret:
            m = lambda channel, body: request(channel, body, headers=headers, timeout=timeout)
        else:
            m = lambda channel, body: publish(channel, body, headers=headers)

        def _inner(*args, **kwargs):
            kwargs["_"] = args
            resp = m(f"{cls.app_name}:{method.__name__}", kwargs)
            return resp.body

        return _inner

    @classmethod
    def api(cls) -> Self:
        obj = cls.__new__(cls)
        methods = [x for x in inspect.getmembers(obj, predicate=inspect.ismethod) if not x[0].startswith("_")]
        for name, method in methods:
            extra_args = {}
            for name_pat, sp in cls.special_args.items():
                if re.match(name_pat, name):
                    extra_args = sp
                    break
            setattr(obj, name, cls._patch(method, ret=True, **extra_args))
        return obj


def api(app_name: str, **kwargs):
    def _inner(cls):
        cls.app_name = app_name
        cls.special_args = kwargs
        return cls

    return _inner
