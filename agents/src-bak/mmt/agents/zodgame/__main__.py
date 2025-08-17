from confctl import config, util
from litter.adapt import adapt
from . import APP_NAME
from .agent import ZodgameAgent

util.default_arg_config_loggers()
adapt(
    ZodgameAgent(config.get("zodgame/cookies"), config.get("proxies", None)),
    APP_NAME,
    APP_NAME,
    host=config.get("redis/host"),
    port=config.get("redis/port"),
    bg=False
)
