from confctl import config

config.load_config("config/dev.yaml")
from litter import subscribe, listen_bg, Message, connect


@subscribe("litter_agent_test_?")
def consumer(message: Message):
    """Test decorator style subscribe"""
    print("got message", message)
    return Message("114514", channel="litter_agent_test_resp")


def check_resp(message: Message):
    """Test return response message"""
    print("RESP:", message)


def main():
    subscribe("litter_agent_test_resp", check_resp)  # Test func style subscribe
    connect(config.get("redis/host"), int(config.get("redis/port")))
    listen_bg()  # Test listen and listen_bg

    import time
    while True:
        print(f"[Main] I'm still running.")
        time.sleep(2)


if __name__ == '__main__':
    main()
