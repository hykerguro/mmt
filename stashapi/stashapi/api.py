from traceback import print_exc
from typing import TypeVar, Any, Iterator

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
    @staticmethod
    def build_param_string(params: dict[str, Any]) -> str:
        if params:
            return "(" + ",".join(f"{k}: {to_params(v)}" for k, v in params.items()) + ")"
        else:
            return ""

    @classmethod
    def query(cls, method_name: str, params: dict[str, Any], ret_cls: type[_T]) -> _T:
        ret = cls.execute(
            "query{" + method_name + cls.build_param_string(params) + ret_cls.to_fields() + "}"
        )
        return ret_cls.from_dict(ret[method_name])

    @classmethod
    def mutation(cls, method_name: str, params: dict[str, Any], ret_cls: type[_T]) -> _T:
        is_list = False
        if ret_cls is not None:
            t, sub = get_origin_type(ret_cls)
            if t is list:
                ret_cls = sub
                is_list = True

        ret = cls.execute(
            "mutation{" + method_name + cls.build_param_string(params) + to_fields(ret_cls) + "}"
        )

        if ret_cls is None:
            return ret[method_name]

        return list(map(lambda x: from_dict(ret_cls, x), ret[method_name])) if is_list \
            else from_dict(ret_cls, ret[method_name])

    @classmethod
    def subscription(cls, method_name: str, params: dict[str, Any], ret_cls: type[_T]) -> Iterator[_T]:
        is_list = False
        if ret_cls is not None:
            t, sub = get_origin_type(ret_cls)
            if t is list:
                ret_cls = sub
                is_list = True

        for ret in cls.client.subscribe(gql(
                "subscription{" + method_name + cls.build_param_string(params) + to_fields(ret_cls) + "}"
        )):
            if ret_cls is None:
                yield ret[method_name]

            yield list(map(lambda x: from_dict(ret_cls, x), ret[method_name])) if is_list \
                else from_dict(ret_cls, ret[method_name])

    @classmethod
    def execute(cls, request_string, **variable_values):
        logger.trace(f"Stash api >>> {request_string}")
        resp = cls.client.execute(gql(request_string), variable_values=variable_values)
        logger.trace(f"Stash api <<< {resp}")
        return resp

    @classmethod
    def find_galleries(cls, gallery_filter: GalleryFilterType | None = None, filter: FindFilterType | None = None,
                       ids: list[int] | None = None) -> FindGalleriesResultType:
        return cls.query("findGalleries", dict(gallery_filter=gallery_filter, filter=filter, ids=ids or []),
                         FindGalleriesResultType)

    @classmethod
    def find_images(cls, image_filter: ImageFilterType | None = None, filter: FindFilterType | None = None,
                    image_ids: list[int] | None = None, ids: list[int] | None = None) -> FindImagesResultType:
        return cls.query("findImages",
                         dict(image_filter=image_filter, filter=filter, image_ids=image_ids or [], ids=ids or []),
                         FindImagesResultType)

    @classmethod
    def download_file(cls, url: str) -> bytes:
        resp = cls.session.get(url)
        return resp.content

    @classmethod
    def metadata_scan(cls, input: ScanMetadataInput | None = None) -> str:
        return cls.mutation("metadataScan", dict(input=input), ret_cls=str)

    @classmethod
    def bulk_image_update(cls, input: BulkImageUpdateInput) -> list[Image]:
        return cls.mutation("bulkImageUpdate", dict(input=input), ret_cls=list[Image])

    @classmethod
    def scan_complete_subscribe(cls) -> Iterator[bool]:
        return cls.subscription("scanCompleteSubscribe", dict(), bool)

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
