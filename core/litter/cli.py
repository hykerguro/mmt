import argparse
import json

import litter


def publish(channel: str, body: str):
    data = json.loads(body)
    litter.publish(channel, data)


def request(channel: str, body: str):
    data = json.loads(body)
    litter.request(channel, data)


def main():
    parser = argparse.ArgumentParser(prog="litter", description="Litter CLI tool")
    parser.add_argument("--config-path", "-c", default="config/config.yaml", help="Configuration file path")
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

    if args.command == "publish":
        publish(args.channel, args.body)
    elif args.command == "request":
        request(args.channel, args.body)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
