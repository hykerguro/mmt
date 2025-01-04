import os
import subprocess
import time

from loguru import logger
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from confctl import util, config


class ProcessHandler:
    def __init__(self, name, agent, process=None, *, stdout=None, stderr=None):
        self.name = name
        self.cmd = agent["cmd"]
        self.process = process
        self.stdout = stdout
        self.stderr = stderr

    def start_process(self):
        self.process = subprocess.Popen(self.cmd, stdout=self.stdout, stderr=self.stderr)
        logger.info(f"{self.name} started with {self.cmd}")

    def terminate_process(self):
        if self.process:
            self.process.terminate()
            logger.info(f"{self.name} terminated")

    def restart_process(self):
        self.terminate_process()
        self.start_process()


class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, process_handler: ProcessHandler):
        self.process_handler = process_handler

    def on_modified(self, event):
        if (event.src_path.endswith(".py") or event.src_path.endswith(".yaml")
                or event.src_path.endswith(".yml") or event.src_path.endswith(".json")):
            logger.info(
                f"Detected change in {event.src_path}. Restarting {self.process_handler.name} ...")
            self.process_handler.restart_process()


def monitor_and_restart(agents):
    process_handlers = {}
    observers = []
    for name, info in agents.items():
        stdout_dir = config.get("watchdog/agent_console/stdout", "console")
        stderr_dir = config.get("watchdog/agent_console/stderr", "console")
        if stdout_dir == "console":
            stdout = None
        elif stderr_dir == "devnull":
            stdout = subprocess.DEVNULL
        else:
            os.makedirs(stdout_dir, exist_ok=True)
            stdout = open(f"{stdout_dir}/{name}.stdout.log", "a", encoding="utf-8")

        if stderr_dir == "console":
            stderr = None
        elif stderr_dir == "devnull":
            stderr = subprocess.DEVNULL
        else:
            os.makedirs(stderr_dir, exist_ok=True)
            stderr = open(f"{stderr_dir}/{name}.stderr.log", "a", encoding="utf-8")

        handler = ProcessHandler(name, info, stdout=stdout, stderr=stderr)
        handler.start_process()
        process_handlers[name] = handler

        observer = Observer()
        observers.append(observer)
        observer.schedule(FileChangeHandler(handler), path=info["src"], recursive=True)
        observer.schedule(FileChangeHandler(handler), path=info["conf"], recursive=False)
        observer.start()

        logger.info(f"Started monitoring changes for {name} ...")
    try:
        while True:
            time.sleep(1)  # 保持主线程活跃
    except KeyboardInterrupt:
        for handler in process_handlers.values():
            handler.terminate_process()  # 手动停止进程
        for observer in observers:
            observer.stop()
    for observer in observers:
        observer.join()


if __name__ == "__main__":
    parser = util.get_argparser()
    parser.add_argument("-p", "--python", help="Python executable file path")
    parser.add_argument("-a", "--agent-config")
    args = parser.parse_args()
    util.init_config(args)
    util.init_loguru_loggers("watchdog/logs")

    agents = {
        "heartbeat": {
            "cmd": [args.python, "heartbeat/heartbeat/server.py", "-c", args.agent_config],
            "src": "heartbeat/",
            "conf": args.agent_config,
        },
        "monitor": {
            "cmd": [args.python, "-m", "litter.monitor", "-c", args.agent_config],
            "src": "litter/litter/monitor",
            "conf": args.agent_config,
        },
        "ntfy": {
            "cmd": [args.python, "ntfy/ntfy/agent.py", "-c", args.agent_config],
            "src": "ntfy/",
            "conf": args.agent_config,
        },
        "tg": {
            "cmd": [args.python, "tg/tg/agent.py", "-c", args.agent_config],
            "src": "tg/",
            "conf": args.agent_config,
        },
        "pixiv_scraper": {
            "cmd": [args.python, "apps/random_setu/pixiv_scraper.py", "-c", args.agent_config],
            "src": "apps/random_setu/",
            "conf": args.agent_config,
        },
        "sesebot": {
            "cmd": [args.python, "apps/sesebot/bot.py", "-c", args.agent_config],
            "src": "apps/sesebot/",
            "conf": args.agent_config,
        },
        "pixiv_fav": {
            "cmd": [args.python, "-m", "apps.pixiv_fav", "fav", "follow", "-c", args.agent_config],
            "src": "apps/pixiv_fav/",
            "conf": args.agent_config,
        },
    }
    monitor_and_restart(agents)
