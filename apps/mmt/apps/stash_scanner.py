"""
1. pixiv fav 下载完成后执行stash扫描
2. stash 定时扫描
"""
from pathlib import Path

APP_NAME = "stash_scanner"
from confctl import config, util

util.default_arg_config_loggers("stash_scanner/logs")

import litter

litter.connect(config.get("redis/host"), config.get("redis/port"), app_name=APP_NAME)

from loguru import logger

from stashapi import StashAPI, ImageFilterType, MultiCriterionInput, CriterionModifier, FindFilterType, \
    SortDirectionEnum, Image, BulkImageUpdateInput, BulkUpdateIds, BulkUpdateIdMode
from stashapi.model import ScanMetadataInput
from schd.api import on


def path_proxy(path: str | Path) -> str:
    path = str(path)
    for mapper in config.get("stash_scanner/path_mapper", []):
        host_path, container_path = mapper.split(":")
        if path.startswith(host_path):
            path = container_path + path[len(host_path):]
    return path


def belonging_gallery(image: Image) -> int | None:
    for path, gallery_id in map(lambda x: x.split(":"), config.get("stash_scanner/archive", [])):
        if image.visual_files[0].path.startswith(path):
            return gallery_id
    return None


@on("stash.fav.archive", "cron", crontab=config.get("stash_scanner/fav_archive/crontab", "20 * * * *"))
def archive(message: litter.Message) -> None:
    """
    定时扫描所有不属于图库的照片，归档到pixiv fav和follow
    :param message:
    :return:
    """
    logger.info(f"归档 pixiv fav ...")
    belongs = {}

    page = 1
    while True:
        resp = StashAPI.find_images(
            image_filter=ImageFilterType(galleries=MultiCriterionInput(modifier=CriterionModifier.IS_NULL)),
            filter=FindFilterType(per_page=1000, page=page, sort="updated_at", direction=SortDirectionEnum.DESC)
        )
        if not resp.images:
            break

        for image in resp.images:
            if gallery_id := belonging_gallery(image):
                belongs.setdefault(gallery_id, []).append(image)
        page += 1
    logger.info(f"归档图片数量 {sum(map(len, belongs.values()))}")

    # do archive
    for gallery_id, images in belongs.items():
        StashAPI.bulk_image_update(
            BulkImageUpdateInput(gallery_ids=BulkUpdateIds(mode=BulkUpdateIdMode.ADD, ids=[gallery_id]),
                                 ids=[image.id for image in images]))
        logger.info(f"{len(images)}张图片添加到图库{gallery_id}")


# 监测Pixiv下载扫描
@litter.subscribe(["pixiv_fav.archive_follow.done", "pixiv_fav.archive_fav.done"])
def on_pixiv_archive_done(message: litter.Message):
    """
    pixiv fav 结束后扫描stash照片
    :param message:
    :return:
    """
    logger.debug(f"on_pixiv_archive_done: {message}")

    data = message.json()
    local_dir = Path(data["local_dir"])

    iids = [x['id'] for x in data["diff_illusts"]]
    if iids:
        logger.info(f"监测到Pixiv归档完毕：{message.channel}，{local_dir=}, {iids=}")
    else:
        logger.info(f"无新增")
        return

    for iid in iids:
        (local_dir / str(iid) / ".nogallery").open("wb").close()

    scan_id = StashAPI.metadata_scan(ScanMetadataInput(
        paths=[str(path_proxy(local_dir))], scanGenerateCovers=True, scanGeneratePreviews=True,
        scanGenerateImagePreviews=True, scanGenerateThumbnails=True, scanGenerateClipPreviews=True))
    logger.info(f"Stash扫描任务开始，任务id={scan_id}")


# 定时全库扫描
@on("stash.scanner.period.scan", "cron", crontab=config.get("stash_scanner/period_scan/crontab", "0 6 * * *"))
def period_scan(message: litter.Message):
    scan_id = StashAPI.metadata_scan(ScanMetadataInput(
        scanGenerateCovers=True, scanGeneratePreviews=True,
        scanGenerateImagePreviews=True, scanGenerateThumbnails=True, scanGenerateClipPreviews=True,
        scanGeneratePhashes=True, scanGenerateSprites=True
    ))
    logger.info(f"Stash Scanner 定时扫描：{scan_id=}")


logger.info(f"stash scanner 开始监听")
litter.listen(config.get("redis/host"), config.get("redis/port"), APP_NAME)
