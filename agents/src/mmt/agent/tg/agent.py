from datetime import datetime
from typing import Any, overload

from telethon.tl import types

from mmt.api.tg import TelegramApi
from . import client, me, sleep_util_complete


def proper_name(ext: str) -> str:
    date = datetime.now()
    return 'photo_{}-{:02}-{:02}_{:02}-{:02}-{:02}.{}'.format(
        date.year, date.month, date.day,
        date.hour, date.minute, date.second,
        ext
    )


@overload
async def download_media(media: dict[str, Any], file: str) -> None:
    pass


@overload
async def download_media(media: dict[str, Any], file: None = None) -> tuple[str, bytes, str]:
    pass


async def download_media(media: dict[str, Any], file: str | None = None) -> tuple[str, bytes, str] | None:
    if media["_"] == "MessageMediaDocument":
        media = media["document"]
    elif media["_"] == "MessageMediaPhoto":
        media = media["photo"]

    if media["_"] == "Photo":
        # download photo
        photo = media
        size = [(s["type"], max(s["sizes"])) for s in photo['sizes'] if s["_"] == "PhotoSizeProgressive"][0]
        result = await client().download_file(
            types.InputPhotoFileLocation(
                id=photo["id"],
                access_hash=photo["access_hash"],
                file_reference=photo["file_reference"],
                thumb_size=size[0]
            ),
            file=file,
            file_size=size[1],
            progress_callback=lambda ia, ib: print(f"{ia}/{ib}")
        )
        if file is None:
            return proper_name("jpg"), result, "image/jpg"

    elif media["_"] == "Document":
        document = media["document"]
        result = await client().download_file(
            types.InputDocumentFileLocation(
                id=document["id"],
                access_hash=document["access_hash"],
                file_reference=document["file_reference"],
                thumb_size=''
            ),
            file,
            file_size=document["size"],
            msg_data=None
        )
        if name_attr := list(filter(lambda a: a["_"] == "DocumentAttributeFilename", document["attributes"])):
            name = name_attr[0]["file_name"]
        elif any(attr["_"] == "DocumentAttributeVideo" for attr in document["attributes"]):
            name = proper_name("mp4")
        else:
            raise ValueError(f"Unknown document {document['_']} with attribute {document['attributes']}")
        return name, result, document.get("mime_type", None)
    else:
        raise ValueError(f"Unsupported media type: {media['_']}")


class TelegramAgent(TelegramApi):
    def send_message(self, message) -> dict:
        return sleep_util_complete(client().send_message(me().id, message)).to_dict()

    def download_media(self, document: dict[str, Any], file: str | None = None) -> tuple[str, bytes, str] | None:
        return sleep_util_complete(download_media(document, file))

    def get_message(self, *args, **kwargs) -> list[dict]:
        return sleep_util_complete(client().get_messages(*args, **kwargs))
