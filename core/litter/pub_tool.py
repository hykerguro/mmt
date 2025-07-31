import json
from traceback import print_exc

import litter
from confctl import util, config

util.default_arg_config_loggers()

host = config.get("redis/host") or input("Redis host: ")
port = int(config.get("redis/port") or input("Redis port: "))
name = config.get("redis/host") or input("Client name: ") or "mmt.pub.tool"
litter.connect(host, port, name)

channel = None
mode = "P"
while (data := input(">>> ").strip()) != "exit":
    flag = data.count("|")
    if flag == 0:
        pass
    elif flag == 1:
        channel, data = data.split("|")
    elif flag == 2:
        mode, channel, data = data.split("|")
    else:
        print(f"Invalid input. Format: <mode>|<channel>|<data>")

    if channel is None:
        print(f"Invalid input. Format: <mode>|<channel>|<data>")
        continue

    try:
        data = json.loads(data)
    except json.JSONDecodeError:
        print_exc()
        continue

    if mode == "P":
        litter.publish(channel, data)
    elif mode == "R":
        try:
            print("<<<", litter.request(channel, data))
        except litter.RequestTimeoutException:
            print("Request timeout")
    else:
        print(f"Invalid input. `mode` must be 'P' for publish or 'R' for request.")
