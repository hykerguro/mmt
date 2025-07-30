import argparse
from typing import Any, Mapping, Sequence, TypeAlias

from . import config

_A: TypeAlias = Sequence[Sequence[str | Mapping[str, Any]]]


def get_argparser(arguments: _A | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config_path",
                        type=str, nargs="*", default='./config.json', help='配置文件路径')
    if arguments is not None:
        for arg in arguments:
            assert isinstance(arg, Sequence) and isinstance(arg[-1], Mapping)
            parser.add_argument(*arg[:-1], **arg[-1])
    return parser


def init_config(args):
    for conf in args.config_path:
        config.load_config(conf, update=True)
    return config


def init_loguru_loggers(key):
    from loguru import logger

    for conf in config.get(key, []):
        if conf["sink"].startswith("ntfy://"):
            try:
                from ntfy.api import logger_handler
            except ImportError:
                print("WARN: import ntfy failed")
            else:
                conf = dict(conf)
                sink = conf.pop("sink")
                logger.add(logger_handler(sink), **conf)
        else:
            logger.add(**conf)
    return logger


def default_arg_config_loggers(log_config_key: str | None = None,
                               extra_arguments: _A | None = None) -> argparse.Namespace:
    args = get_argparser(extra_arguments).parse_args()
    init_config(args)
    if log_config_key is not None:
        init_loguru_loggers(log_config_key)
    return args
