import json
from time import sleep, time
from traceback import format_exc
from typing import Any

import litter
from confctl import util, config

name = "mmt.pub.tool"

util.default_arg_config_loggers()


def get_host_and_port():
    host = input("Redis host: ")
    port = int(input("Redis port: "))
    password = input("Redis password: ")
    db = input("Redis db: ")
    return host, port, password, db


def connect():
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

    litter.connect(app_name=name, redis_credentials={"host": host, "port": port, "password": password, "db": db})


def parse_input(s: str) -> tuple[str, str, Any]:
    mode, channel, body = "P", None, None

    flag = s.count("|")
    if flag == 1:
        channel, body = s.split("|")
    elif flag == 2:
        mode, channel, body = s.split("|")

    if channel is None or mode not in ("P", "R") or flag > 2:
        raise ValueError(f"Invalid input. Format: <mode:P/R>|<channel>|<body>")

    return mode, channel, json.loads(body)


def prettify_resp(resp: Any) -> str:
    if isinstance(resp, (dict, list)):
        return json.dumps(resp, indent=2, ensure_ascii=False, default=str)
    if isinstance(resp, litter.Response):
        return "litter.Response" + "\n\n" + prettify_resp(resp.headers) + "\n\n" + prettify_resp(resp.body)
    return str(resp)

def loop():
    command_history = []
    while (line := input(">>> ").strip()) != "exit":
        if line == "_":
            # 重复上一个命令
            if command_history:
                line = command_history[-1]["input"]
            else:
                continue
        elif line == "dump":
            filename = f"history_{time()}.json"
            with open(filename, "w", encoding="utf8") as f:
                json.dump(command_history, f, indent=4, ensure_ascii=False)
            print(f"<<< dumped to {filename}")
            continue

        record = {
            "input": line,
            "response": None,
            "exception": None,
        }

        try:
            mode, channel, body = parse_input(line)
            if mode == "P":
                litter.publish(channel, body)
            elif mode == "R":
                resp = litter.request(channel, body)
                print("<<<", prettify_resp(resp))
                record["response"] = resp
        except Exception as e:
            record["exception"] = format_exc()
            print("ERR", record["exception"])
        finally:
            command_history.append(record)


if __name__ == '__main__':
    connect()
    sleep(0.5)
    try:
        loop()
    except KeyboardInterrupt:
        exit(0)
