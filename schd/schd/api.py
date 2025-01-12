from typing import Any

import litter


def add_job(channel: str, body: Any, trigger: str, **kwargs) -> str:
    """
    添加定时发送litter消息的任务
    :param channel: redis channel
    :param body: 消息内容
    :param trigger: 定时任务触发器。支持'interval', 'date' 和 'cron'；trigger=='cron' 时，传入crontab参数
    :param kwargs: 传给apscheduler.add_job的参数
    :return:
    """
    resp = litter.request("schd.add_job", {
        "channel": channel,
        "body": body,
        "trigger": trigger,
        **kwargs
    })
    if resp.success:
        return resp.body
    else:
        raise litter.RemoteFunctionRaisedException(resp)


def remove_job(job_id: str) -> None:
    resp = litter.request("schd.remove_job", {
        "job_id": job_id
    })
    if not resp.success:
        raise litter.RemoteFunctionRaisedException(resp)
