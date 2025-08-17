from confctl import config, util

util.default_arg_config_loggers()

import litter

litter.connect(redis_credentials=config.get("redis"))

from mmt.agents.helloworld.agent import HelloWorld

api: HelloWorld = HelloWorld.api()

result = api.hello("nihao")
print(result)
