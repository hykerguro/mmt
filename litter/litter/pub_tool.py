import json
from traceback import print_exc

import litter

host = input("Redis host: ")
port = int(input("Redis port: "))
name = input("Client name: ") or None
litter.connect(host, port, name)

channel = None
while (data := input(">>> ").strip()) != "exit":
    if "|" in data:
        channel, data = data.split("|", maxsplit=1)

    if channel is None:
        print(f"Invalid input. Format: <channel>|<data>")
        continue

    try:
        data = json.loads(data)
    except json.JSONDecodeError:
        print_exc()
        continue

    litter.publish(channel, data)
