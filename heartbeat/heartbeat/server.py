import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from loguru import logger

import confctl.util
import litter
from confctl import config


class Alert:
    def lost(self, service: str, severe: int, record: dict[str, Any]):
        raise NotImplementedError

    def revived(self, service: str, record: dict[str, Any]):
        raise NotImplementedError


class ConsoleAlert(Alert):
    def __int__(self):
        self.last_alert = 0.

    def _do_alert(self, message):
        print(message)
        self.last_alert = time.time()

    def lost(self, service: str, severe: int, record: dict[str, Any]):
        message = f"{service} 挂掉了：\n" + \
                  "\t上次心跳时间：" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record['last'])) + "\n" + \
                  f"\t失联计数：{severe}"
        if severe == 0 or time.time() - self.last_alert > 3600:
            self._do_alert(message)

    def revived(self, service: str, record: dict[str, Any]):
        last = record.get('last', 0)
        message = f"{service} 上线了：\n" + \
                  ("\t上次心跳时间：" + time.strftime("%Y-%m-%d %H:%M:%S",
                                                     time.localtime(last)) + "\n") if last > 0 else ""
        self._do_alert(message)

    def __str__(self):
        return "ConsoleAlert"


class NtfyAlert(ConsoleAlert):
    def __init__(self, host: str, port: int, topic: str):
        self.host = host
        self.port = port
        self.topic = topic
        litter.connect(host, port)
        from ntfy.api import TopicPublisher
        self.lp = TopicPublisher(topic)

    def _do_alert(self, message):
        self.lp.publish(message)
        self.last_alert = time.time()

    def __str__(self):
        return f"NtfyAlert://{self.host}:{self.port}/{self.topic}"


NOTE = {}
ALERTS: list[Alert] = []
_EXEPOOL = ThreadPoolExecutor(max_workers=4)


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
        ALERTS.append(NtfyAlert(host, port, topic))
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


def period_check(interval: float, tolerance: int):
    global NOTE
    while True:
        for service, record in NOTE.items():
            record['cnt'] += 1
            logger.trace(f"Check {service}: {record=}")
            if (severe := record['cnt'] - tolerance) >= 0:
                
                do_alert(service, severe, record)
        time.sleep(interval)


def main(host, port, channel, interval, tolerance):
    global NOTE

    @litter.subscribe(channel)
    def _heartbeat_listener(message):
        data = message.json()
        service = data['service']
        if service in NOTE and NOTE[service]['cnt'] >= tolerance:
            do_revived(service, NOTE[service])

        NOTE[service] = {"last": time.time(), "cnt": 0}

    litter.listen_bg(host, port)
    logger.info(f"Heartbeat service started at redis://{host}:{port}/{channel}, {interval=}, {tolerance=} "
                f"with {len(ALERTS)} alerts:" + ", ".join(map(str, ALERTS)))
    period_check(interval, tolerance)


if __name__ == '__main__':
    parser = confctl.util.get_argparser()
    args = parser.parse_args()
    confctl.util.init_config(args)
    confctl.util.init_loguru_loggers("heartbeat/logs")

    for ac in config.get("heartbeat/alerts"):
        register_alert(ac)

    litter.connect(config.get("redis/host"), config.get("redis/port"))

    logger.catch(main)(
        config.get("redis/host"),
        config.get("redis/port"),
        config.get("heartbeat/channel", "heartbeat.beat"),
        config.get("heartbeat/interval", 10.),
        config.get("heartbeat/tolerance", 3)
    )
