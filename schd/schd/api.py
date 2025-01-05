from typing import Any

import litter


def add_job(channel: str, body: Any, trigger: str, **kwargs) -> str:
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
