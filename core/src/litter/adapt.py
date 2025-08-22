import inspect
from typing import Callable, Any

from loguru import logger

from confctl import util, config
from .agent import subscribe, listen_bg, listen
from .model import Message

__all__ = [
    "adapt",
    "agent",
    "FromConfig"
]


def _adapt_method(name: str, method: Callable) -> Callable:
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


def adapt(obj, app_name: str, *,
          redis_credentials: dict[str, Any] | None = None, bg: bool = False,
          executor_workers: int = 4
          ) -> None:
    """
    将一个对象转为监听litter消息的服务应用，对象的 method_name 方法会被转为监听 app_name:method_name 的litter接口
    :param obj: 被转换的对象
    :param app_name: 应用名称
    :param redis_credentials: 连接litter的redis配置，缺省时自动读取配置文件中的redis项
    :param bg: 是否后台运行
    :param executor_workers:
    :return: None
    """
    methods = [x for x in inspect.getmembers(obj, predicate=inspect.ismethod)
               if not x[0].startswith("_") and x[0] != "api"]
    logger.info(f"Adapting {len(methods)} methods of {app_name}:")
    for name, method in methods:
        subscribe(f"{app_name}:{name}", _adapt_method(name, method))
        logger.info(f"\t{name}")

    (listen_bg if bg else listen)(app_name=app_name, redis_credentials=redis_credentials,
                                  executor_workers=executor_workers)


class FromConfig:
    def __init__(self, key: str, default: Any = config._CONFIG_VALUE_GUARD):
        self.key = key
        self.default = default

    def __call__(self):
        return config.get(self.key, self.default)


def agent(
        app_name: str, *, init_args: tuple | None = None, init_kwargs: dict[str, Any] | FromConfig | None = None,
        init_config: bool = True, log_config_key=None, redis_credentials: dict[str, Any] | None = None,
        executor_workers: int = 4
):
    """
    将一个类转为监听litter消息的服务应用，类的 method_name 方法会被转为监听 app_name:method_name 的litter接口
    :param app_name: litter 应用名称
    :param init_args: 实例化class时的参数
    :param init_kwargs: 实例化class时的参数
    :param init_config: 是否初始化配置，为True时log_config_key、redis_credentials才生效
    :param log_config_key: 日志配置在配置文件中的位置
    :param redis_credentials: 连接litter的redis配置，缺省时自动读取配置文件中的redis项
    :param executor_workers:
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
            if isinstance(init_kwargs, FromConfig):
                init_kwargs = init_kwargs()
                assert isinstance(init_kwargs, dict)
            init_kwargs = {
                k: (arg() if isinstance(arg, FromConfig) else arg)
                for k, arg in init_kwargs.items()
            } if init_kwargs else {}

            delegate = clazz(*init_args, **init_kwargs)
            adapt(delegate, app_name=app_name, bg=False, redis_credentials=redis_credentials,
                  executor_workers=executor_workers)
        return clazz

    return _inner
