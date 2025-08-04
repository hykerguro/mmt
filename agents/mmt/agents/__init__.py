from typing import Any

from confctl import util, config
from litter.adapter import adapt


class FromConfig:
    def __init__(self, key: str, default: Any = config._CONFIG_VALUE_GUARD):
        self.key = key
        self.default = default

    def __call__(self):
        return config.get(self.key, self.default)


def agent(
        app_name: str, *, log_config_key=None,
        redis_credentials: dict[str, Any] | None = None,
        init_args: tuple | None = None, init_kwargs: dict[str, Any] | None = None
):
    def _inner(clazz):
        if clazz.__module__ == "__main__":
            nonlocal init_args, init_kwargs
            util.default_arg_config_loggers(log_config_key=log_config_key)

            init_args = [
                (arg() if isinstance(arg, FromConfig) else arg)
                for arg in init_args
            ] if init_args else []
            init_kwargs = {
                k: (arg() if isinstance(arg, FromConfig) else arg)
                for k, arg in init_kwargs.items()
            } if init_kwargs else {}

            delegate = clazz(*init_args, **init_kwargs)
            adapt(delegate, app_name=app_name, bg=False, redis_credentials=redis_credentials)
        else:
            clazz._mmt_delegated = dict(app_name=app_name)
            # TODO: build api
        return clazz

    return _inner
