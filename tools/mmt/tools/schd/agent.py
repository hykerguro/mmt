from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

import litter
from confctl import util, config

scheduler: BlockingScheduler | None = None


def _publish(*args, **kwargs):
    logger.info(f"Job executed: {args}, {kwargs}")
    litter.publish(*args, **kwargs)


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
    logger.info(f"Added job {job.id}: {trigger=}")
    return job.id


@litter.subscribe("schd.remove_job")
def remove_job(message: litter.Message):
    params = message.json()
    """
    {
        "job_id": str
    }
    """
    job_id = params.pop("job_id")
    scheduler.remove_job(job_id)
    litter.publish("schd.remove_job.done", job_id)
    logger.info(f"Removed job {job_id}")


@litter.subscribe("schd.list_jobs")
def list_jobs(message: litter.Message):
    return list(map(str, scheduler.get_jobs()))


def main():
    global scheduler
    litter.listen_bg(app_name="schd")

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
