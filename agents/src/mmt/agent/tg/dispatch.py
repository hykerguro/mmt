import telethon.tl.patched
from telethon import events

import litter
from . import client


@client().on(events.NewMessage(incoming=True))
async def message_dispatcher(event: events.NewMessage.Event):
    message: telethon.tl.patched.Message = event.message
    dm = message.to_dict()
    litter.publish("agent.tg.message.receive", dm)
