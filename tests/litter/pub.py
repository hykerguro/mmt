from confctl import config
from litter import publish, connect

config.load_config("config/dev.yaml")

channels = ["litter_agent_test_1", "litter_agent_test_2", "litter_agent_test_3"]


def main():
    import random
    import time
    connect(config.get("redis/host"), config.get("redis/port"))
    while True:
        channel = random.choice(channels)
        data = random.randint(1, 100)
        print(f"{data} -> {channel}")
        resp = publish(channel, data)
        print(f"{resp} <- Redis")
        time.sleep(1)


if __name__ == '__main__':
    main()
