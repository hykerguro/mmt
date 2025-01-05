from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

import litter
from confctl import util, config

scheduler: BlockingScheduler | None = None

_publish = litter.publish


@litter.subscribe("schd.add_job")
def add_job(message: litter.Message):
    params = message.json()
    """
    {
        "channel": str,
        "body": Any,
        "trigger": "date", "cron" or "interval",
        **kwargs passed to trigger constructor
    }
    """
    channel = params.pop("channel")
    body = params.pop("body")
    trigger = params.pop("trigger")
    if trigger == "cron" and "crontab" in params:
        trigger = CronTrigger.from_crontab(params.pop("crontab"))
    job = scheduler.add_job(_publish, kwargs=dict(channel=channel, body=body), trigger=trigger, **params)
    litter.publish("schd.add_job.done", job.id)
    return job.id


@litter.subscribe("schd.remove_job")
def remove_job(message: litter.Message):
    params = message.json()
    """
    {
        "job_id": str
    }
    """
    scheduler.remove_job(params["job_id"])
    litter.publish("schd.remove_job.done", params["job_id"])


def main():
    global scheduler
    litter.listen_bg(config.get("redis/host"), config.get("redis/port"), "schd")

    scheduler = BlockingScheduler(jobstores={
        'default': SQLAlchemyJobStore(url=config.get("db_url"))
    })
    logger.info(f"Start sched")

    try:
        from heartbeat.agent import beat_bg
    except ImportError:
        pass
    else:
        beat_bg()

    try:
        scheduler.start()
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Stop sched")
        scheduler.shutdown()


if __name__ == '__main__':
    util.default_arg_config_loggers("schd/logs")
    main()
