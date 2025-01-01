from time import sleep

import litter
from confctl import config
from ntfy.api import publish, PublishTemplate, TopicPublisher

config.load_config("config/dev.yaml")

litter.connect(config.get("redis/host"), config.get("redis/port"))

publish("test", "测试", tags=["debug"])
sleep(1)

templ = PublishTemplate(topic="test", tags=["debug", "template"])
templ.publish(message="你好")
templ.publish(message="谢谢")
templ.publish(message="小笼包")
templ.publish(message="再见")
sleep(1)

tp = TopicPublisher(topic="test")
tp.publish("李田所")
tp.publish("钱浩二")
