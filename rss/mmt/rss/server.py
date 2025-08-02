import importlib.util
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote

import pytz
from fastapi import FastAPI, Response, Query, HTTPException
from feedgen.feed import FeedGenerator
from loguru import logger

import litter
from confctl import config

config.load_config("config/dev.yaml")
litter.connect(config.get('redis/host'), config.get('redis/port'), app_name='rss_server')


# region model定义

@dataclass
class MmtItem:
    id: str
    title: str
    description: str = ""
    link: str = ""
    image: str = ""
    author: str = ""
    pub_date: datetime = None


class AbstractSupplier(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    def description(self) -> str:
        return self.name

    @abstractmethod
    def supply(self) -> list[MmtItem]:
        pass

    @abstractmethod
    def resolve(self, url: str) -> bytes | None:
        pass


# endregion


def load_supplier(channel: str) -> AbstractSupplier:
    """
    加载supplier，查找文件夹由配置项rss/suppliers/path定义
    :param channel:
    :return:
    """
    if channel not in supplier_pool:
        paths = config.get("rss/suppliers/path", [os.path.dirname(os.path.abspath(__file__)) + "/suppliers"])
        if not paths:
            raise ValueError("Invalid supplier channel")

        filename = channel + ".py"
        for path in paths:
            file_path = os.path.join(path, filename)
            if os.path.isfile(file_path):
                module_name = f"_supplier_{channel}_{abs(hash(file_path))}"
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if not spec or not spec.loader:
                    raise ImportError(f"无法加载模块: {file_path}")
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                if not hasattr(module, "supplier"):
                    raise AttributeError(f"模块 {file_path} 中未定义变量 supplier")

                supplier = getattr(module, "supplier")

                if not isinstance(supplier, AbstractSupplier):
                    raise TypeError(f"{file_path} 中的 supplier 不是 AbstractSupplier 的实例")

                supplier_pool[channel] = supplier

    return supplier_pool[channel]


# region http服务器


supplier_pool: dict[str, AbstractSupplier] = {}

app = FastAPI()


@app.get("/resolve")
def resolve_url(
        channel: str = Query(..., description="Channel"),
        url: str = Query(..., description="URL to resolve")
) -> Response:
    if channel not in supplier_pool:
        raise HTTPException(status_code=404, detail="Channel not found")
    logger.info(f"Resolving {url} for {channel}")
    result = supplier_pool.get(channel).resolve(url)
    if result is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return Response(content=result, media_type="application/octet-stream")


@app.get("/rss")
def generate_rss(channel: str = Query(..., description="Channel")) -> Response:
    try:
        supplier = load_supplier(channel)
    except ImportError:
        raise HTTPException(status_code=404, detail="Channel not found")

    fg = FeedGenerator()
    fg.load_extension("media")
    fg.id(f"mmt.rss.{channel}")
    fg.title(supplier.name)
    fg.link(href="https://{}/rss?channel={}".format(config.get("rss/host"), channel), rel="alternate")
    fg.description(supplier.description())
    fg.language("zh-cn")
    fg.lastBuildDate(datetime.now(pytz.timezone("Asia/Shanghai")))

    for item in supplier.supply():
        logger.debug(item)
        fe = fg.add_entry()
        fe.id(f'{channel}_{item.id}')
        fe.title(item.title)
        fe.link(href=item.link)
        fe.pubDate(item.pub_date)
        fe.description(item.description)
        # Media RSS 扩展
        me = fe.media
        me.content(
            url=f"/resolve?channel={channel}&url={quote(item.image)}",
            type='image/jpeg',
            medium="image"
        )

    rss_str = fg.rss_str(pretty=True)
    return Response(content=rss_str, media_type="application/xml")

# endregion
