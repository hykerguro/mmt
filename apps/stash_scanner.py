"""
1. pixiv fav 下载完成后执行stash扫描
2. stash 定时扫描
"""
from pathlib import Path

APP_NAME = "stash_scanner"
from confctl import config, util

util.default_arg_config_loggers("stash_scanner/logs")

import litter
from loguru import logger

from stashapi import StashAPI
from stashapi.model import ScanMetadataInput


# 监测Pixiv下载
@litter.subscribe(["pixiv_fav.archive_follow.done", "pixiv_fav.archive_fav.done"])
def on_pixiv_archive_done(message: litter.Message):
    data = message.json()
    local_dir = Path(data["local_dir"])
    iids = [x['id'] for x in data["diff_illusts"]]
    logger.info(f"监测到Pixiv归档完毕：{message.channel}，{local_dir=}, {iids=}")

    if not (local_dir / '.forcegallery').exists():
        (local_dir / '.forcegallery').open("wb").close()
    for iid in iids:
        (local_dir / str(iid) / ".nogallery").open("wb").close()

    scan_id = StashAPI.metadata_scan(ScanMetadataInput(
        paths=[str(local_dir)], scanGenerateCovers=True, scanGeneratePreviews=True,
        scanGenerateImagePreviews=True, scanGenerateThumbnails=True, scanGenerateClipPreviews=True))
    logger.info(f"Stash扫描任务开始，任务id={scan_id}")


# 定时扫描
crontab = config.get("stash_scanner/period_scan/crontab", None)
if crontab:
    litter.connect(config.get("redis/host"), config.get("redis/port"), APP_NAME)
    from schd.api import add_job

    job_id = add_job("stash.scanner.period.scan", None, "cron", crontab=crontab, replace_existing=True,
                     id="stash_scanner.period")
    logger.info(f"添加Stash定时扫描任务：{crontab=}, {job_id=}")


    @litter.subscribe("stash.scanner.period.scan")
    def period_scan(message: litter.Message):
        scan_id = StashAPI.metadata_scan(ScanMetadataInput(
            scanGenerateCovers=True, scanGeneratePreviews=True,
            scanGenerateImagePreviews=True, scanGenerateThumbnails=True, scanGenerateClipPreviews=True,
            scanGeneratePhashes=True, scanGenerateSprites=True
        ))
        logger.info(f"Stash Scanner 定时扫描：{scan_id=}")

litter.listen(config.get("redis/host"), config.get("redis/port"), APP_NAME)
