from pathlib import Path
from typing import Literal, Any

from litter.adapter import api
from . import APP_NAME
from .webapi import Json


@api(APP_NAME)
def get(endpoint: str, params: dict = None, **kwargs) -> Json | None:
    """
    HTTP GET 请求
    :param endpoint: 请求路径
    :param params:  query参数
    :param kwargs:  其他参数
    :return: json
    """
    ...


@api(APP_NAME)
def request(method: str, endpoint: str, **kwargs) -> Json | None:
    ...


@api(APP_NAME)
def user_bookmarks(user_id: int | None = None, tag: str = "", offset: int = 0,
                   limit: int = 48, rest: Literal["show", "hide"] = "show") -> Json | None:
    """
    获取用户的收藏
    :param user_id: 用户id；缺省值为当前用户
    :param tag: 指定tag
    :param offset: 页偏移
    :param limit:  页尺寸
    :param rest:
    :return: json
    """
    ...


@api(APP_NAME)
def illust(illust_id: int) -> Json | None:
    """
    illust信息

    :param illust_id:
    :return: json illustType: 0-普通；1-漫画；2-ugoira
    """


@api(APP_NAME)
def illust_pages(illust_id: int | str) -> list[Json] | None:
    """
    获取图片链接
    :param illust_id:
    :return: json
    """
    ...


@api(APP_NAME)
def user_info(user_id: int | None = None) -> Json | None:
    """
    用户信息
    :param user_id:
    :return:
    """
    ...


@api(APP_NAME)
def ugoira_meta(illust_id: int | str) -> Json | None:
    """
    ugoira元数据
    :param illust_id:
    :return:
    """
    ...


@api(APP_NAME)
def download(url: str, path: str | Path | None, max_retries: int = 3, timeout: float = 10.,
             *, frames: list[dict[str, Any]] | None = None) -> bytes | None:
    """
    下载illust（支持ugoira）
    :param url: URL路径
    :param path: 下载路径；为None时下载到内存从并将二进制数据返回；下载ugoira且下载路径以.gif结尾时，自动转换为gif动图
    :param max_retries: 最大尝试次数
    :param timeout: 超时时间
    :param frames: ugoira的帧率信息；可选，为None时会自动发起请求获取
    :return: 如果path为None，则返回下载的图片的二进制数据
    """
    ...


@api(APP_NAME)
def follow_latest_illust(p: int = 1, mode: Literal["all", "r18"] = "all"):
    """
    用户关注的最新作品
    :param p: 页
    :param mode: all/r18
    :return: json
    """
    ...


@api(APP_NAME)
def top_illust(mode: Literal["all", "r18"] = "all"):
    """

    :param mode:
    :return:
    """
    ...


@api(APP_NAME)
def resolve(url: str, method: Literal["GET", "POST"] = 'GET', data: Any = None) -> bytes | None:
    ...


@api(APP_NAME)
def bookmarks_add(self, illust_id: int | str, *, restrict: int = 0, comment: str = "",
                  tags: list[str] | None = None) -> Json | None:
    """
    添加到收藏
    :param self:
    :param illust_id:
    :param restrict:
    :param comment:
    :param tags:
    :return:
    """


@api(APP_NAME)
def bookmarks_delete(*, bookmark_id: int | str | None = None, illust_id: int | str | None = None) -> Json | None:
    """
    删除收藏
    :param self:
    :param illust_id:
    :return:
    """
