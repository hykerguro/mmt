import threading
import time

from loguru import logger

import litter

_HEARTBEAT_BG_THREAD: threading.Thread | None = None


def beat(app_name: str | None = None, *, interval: float = 5., channel: str = "heartbeat.beat",
         initial_wait: float = 10., **kwargs):
    time.sleep(initial_wait)
    if "host" in kwargs and "port" in kwargs:
        litter.connect(host=kwargs["host"], port=kwargs["port"], app_name=app_name)
    while True:
        litter.publish(channel, {"service": litter.get_appname()})
        logger.trace(f"{litter.get_appname()} beat sent.")
        time.sleep(interval)


def beat_bg(app_name: str | None = None, *, interval: float = 5., channel: str = "heartbeat.beat",
         **kwargs):
    global _HEARTBEAT_BG_THREAD
    if _HEARTBEAT_BG_THREAD is not None:
        raise RuntimeError(f"beat_bg thread had been already running")

    litter_thread = threading.Thread(target=beat, kwargs={
        "app_name": app_name,
        "interval": interval,
        "channel": channel,
        **kwargs
    })
    litter_thread.name = "HEARTBEAT_BG_THREAD"
    litter_thread.daemon = True
    litter_thread.start()


if __name__ == '__main__':
    from confctl import config, util

    args = util.get_argparser().parse_args()
    util.init_config(args)
    beat("demo", host=config.get("redis/host"), port=config.get("redis/port"))
