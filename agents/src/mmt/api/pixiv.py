from pathlib import Path
from typing import Literal, TypeAlias, Any

from .framework import ApiBase, api

Json: TypeAlias = dict[str, Any] | list[Any]


@api("mmt.agents.pixiv", download={"timeout": 60})
class PixivApi(ApiBase):
    def resolve(self, url: str, method: Literal["GET", "POST"] = 'GET', data: Any = None) -> bytes:
        ...

    def request(self, method: str, endpoint: str, **kwargs) -> Json | None:
        ...

    def get(self, endpoint: str, params: dict = None, **kwargs) -> Json | None:
        ...

    def user_bookmarks(self, user_id: int | None = None, tag: str = "", offset: int = 0,
                       limit: int = 48, rest: Literal["show", "hide"] = "show") -> Json | None:
        ...

    def illust(self, illust_id: int) -> Json | None:
        """
        illustType: 0-普通；1-漫画；2-ugoira
        :param illust_id:
        :return:
        """
        ...

    def illust_pages(self, illust_id: int | str) -> list[Json] | None:
        ...

    def user_info(self, user_id: int | None = None) -> Json | None:
        ...

    def ugoira_meta(self, illust_id: int | str) -> Json | None:
        ...

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
        ...

    def follow_latest_illust(self, p: int = 1, mode: Literal["all", "r18"] = "all"):
        """
        用户关注的最新作品
        :param p: 页
        :param mode: all/r18
        :return: json
        """
        ...

    def top_illust(self, mode: Literal["all", "r18"] = "all"):
        ...

    def bookmarks_add(self, illust_id: int | str, *, restrict: int = 0, comment: str = "",
                      tags: list[str] | None = None) -> Json | None:
        ...

    def bookmarks_delete(self, *, bookmark_id: int | str | None = None,
                         illust_id: int | str | None = None) -> Json | None:
        ...
