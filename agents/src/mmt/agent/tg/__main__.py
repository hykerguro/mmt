from loguru import logger

import litter
from confctl import util
from litter.adapt import adapt
from . import init_client, me

util.default_arg_config_loggers("tg/logs")
litter.connect(app_name="mmt.agent.tg")

init_client()
logger.info(f"Current user: {me().username}, {me().id}")

from .dispatch import *
from .agent import TelegramAgent

adapt(TelegramAgent(), "mmt.agent.tg", bg=True)

client().run_until_disconnected()
