import io
import re
import zipfile
from pathlib import Path
from tempfile import TemporaryFile
from time import sleep, time
from typing import TypeAlias, Any, Literal

import requests
from PIL import Image
from loguru import logger

from litter.adapt import agent, FromConfig
from mmt.api.pixiv import PixivApi

Json: TypeAlias = dict[str, Any] | list[Any]


class PixivWebAPIException(Exception):
    pass


@agent("mmt.agent.pixiv",
       init_args=(FromConfig("pixiv_webapi/php_session_id"), FromConfig("pixiv_webapi/csrf_token"))
       )
class PixivWebAPI(PixivApi):
    def __init__(self, php_session_id: str, csrf_token: str, lang: str = "zh", proxies=None, *,
                 min_interval: float = 0.5):
        self.lang = lang
        self.base_url = "https://www.pixiv.net/ajax"
        self.session = requests.Session()
        self.session.cookies.set("PHPSESSID", php_session_id)
        self.user_id = int(php_session_id.split("_")[0])
        self.session.headers.update({
            "accept-encoding": "application/json",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0",
            "x-csrf-token": csrf_token,
        })
        if proxies and isinstance(proxies, dict):
            self.session.proxies.update(proxies)
        self.min_interval = min_interval
        self._last_request_time = 0.

    def resolve(self, url: str, method: Literal["GET", "POST"] = 'GET', data: Any = None) -> bytes:
        return self.session.request(method=method, url=url, data=data,
                                    headers={"Referer": "https://www.pixiv.net/"}).content

    def request(self, method: str, endpoint: str, **kwargs) -> Json | None:
        if (itv := time() - self._last_request_time) < self.min_interval:
            s = self.min_interval - itv
            logger.debug(f"请求过于频繁，等待{s:.2f}秒")
            sleep(s)

        self._last_request_time = time()

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        if method == "GET":
            if "params" not in kwargs or not kwargs["params"]:
                kwargs["params"] = {}
            if "lang" not in kwargs["params"]:
                kwargs["params"]["lang"] = self.lang

        try:
            logger.debug(f"{method} {url} {kwargs}")
            response = self.session.request(method, url, **kwargs)
            # response.raise_for_status()
            logger.debug(f"响应: {response.status_code} {response.text[:100]}...")
            ret_data = response.json()
            if ret_data["error"]:
                raise PixivWebAPIException(f"{method} {endpoint}: {ret_data}")
            return ret_data["body"]
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {e}")
            raise e

    def get(self, endpoint: str, params: dict = None, **kwargs) -> Json | None:
        return self.request(method="GET", endpoint=endpoint, params=params, **kwargs)

    def user_bookmarks(self, user_id: int | None = None, tag: str = "", offset: int = 0,
                       limit: int = 48, rest: Literal["show", "hide"] = "show") -> Json | None:
        if user_id is None:
            user_id = self.user_id
        return self.get(f"user/{user_id}/illusts/bookmarks",
                        params={"tag": tag, "offset": offset, "limit": limit, "rest": rest})

    def illust(self, illust_id: int) -> Json | None:
        """
        illustType: 0-普通；1-漫画；2-ugoira
        :param illust_id:
        :return:
        """
        return self.get(f"illust/{illust_id}")

    def illust_pages(self, illust_id: int | str) -> list[Json] | None:
        return self.get(f"illust/{illust_id}/pages")

    def user_info(self, user_id: int | None = None) -> Json | None:
        if user_id is None:
            user_id = self.user_id
        return self.get(f"user/{user_id}", headers={"Referer": f"https://www.pixiv.net/member.php?id={user_id}"})

    def ugoira_meta(self, illust_id: int | str) -> Json | None:
        return self.get(f"illust/{illust_id}/ugoira_meta")

    def download(self, url: str, path: str | Path | None, max_retries: int = 3, timeout: float = 10.,
                 *, frames: list[dict[str, Any]] | None = None) -> bytes | bool | None:
        """
        下载illust（支持ugoira）
        :param url: URL路径
        :param path: 下载路径；为None时下载到内存从并将二进制数据返回；下载ugoira且下载路径以.gif结尾时，自动转换为gif动图
        :param max_retries: 最大尝试次数
        :param timeout: 超时时间
        :param frames: ugoira的帧率信息；可选，为None时会自动发起请求获取
        :return: 如果path为None，则返回下载的图片的二进制数据；否则返回下载是否成功
        """
        if path is None:
            file = TemporaryFile(mode="w+b")
        else:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            file = open(path, "wb")

        fail_reason = []
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, stream=True, timeout=timeout,
                                            headers={"Referer": "https://www.pixiv.net/"})
                if response.status_code != 200:
                    logger.error(f"图片 {url} 下载失败，状态码: {response.status_code}")
                    fail_reason.append(f"Status Code: {response.status_code}")

                if (mat := re.match(r".+/(?P<iid>\d+)_ugoira.+\.zip$", url)) is not None:
                    iid = mat.group("iid")
                    zip_buffer = io.BytesIO(response.content)

                    if path is None or path.suffix == ".gif":
                        if frames is None:
                            frames = self.ugoira_meta(iid)["frames"]
                        logger.debug("开始转换ugoira为gif")
                        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
                            images = [Image.open(io.BytesIO(zip_file.read(frame["file"]))) for frame in frames]
                            durations = [frame["delay"] for frame in frames]
                            images[0].save(file, save_all=True, append_images=images[1:], duration=durations, loop=0)
                    else:
                        file.write(zip_buffer.getvalue())
                else:
                    chunk_size = 1024 * 1024  # 1 MB
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            file.write(chunk)

                logger.info(f"图片 {url} 已成功下载并保存为 {path}")
                break

            except requests.exceptions.RequestException as e:
                logger.warning(f"图片 {url} 下载出错：{e}，重试次数: {attempt + 1}/{max_retries}")
                fail_reason.append(f"Error: {e}")
                if attempt < max_retries - 1:
                    sleep(timeout)
                else:
                    logger.error(f"图片 {url} 重试已超过最大次数，下载失败")
                return None if path is None else False

        if path is None:
            file.seek(0)
            res = file.read()
            file.close()
            return res

        if file is not None:
            file.close()

        return True

    def follow_latest_illust(self, p: int = 1, mode: Literal["all", "r18"] = "all"):
        """
        用户关注的最新作品
        :param p: 页
        :param mode: all/r18
        :return: json
        """
        return self.get(f"follow_latest/illust", params={"p": p, "mode": mode})

    def top_illust(self, mode: Literal["all", "r18"] = "all"):
        return self.get(f"top/illust", params={"mode": mode})

    def bookmarks_add(self, illust_id: int | str, *, restrict: int = 0, comment: str = "",
                      tags: list[str] | None = None) -> Json | None:
        tags = tags or []
        return self.request("POST", "illusts/bookmarks/add",
                            json={
                                "illust_id": str(illust_id),
                                "restrict": restrict,
                                "comment": comment,
                                "tags": tags
                            })

    def bookmarks_delete(self, *, bookmark_id: int | str | None = None,
                         illust_id: int | str | None = None) -> Json | None:
        if bookmark_id is None:
            assert illust_id is not None
            bookmark_data = self.illust(illust_id)["bookmarkData"]
            if not bookmark_data or not bookmark_data["id"]:
                return None
            bookmark_id = bookmark_data["id"]
        return self.request("POST", "illusts/bookmarks/delete", data={"bookmark_id": bookmark_id})
