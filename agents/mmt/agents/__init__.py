from typing import Any, Self

from confctl import util, config
from litter.adapter import adapt


class FromConfig:
    def __init__(self, key: str, default: Any = config._CONFIG_VALUE_GUARD):
        self.key = key
        self.default = default

    def __call__(self):
        return config.get(self.key, self.default)


def agent(
        app_name: str, *, init_args: tuple | None = None, init_kwargs: dict[str, Any] | None = None,
        init_config: bool = True, log_config_key=None, redis_credentials: dict[str, Any] | None = None
):
    """
    将class转为agent
    :param app_name: litter 应用名称
    :param init_args: 实例化class时的参数
    :param init_kwargs: 实例化class时的参数
    :param init_config: 是否初始化配置，为True时log_config_key、redis_credentials才生效
    :param log_config_key: 日志配置在配置文件中的位置
    :param redis_credentials: 连接litter的redis配置，缺省时自动读取配置文件中的redis项
    :return:
    """
    def _inner(clazz):
        if clazz.__module__ == "__main__":
            nonlocal init_args, init_kwargs
            if init_config:
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
            import inspect
            from litter.adapter import api
            clazz._mmt_delegated = dict(app_name=app_name)
            # TODO: build api
            obj = clazz.__new__(clazz)
            methods = [x for x in inspect.getmembers(obj, predicate=inspect.ismethod) if not x[0].startswith("_")]
            for name, method in methods:
                setattr(obj, name, api(app_name, ret=True)(method))
            setattr(clazz, "api", lambda: obj)
        return clazz

    return _inner


class AgentBase:
    @classmethod
    def api(cls) -> Self:
        pass
