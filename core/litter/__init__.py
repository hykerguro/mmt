from .agent import *
from .model import *


def setup(app_name: str | None = None) -> None:
    from confctl import util
    util.default_arg_config_loggers()
    connect(app_name=app_name)
