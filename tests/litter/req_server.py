import time

import litter
from confctl import util, config


@litter.subscribe("ltreq.server.f1")
def f1(message: litter.Message):
    print(message)


@litter.subscribe("ltreq.server.f2")
def f2(message: litter.Message):
    print(message)
    time.sleep(1)
    return "OK f2"


@litter.subscribe("ltreq.server.f2")
def f2(message: litter.Message):
    print(message)
    time.sleep(2)
    return "2s OK f2"


@litter.subscribe("ltreq.server.f2")
def f2(message: litter.Message):
    print(message)
    time.sleep(10)
    return "10s OK f2"


if __name__ == '__main__':
    util.default_arg_config_loggers()
    host, port = config.get("redis/host"), config.get("redis/port")
    litter.listen(host, port, "req_server")
