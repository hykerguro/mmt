import json
from pathlib import Path

import telethon.tl.patched
from telethon import events

import litter
from confctl import config
from . import client


@client().on(events.NewMessage(incoming=True))
async def message_dispatcher(event: events.NewMessage.Event):
    message: telethon.tl.patched.Message = event.message
    dm = message.to_dict()
    litter.publish("agent.tg.message.receive", dm)
    if config.get("tg/debug", False) and (p := config.get("tg/dump_path", None)):
        (Path(p) / "message").mkdir(parents=True, exist_ok=True)
        with (Path(p) / "message" / f"{message.id}.json").open("w", encoding="utf8") as f:
            json.dump(dm, f, indent=4, ensure_ascii=False, default=str)
