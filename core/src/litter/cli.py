import argparse
import json

from loguru import logger

import litter
from confctl import config


def publish(channel: str, body: str):
    data = json.loads(body)
    litter.publish(channel, data)
    logger.info(f"published to {channel}")


def request(channel: str, body: str):
    data = json.loads(body)
    logger.info(f"request to {channel}")
    result = litter.request(channel, data)
    logger.info(f"result from {channel}:\n{result}")


def main():
    parser = argparse.ArgumentParser(prog="litter", description="Litter CLI tool")
    parser.add_argument("--config-path", "-c", default="config/config.yaml", help="Configuration file path")
    parser.add_argument("--app-name", "-n", default=None, help="App name")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # publish 子命令
    publish_parser = subparsers.add_parser("publish", help="Publish a message")
    publish_parser.add_argument("channel", help="Channel name")
    publish_parser.add_argument("body", help="JSON body string")

    # request 子命令
    request_parser = subparsers.add_parser("request", help="Send a request")
    request_parser.add_argument("channel", help="Channel name")
    request_parser.add_argument("body", help="JSON body string")

    args = parser.parse_args()

    config.load_config(args.config_path)
    litter.connect(redis_credentials=config.get("redis"), app_name=args.app_name)

    if args.command == "publish":
        publish(args.channel, args.body)
    elif args.command == "request":
        request(args.channel, args.body)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
