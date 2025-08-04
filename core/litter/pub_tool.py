import json
from time import sleep
from traceback import print_exc

import litter
from confctl import util, config

util.default_arg_config_loggers()


def get_host_and_port():
    host = input("Redis host: ")
    port = int(input("Redis port: "))
    password = input("Redis password: ")
    db = input("Redis db: ")
    return host, port, password, db


host = config.get("redis/host", None)
port = int(config.get("redis/port", 0))
password = config.get("redis/password", None)
db = int(config.get("redis/db", 0))

if host and port:
    ans = input(f"Connect to {host}:{port} (y/n): ")
    if ans.lower() == "n":
        host, port, password, db = get_host_and_port()
    elif ans.lower() == "y":
        pass
    else:
        print("Invalid input, exiting...")
        exit(1)
else:
    host, port, password, db = get_host_and_port()

name = "mmt.pub.tool"
litter.connect(app_name=name, redis_credentials={"host": host, "port": port, "password": password, "db": db})
sleep(0.5)
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
