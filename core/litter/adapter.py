import inspect
from typing import Callable, Any

from loguru import logger

import litter.agent
from .agent import subscribe, listen_bg, request, publish
from .model import Message

__all__ = [
    "adapt",
    "api"
]


def build_adapter(name: str, method: Callable) -> Callable:
    def _inner(message: Message):
        kwargs = message.body
        args = kwargs.pop("_", [])
        param_expr = ', '.join([
            *map(str, args),
            *(f'{k}={str(v)}' for k, v in kwargs.items()),
        ])
        logger.debug(f"Invoke {name}({param_expr})")
        return method(*args, **kwargs)

    return _inner


def adapt(api_obj, app_name: str, pattern_prefix: str | None = None, *,
          redis_credentials: dict[str, Any] | None = None, bg: bool = False,
          executor_workers: int = 4
          ) -> None:
    if pattern_prefix is None:
        pattern_prefix = app_name
    assert " " not in pattern_prefix
    methods = [x for x in inspect.getmembers(api_obj, predicate=inspect.ismethod) if not x[0].startswith("_")]
    logger.info(f"Adapting {len(methods)} methods of {app_name}:")
    for name, method in methods:
        subscribe(f"{pattern_prefix}:{name}", build_adapter(name, method))
        logger.info(f"\t{name}")

    listen_bg(app_name=app_name, redis_credentials=redis_credentials,
                                  executor_workers=executor_workers)

    if not bg:
        try:
            while True:
                pass
        except KeyboardInterrupt:
            litter.agent.disconnect()

def api(app_name: str, *, ret: bool | None = None) -> Callable:
    def decorator(method: Callable) -> Callable:
        nonlocal ret
        if ret is None:
            ret = inspect.signature(method).return_annotation is not None
        m = request if ret else publish

        def _inner(*args, **kwargs):
            kwargs["_"] = args
            resp = m(f"{app_name}:{method.__name__}", kwargs)
            return resp.body

        return _inner

    return decorator
