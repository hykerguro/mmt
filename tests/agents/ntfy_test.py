from litter import setup

setup("ntfy_test")

from mmt.agents import NtfyAgent

api: NtfyAgent = NtfyAgent.api()

api.publish("test", "你好")
api.publish("test", "谢谢", tags=["debug"])
api.publish("test", "再见" * 2500, tags=["too long"])
