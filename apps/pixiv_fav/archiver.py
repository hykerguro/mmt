import json
import math
import time
from pathlib import Path
from typing import Any

from loguru import logger
from peewee import fn

from confctl import config
from .model import BookmarkWork, FollowWork
from pixiv_webapi import PixivWebAPI, PixivWebAPIException

_lp = lambda *_args, **_kwargs: None
try:
    import litter

    litter.connect(config.get("redis/host"), config.get("redis/port"))
    _lp = litter.publish
except (ImportError, KeyError, TypeError) as e:
    from traceback import print_exc

    print_exc()


class PixivFavArchiver:
    papi: PixivWebAPI | None

    def __init__(self):
        self.papi = None

    def refresh_papi(self):
        self.papi = PixivWebAPI(config.get("pixiv_webapi/token"), proxies=config.get("pixiv_webapi/proxy", None))

    def verify_papi(self, max_retries: int = 3):
        logger.info(f"验证Pixiv token有效性...")

        if self.papi is None:
            self.refresh_papi()

        error = None
        for i in range(max_retries):
            try:
                self.papi.user_info()
                logger.info(f"Pixiv token有效")
                return
            except PixivWebAPIException as e:
                error = e
                logger.warning(f"[{i + 1}/{max_retries}] Pixiv token失效: {e}。尝试刷新token。")
                self.refresh_papi()

        _lp("pixiv_fav.verify_papi.fail", str(error))
        raise error

    def get_new_favs(self, max_bookmark_id=None, pagesize: int = 48) -> list[dict[str, Any]]:
        """
        获取收藏的illust，如果不提供stop_sign，只获取第一页
        """
        logger.debug(f"开始获取收藏，{max_bookmark_id=}")
        _lp("pixiv_fav.get_new_favs.start", {"max_bookmark_id": max_bookmark_id, "pagesize": pagesize})

        if max_bookmark_id is None:
            return self.papi.user_bookmarks(limit=pagesize)["works"]

        illusts = []

        def update_result(works):
            for ill in works:
                if int(ill['bookmarkData']['id']) <= int(max_bookmark_id):
                    return True
                illusts.append(ill)
            return False

        page = self.papi.user_bookmarks(limit=pagesize)
        if update_result(page["works"]):
            return illusts

        total = page["total"]
        for offset in range(pagesize, total, pagesize):
            page = self.papi.user_bookmarks(offset=offset, limit=pagesize)
            if page["total"] != total:
                # 收藏发生变化，重来
                logger.warning(f"获取收藏过程中收藏内容变化，重新获取")
                _lp("pixiv_fav.get_new_favs.interchanged", {"total_old": total, "total_new": page["total"]})

                return self.get_new_favs(max_bookmark_id, pagesize)
            if update_result(page["works"]):
                return illusts

        _lp("pixiv_fav.get_new_favs.done", {"max_bookmark_id": max_bookmark_id, "illusts": illusts})
        return illusts

    def get_new_follows(self, max_illust_id: int | None = None) -> list[dict[str, Any]]:
        """
        获取订阅的illust，如果不传max_illust_id，只获取第一页
        """
        logger.debug(f"开始获取收藏，{max_illust_id=}")
        _lp("pixiv_fav.get_new_follows.start", {"max_illust_id": max_illust_id})

        if max_illust_id is None:
            return self.papi.follow_latest_illust()["thumbnails"]["illust"]

        illusts = []

        def update_result(works):
            for ill in works:
                if int(ill['id']) <= int(max_illust_id):
                    return True
                if ill['id'] not in map(lambda x: x["id"], illusts):
                    illusts.append(ill)
            return False

        p = 1
        last_page = False
        while not last_page:
            page = self.papi.follow_latest_illust(p=p)
            if update_result(page["thumbnails"]["illust"]):
                return illusts
            p += 1
            last_page = page["page"]["isLastPage"]

        _lp("pixiv_fav.get_new_follows.done", {"max_illust_id": max_illust_id, "illusts": illusts})
        return illusts

    def download_illust(self, illust_id: int, folder: Path, meta: bool = False, meta_info=None) -> list[str]:
        """
        下载illust到指定目录，文件组织结构：
        folder/
            <illust_id>.json    # 如果meta is True
            <illust_id>_p001.<ext>
            <illust_id>_p002.<ext>
            ...
            <illust_id>_p123.<ext>

        :param illust_id:
        :param folder:
        :param meta: 是否保存元数据
        :return: 下载的图片的链接
        """
        logger.debug(f"开始下载{illust_id=}到{folder}")
        _lp("pixiv_fav.download_illust.start", {"illust_id": illust_id, "folder": str(folder)})

        # 获取图片链接
        pages: list[dict] = self.papi.illust_pages(illust_id)
        urls = [page["urls"]["original"] for page in pages]
        pwidth = math.ceil(math.log10(len(urls) + 1))

        # 下载图片
        folder.mkdir(exist_ok=True, parents=True)
        for i, url in enumerate(urls):
            filepath = (folder / f"{illust_id}_p{str(i).rjust(pwidth, '0')}.{url.rsplit('.')[-1]}")
            self.papi.download(url, filepath)

            # 速度控制
            if i <= len(urls) - 1 and (s := config.get("pixiv_fav/sleep", 0)) > 0:
                logger.debug(f"休息 {s:.2f} 秒")
                time.sleep(s)

        # 保存meta
        if meta or meta_info is not None:
            metapath = (folder / f"{illust_id}.json")
            if meta_info is None:
                meta_info = self.papi.illust(illust_id)
            with open(metapath, "w", encoding="utf-8") as fp:
                json.dump(meta_info, fp, ensure_ascii=False, indent=4)

        logger.debug(f"下载完成{illust_id=}到{folder}")
        _lp("pixiv_fav.download_illust.done",
            {"illust_id": illust_id, "folder": str(folder), "urls": urls})

        return urls

    def archive_fav(self):
        local_dir = Path(config.get("pixiv_fav/local_dir/bookmark"))

        logger.info(f"开始同步收藏 ...")
        _lp("pixiv_fav.archive_fav.start", {"local_dir": str(local_dir)})

        self.verify_papi()

        max_bookmark_id = BookmarkWork.select(fn.MAX(BookmarkWork.bookmark_id)).scalar()
        diff_illusts = self.get_new_favs(max_bookmark_id)

        if not diff_illusts:
            logger.info(f"没有新的收藏")
            return

        logger.info(f"{len(diff_illusts)} 新的收藏，开始同步")
        # 从bookmarkId小的开始同步，避免同步中断导致空隙
        diff_illusts.sort(key=lambda x: int(x["bookmarkData"]["id"]))
        for i, illust in enumerate(diff_illusts):
            logger.info(f"开始下载 {illust['id']} {illust['title']}：{illust['pageCount']} 页")
            original_urls = self.download_illust(illust['id'], local_dir / str(illust['id']), meta_info=illust)

            logger.info(f"写入数据库")
            BookmarkWork.create(
                illust_id=illust["id"],
                bookmark_id=illust["bookmarkData"]["id"],
                is_private=illust["bookmarkData"]["private"],
                create_datetime=illust["createDate"],
                update_datetime=illust["updateDate"],
                meta=illust,
            )
            _lp("pixiv_fav.archive_fav.partdone",
                {"local_dir": str(local_dir), "i": i, "total": len(diff_illusts), "illust": illust,
                 "original_urls": original_urls})

        logger.info(f"同步完成")
        _lp("pixiv_fav.archive_fav.done", {"local_dir": str(local_dir), "diff_illusts": diff_illusts})

    def archive_follow(self):
        local_dir = Path(config.get("pixiv_fav/local_dir/follow"))

        logger.info(f"开始同步关注 ...")
        _lp("pixiv_fav.archive_follow.start", {"local_dir": str(local_dir)})

        self.verify_papi()

        max_illust_id = FollowWork.select(fn.MAX(FollowWork.illust_id)).scalar()
        diff_illusts = self.get_new_follows(max_illust_id)

        if not diff_illusts:
            logger.info(f"没有新的关注")
            return

        logger.info(f"{len(diff_illusts)} 新的关注，开始同步")
        # 从小的开始同步，避免同步中断导致空隙
        diff_illusts.sort(key=lambda x: int(x["id"]))
        for i, illust in enumerate(diff_illusts):
            logger.info(f"开始下载 {illust['id']} {illust['title']}：{illust['pageCount']} 页")
            illust_info = self.papi.illust(illust['id'])
            original_urls = self.download_illust(illust['id'], local_dir / str(illust['id']), meta_info=illust_info)

            logger.info(f"写入数据库")
            FollowWork.create(
                illust_id=illust["id"],
                create_datetime=illust["createDate"],
                update_datetime=illust["updateDate"],
                meta=illust_info,
            )
            _lp("pixiv_fav.archive_follow.partdone",
                {"local_dir": str(local_dir), "i": i, "total": len(diff_illusts), "illust": illust,
                 "original_urls": original_urls})

        logger.info(f"同步完成")
        _lp("pixiv_fav.archive_follow.done", {"local_dir": str(local_dir), "diff_illusts": diff_illusts})
