from typing import Sequence

from .agent import *
from .model import *


def setup(app_name: str | None = None, config_path: str | Sequence[str] | None = None) -> None:
    from confctl.util import default_arg_config_loggers
    default_arg_config_loggers(argv=["-c", config_path] if config_path else None)
    connect(app_name=app_name)
