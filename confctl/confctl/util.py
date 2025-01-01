import argparse

from confctl import config


def get_argparser(*arg, **kwargs) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(*arg, **kwargs)
    parser.add_argument("-c", "--config_path", type=str, nargs="*", default='./config.json', help='配置文件路径')
    return parser


def init_config(args):
    for conf in args.config_path:
        config.load_config(conf, update=True)
    return config


def init_loguru_loggers(key):
    from loguru import logger

    for conf in config.get(key, []):
        if conf["sink"].startswith("ntfy://"):
            from ntfy.api import logger_handler
            conf = dict(conf)
            sink = conf.pop("sink")
            logger.add(logger_handler(sink), **conf)
        else:
            logger.add(**conf)
    return logger


def default_arg_config_loggers(key: str | None = None):
    args = get_argparser().parse_args()
    _c = init_config(args)
    if key is not None:
        init_loguru_loggers(key)
    return _c
