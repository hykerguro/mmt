from datetime import datetime
from typing import Iterator

import pytz
from eh_api.exception import GalleryNotAvailable, GalleryNotFound
from eh_api.model import Gallery
from loguru import logger

from eh_api import get_fav, get_gallery, ROOT
from model import GalleryEntity

__all__ = [
    "root_url",
    "check_update",
    "get_gallery",
    "check_single_gallery_update",
    "iter_all_galleries_update",
    "track_gallery",
    "track_fav",
]

def root_url() -> str:
    return ROOT


def check_update(gid: int, token: str) -> Gallery | None:
    """
    如果有更新返回最新图库，否则返回None
    """
    origin_gallery = get_gallery(gid, token)
    if not origin_gallery.newer:
        return None
    latest_gallery_url, latest_gallery_datetime = origin_gallery.newer[-1]
    return get_gallery(latest_gallery_url)


def gallery_diff(gallery_old: Gallery, gallery_new: Gallery) -> list[str]:
    diffs = [f"{attr}: {getattr(gallery_old, attr)} -> {getattr(gallery_new, attr)}" for attr in (
        "gid", "token", "title", "title_jpn", "thumb", "eh_category", "uploader", "filecount", "date")
             if getattr(gallery_old, attr) != getattr(gallery_new, attr)]
    return diffs


def check_single_gallery_update(gallery: Gallery) -> tuple[Gallery, list[str]] | None:
    """
    if the gallery has been updated, return (the latest gallery, diff),
    otherwise return None
    """
    if gallery.id is None:
        raise ValueError("gallery.id cannot be None")

    latest_gallery = check_update(gallery.gid, gallery.token)
    if latest_gallery is not None:
        latest_gallery.id = gallery.id
        logger.info(f"图库 {gallery.id} [{gallery.title}] 有更新:")
        diffs = gallery_diff(gallery, latest_gallery)
        for diff in diffs:
            logger.info(diff)
        # dao.update_gallery(latest_gallery)
        GalleryEntity.update(
            gid=latest_gallery.gid,
            token=latest_gallery.token,
            title=latest_gallery.title,
            title_jpn=latest_gallery.title_jpn,
            thumb=latest_gallery.thumb,
            eh_category=latest_gallery.eh_category,
            uploader=latest_gallery.uploader,
            expunged=int(latest_gallery.expunged) if latest_gallery.expunged is not None else None,
            date=latest_gallery.date.isoformat() if latest_gallery.date is not None else None,
            filecount=latest_gallery.filecount,
        ).where(GalleryEntity.id == latest_gallery.id).execute()
        return latest_gallery, diffs


def ge2g(ge: GalleryEntity) -> Gallery | None:
    if ge is None:
        return None
    return Gallery.from_dict(dict(
        id=ge.id,
        gid=ge.gid,
        token=ge.token,
        title=ge.title,
        title_jpn=ge.title_jpn,
        thumb=ge.thumb,
        eh_category=ge.eh_category,
        uploader=ge.uploader,
        expunged=ge.expunged,
        date=datetime.fromisoformat(ge.date).astimezone(
            pytz.timezone("Asia/Shanghai")) if ge.date is not None else None,
        filecount=ge.filecount,
    ))


def iter_all_galleries_update() -> Iterator[tuple[Gallery, list[str]]]:
    """
    yield all updated galleries and diffs
    """
    memo = {}

    def _update_memo(_g):
        if _g.gid in memo:
            # dao.delete_gallery(_g.id)
            GalleryEntity.get(GalleryEntity.gid == _g.gid).delete_instance()
            logger.warning(f"追踪列表中有重复项({_g.gid}, {_g.token}): id={_g.id},id={memo[_g.gid]}；已删除id={_g.id}")
            return True
        else:
            memo[_g.gid] = _g.id
            return False

    for ge in GalleryEntity.select():
        # for gallery in dao.fetch_all_galleries():
        gallery = ge2g(ge)
        update = check_single_gallery_update(gallery)
        if update is not None:
            if _update_memo(update[0]):
                continue
            yield update
        else:
            _update_memo(gallery)


def list_all_galleries_update() -> list[tuple[Gallery, list[str]]]:
    """
    list all updated galleries and diffs
    """
    return list(iter_all_galleries_update())


def track_gallery(gid: int | str, token: str, check: bool = True, suppress_duplicate_warning: bool = False) -> int:
    if check and (latest_gallery := check_update(gid, token)) is not None:
        gallery = latest_gallery
    else:
        gallery = get_gallery(gid, token)
    ge = GalleryEntity.select().where(GalleryEntity.gid == gallery.gid, GalleryEntity.token == gallery.token).first()
    record = ge2g(ge)
    if record is None:
        # id = dao.insert_gallery(gallery)
        ng = GalleryEntity.create(
            gid=gallery.gid,
            token=gallery.token,
            title=gallery.title,
            title_jpn=gallery.title_jpn,
            thumb=gallery.thumb,
            eh_category=gallery.eh_category,
            uploader=gallery.uploader,
            expunged=int(gallery.expunged) if gallery.expunged is not None else None,
            date=gallery.date.isoformat() if gallery.date is not None else None,
            filecount=gallery.filecount,
        )
        id = ng.id
        logger.info(f"图库({gallery.title}) 已添加至追踪列表: {id=}")
    else:
        if not suppress_duplicate_warning:
            logger.warning(f"图库({gallery.title} 在追踪列表中已经存在！")
        id = record.id
    return id


def track_fav():
    favs = get_fav()
    for gid, token in favs:
        try:
            track_gallery(gid, token, check=False, suppress_duplicate_warning=True)
        except (GalleryNotAvailable, GalleryNotFound):
            pass
