from confctl import config, util

util.default_arg_config_loggers()

import litter

litter.connect(app_name='rss_server')

import uvicorn
from .server import create_app

uvicorn.run(create_app(), host=config.get('rss/server/host'), port=config.get('rss/server/port'))
