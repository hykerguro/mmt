from confctl import config, util
from .monitor import LitterMonitor

util.default_arg_config_loggers("litter/monitor/logs")
LitterMonitor(
    config.get("redis"),
    db_url=config.get("db_url"),
    exclude_channels=config.get("litter/monitor/exclude_channels", [])
).run()
