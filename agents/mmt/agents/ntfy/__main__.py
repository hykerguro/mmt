from confctl import util
from .agent import init, listen_litter

util.default_arg_config_loggers("ntfy/logs")
init()
listen_litter(bg=False)