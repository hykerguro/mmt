import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from loguru import logger

import litter
from alert import Alert, ConsoleAlert, NtfyAlert
from confctl import config, util

NOTE = {}

_EXEPOOL = ThreadPoolExecutor(max_workers=4)

ALERTS: list[Alert] = []


def register_alert(hb_url: str):
    global ALERTS
    if hb_url == "console":
        ALERTS.append(ConsoleAlert())
    elif mat := re.match(r"ntfy://((?P<host>.+):(?P<port>.+))?/(?P<topic>.+)$", hb_url):
        host = mat.group("host")
        port = mat.group("port")
        topic = mat.group("topic")
        if not (host and port):
            host, port = config.get("redis/host"), config.get("redis/port")
        ALERTS.append(NtfyAlert(topic, host, port))
    else:
        raise ValueError(f"Unknown alert type: {hb_url}")


def do_alert(service: str, severe: int, record: dict[str, Any]):
    logger.info(f"Service {service}: {severe=}, {record=}")
    litter.publish("heartbeat.lost", {"service": service, "severe": severe, "record": record})
    for alert in ALERTS:
        _EXEPOOL.submit(alert.lost, service, severe, record)


def do_revived(service: str, record: dict[str, Any]):
    logger.info(f"Service {service} revived: {record=}")
    litter.publish("heartbeat.revived", {"service": service, "record": record})
    for alert in ALERTS:
        _EXEPOOL.submit(alert.revived, service, record)


def period_check(interval: float, tolerance: int, eliminate: int):
    global NOTE
    while True:
        pops = []
        for service, record in NOTE.items():
            record['cnt'] += 1
            logger.trace(f"Check {service}: {record=}")
            if (severe := record['cnt'] - tolerance) >= 0:
                do_alert(service, severe, record)
                if severe > eliminate:
                    pops.append(service)
        for service in pops:
            logger.info(f"服务{service}下线过久，排除心跳监测")
            NOTE.pop(service)
        time.sleep(interval)


def main(host, port, channel, interval, tolerance, eliminate):
    global NOTE

    @litter.subscribe(channel)
    def _heartbeat_listener(message):
        data = message.json()
        service = data['service']
        if service in NOTE and NOTE[service]['cnt'] >= tolerance:
            do_revived(service, NOTE[service])

        NOTE[service] = {"last": time.time(), "cnt": 0, "interval": 3600}

    litter.listen_bg(host, port, "heartbeat_service")
    logger.info(f"Heartbeat service started at redis://{host}:{port}/{channel}, {interval=}, {tolerance=} "
                f"with {len(ALERTS)} alerts:" + ", ".join(map(str, ALERTS)))
    period_check(interval, tolerance, eliminate)


if __name__ == '__main__':
    util.default_arg_config_loggers("heartbeat/logs")
    litter.connect(config.get("redis/host"), config.get("redis/port"), app_name="heartbeat_service")

    for ac in config.get("heartbeat/alerts"):
        register_alert(ac)

    logger.catch(main)(
        config.get("redis/host"),
        config.get("redis/port"),
        config.get("heartbeat/channel", "heartbeat.beat"),
        config.get("heartbeat/interval", 10.),
        config.get("heartbeat/tolerance", 3),
        config.get("heartbeat/eliminate", 24 * 60 * 6),  # 下线1天
    )
