import json
import os.path

from litter import setup

setup("ntfy_test", config_path="config/dev.yaml")

from mmt.agents.pixiv import PixivAgent

api: PixivAgent = PixivAgent.api()


def test_user_bookmars():
    result = api.user_bookmarks()
    assert type(result) == dict
    assert len(result) > 0
    with open("assets/agent.pixiv/user_bookmarks.json", "w", encoding="utf8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)


def test_illust():
    result = api.illust(133116419)
    assert type(result) == dict
    assert result["illustId"] == "133116419"
    with open("assets/agent.pixiv/illust.json", "w", encoding="utf8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)


def test_illust_pages():
    result = api.illust_pages(133116419)
    assert type(result) == list
    with open("assets/agent.pixiv/illust_pages.json", "w", encoding="utf8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)


def test_user_info():
    result = api.user_info()
    assert type(result) == dict
    with open("assets/agent.pixiv/user_info.json", "w", encoding="utf8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)


def test_ugoira_meta():
    result = api.ugoira_meta(87880887)
    assert type(result) == dict
    assert "frames" in result
    with open(f"assets/agent.pixiv/ugoira_meta.json", "w", encoding="utf8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)


def test_download():
    bytes_result = api.download("https://i.pximg.net/img-original/img/2025/07/26/02/51/20/133116419_p0.png", None)
    assert type(bytes_result) == bytes

    api.download("https://i.pximg.net/img-zip-ugoira/img/2021/02/19/03/34/01/87880887_ugoira600x600.zip",
                 "assets/agent.pixiv/ugoira.gif"
                 )
    assert os.path.exists("assets/agent.pixiv/ugoira.gif") == True


def test_follow_latest_illust():
    result = api.follow_latest_illust()
    assert type(result) == dict
    with open("assets/agent.pixiv/follow_latest_illust.json", "w", encoding="utf8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)


def test_top_illust():
    result = api.top_illust()
    assert type(result) == dict
    with open("assets/agent.pixiv/top_illust.json", "w", encoding="utf8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)


def test_bookmarks_add_and_delete():
    result = api.follow_latest_illust()
    id = result["page"]["ids"][0]
    result_add = api.bookmarks_add(id)
    result_delete = api.bookmarks_delete(illust_id=id)
    assert type(result_add) == dict
    assert type(result_delete) == list
    with open("assets/agent.pixiv/bookmarks_add.json", "w", encoding="utf8") as f:
        json.dump(result_add, f, ensure_ascii=False, indent=4)
    with open("assets/agent.pixiv/bookmarks_delete.json", "w", encoding="utf8") as f:
        json.dump(result_delete, f, ensure_ascii=False, indent=4)
