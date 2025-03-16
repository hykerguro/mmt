import io
import re
import zipfile
from pathlib import Path
from time import sleep, time
from typing import TypeAlias, Any, Literal

import requests
from PIL import Image
from loguru import logger

__all__ = [
    "PixivWebAPI",
    "PixivWebAPIException"
]

Json: TypeAlias = dict[str, Any] | list[Any]

_lp = lambda *_args, **_kwargs: None
try:
    import litter
    import redis
    from confctl import config

    litter.connect(config.get("redis/host"), config.get("redis/port"))
    _lp = litter.publish
except (ImportError, KeyError, TypeError, ConnectionRefusedError, redis.exceptions.ConnectionError):
    pass


class PixivWebAPIException(Exception):
    pass


class PixivWebAPI:
    def __init__(self, php_session_id: str, lang: str = "zh", proxies=None, *, min_interval: float=0.5):
        self.lang = lang
        self.base_url = "https://www.pixiv.net/ajax"
        self.session = requests.Session()
        self.session.cookies.set("PHPSESSID", php_session_id)
        self.user_id = int(php_session_id.split("_")[0])
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0"
        })
        if proxies and isinstance(proxies, dict):
            self.session.proxies.update(proxies)
        self.min_interval = min_interval
        self._last_request_time = 0.

    def _request(self, method: str, endpoint: str, params: dict = None, data: dict = None, **kwargs) -> Json | None:
        if (itv := time() - self._last_request_time) < self.min_interval:
            s = self.min_interval - itv
            logger.debug(f"请求过于频繁，等待{s:.2f}秒")
            sleep(s)
        
        self._last_request_time = time()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        if params is None:
            params = {}
        if "lang" not in params:
            params["lang"] = self.lang

        try:
            logger.debug(f"{method} {url} {params}")
            self.session.request(method, url, params=params, **kwargs)
            response = self.session.get(url, params=params, json=data)
            response.raise_for_status()
            logger.debug(f"响应: {response.status_code} {response.text[:100]}...")
            ret_data = response.json()
            if ret_data["error"]:
                _lp("pixiv_webapi.request.error",
                    {"method": method, "url": url, "params": params, "ret_data": ret_data})
                raise PixivWebAPIException(ret_data["message"])
            _lp("pixiv_webapi.request.success", {"method": method, "url": url, "params": params, "ret_data": ret_data})
            return ret_data["body"]
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {e}")
            _lp("pixiv_webapi.request.fail", {"method": method, "url": url, "params": params, "error": e})
            raise e

    def get(self, endpoint: str, params: dict = None, **kwargs) -> Json | None:
        return self._request(method="GET", endpoint=endpoint, params=params, **kwargs)

    def post(self, endpoint: str, data: dict = None, **kwargs) -> Json | None:
        return self._request(method="POST", endpoint=endpoint, data=data, **kwargs)

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

    def download(self, url: str, path: str | Path, max_retries: int = 3, timeout: float = 10.,
                 *, frames: list[dict[str, Any]] | None = None):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fail_reason = []
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, stream=True, timeout=timeout,
                                            headers={"Referer": "https://www.pixiv.net/"})
                if response.status_code != 200:
                    logger.error(f"图片 {url} 下载失败，状态码: {response.status_code}")
                    fail_reason.append(f"Status Code: {response.status_code}")

                if (mat := re.match(r".+(?P<iid>\d+)_ugoira.+\.zip$", url)) is not None:
                    iid = mat.group("iid")
                    zip_buffer = io.BytesIO(response.content)

                    if path.suffix == ".gif":
                        if frames is None:
                            frames = self.ugoira_meta(iid)["frames"]
                        logger.debug("开始转换ugoira为gif")
                        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
                            images = [Image.open(io.BytesIO(zip_file.read(frame["file"]))) for frame in frames]
                            durations = [frame["delay"] for frame in frames]
                            images[0].save(path, save_all=True, append_images=images[1:], duration=durations, loop=0)
                    else:
                        with open(path, "wb") as f:
                            f.write(zip_buffer.getvalue())
                else:
                    with open(path, "wb") as f:
                        chunk_size = 1024 * 1024  # 1 MB
                        for chunk in response.iter_content(chunk_size=chunk_size):
                            if chunk:
                                f.write(chunk)

                logger.info(f"图片 {url} 已成功下载并保存为 {path}")
                _lp("pixiv_webapi.download.success", {"url": url, "path": path})
                return

            except requests.exceptions.RequestException as e:
                logger.warning(f"图片 {url} 下载出错：{e}，重试次数: {attempt + 1}/{max_retries}")
                fail_reason.append(f"Error: {e}")
                if attempt < max_retries - 1:
                    sleep(timeout)
                else:
                    logger.error(f"图片 {url} 重试已超过最大次数，下载失败")
        _lp(f"pixiv_webapi.download.error", {"url": url, "path": path, "fail_reason": fail_reason})

    def follow_latest_illust(self, p: int = 1, mode: Literal["all", "r18"] = "all"):
        return self.get(f"follow_latest/illust", params={"p": p, "mode": mode})

    def top_illust(self, mode: Literal["all", "r18"] = "all"):
        return self.get(f"top/illust", params={"mode": mode})
