from traceback import print_exc
from typing import TypeVar, Any

import requests
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from loguru import logger

from .model import *

_T = TypeVar('_T')


class StashAPI:
    @classmethod
    def configure(cls, url: str, token: str):
        cls.url = url
        headers = {
            'Apikey': token
        }
        cls.session = requests.Session()
        cls.session.headers.update(headers)
        cls.client = Client(transport=RequestsHTTPTransport(
            url=url,
            headers=headers,
        ), fetch_schema_from_transport=True)

    @classmethod
    def query(cls, method_name: str, params: dict[str, Any], ret_cls: type[_T]) -> _T:
        assert params
        assert issubclass(ret_cls, StashObject)
        ret = cls.execute(
            "query{" + method_name + "(" +
            ",".join(f"{k}: {to_params(v)}" for k, v in params.items()) +
            ")" + ret_cls.to_fields() + "}"
        )
        return ret_cls.from_dict(ret[method_name])

    @classmethod
    def execute(cls, request_string, **variable_values):
        logger.debug(f"Request string: {request_string}")
        return cls.client.execute(gql(request_string), variable_values=variable_values)

    @classmethod
    def query_find_galleries(cls, gallery_filter: GalleryFilterType | None = None, filter: FindFilterType | None = None,
                             ids: list[int] | None = None) -> FindGalleriesResultType:
        return cls.query("findGalleries", dict(gallery_filter=gallery_filter, filter=filter, ids=ids or []),
                         FindGalleriesResultType)

    @classmethod
    def query_find_images(cls, image_filter: ImageFilterType | None = None, filter: FindFilterType | None = None,
                          image_ids: list[int] | None = None, ids: list[int] | None = None) -> FindImagesResultType:
        return cls.query("findImages",
                         dict(image_filter=image_filter, filter=filter, image_ids=image_ids or [], ids=ids or []),
                         FindImagesResultType)

    @classmethod
    def download_file(cls, url: str) -> bytes:
        resp = cls.session.get(url)
        return resp.content


try:
    from confctl import config

    _url, _token = config.get("stashapi/url"), config.get("stashapi/token")
except (ImportError, KeyError, ValueError):
    pass
else:
    try:
        StashAPI.configure(_url, _token)
    except Exception as e:
        print_exc()
    else:
        logger.info(f"StashAPI.configure succeeded")
