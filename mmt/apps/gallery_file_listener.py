from typing import Any

from loguru import logger
from ntfy.api import publish as notify
from tg.api import get_handler, message_predicate as tgmp

import confctl.util
import litter
from confctl import config


def message_handler(message: dict[str, Any]):
    filename = message["media"]["document"]["attributes"][0]["file_name"]
    text = message["message"]
    notify("mmt_tgfile", f"{filename}\n{text}")


def main():
    args = confctl.util.get_argparser().parse_args()
    confctl.util.init_config(args)
    confctl.util.init_loguru_loggers("tg_tools/logs")

    groups = config.get("tg_tools/group_file_listener/groups")
    peers = config.get("tg_tools/group_file_listener/peers")
    # keywords = config.get("tg_tools/group_file_listener/keywords")
    condition = tgmp.all(
        tgmp.any(*(
                [tgmp.from_channel(channel_id) for channel_id in groups] +
                [tgmp.from_private_user(peer) for peer in peers])),
        tgmp.has_file(),
    )
    litter.subscribe("tg.message.receive", get_handler(condition, message_handler))
    host, port = config.get("redis/host"), config.get("redis/port")
    try:
        from heartbeat.agent import beat_bg
        beat_bg("gallery_file_listener", host=host, port=port)
    except ImportError:
        pass
    litter.listen(host, port)


if __name__ == "__main__":
    logger.catch(main)()
