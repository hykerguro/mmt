import time
from typing import Any

__all__ = [
    "Alert",
    "ConsoleAlert"
]


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
        if severe == 0 or time.time() - self.last_alert > record.get("interval", 3600):
            record["interval"] = record.get("interval", 3600) * 2
            self._do_alert(message)

    def revived(self, service: str, record: dict[str, Any]):
        last = record.get('last', 0)
        message = f"{service} 上线了：\n" + \
                  ("\t上次心跳时间：" + time.strftime("%Y-%m-%d %H:%M:%S",
                                                     time.localtime(last)) + "\n") if last > 0 else ""
        record["interval"] = 3600
        self._do_alert(message)

    def __str__(self):
        return "ConsoleAlert"
