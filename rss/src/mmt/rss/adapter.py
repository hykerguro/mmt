from datetime import datetime
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring


def format_rfc2822(dt: datetime) -> str:
    """格式化为 RSS 使用的 RFC 2822 时间格式"""
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z")


def format_rfc3339(dt: datetime) -> str:
    """格式化为 Atom 使用的 RFC 3339 时间格式"""
    return dt.isoformat()


def jsonfeed_to_rss(feed: dict[str, Any]) -> str:
    """将 JSONFeed (dict) 转换为 RSS 2.0 格式"""
    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")

    # 必填
    SubElement(channel, "title").text = feed.get("title", "")
    SubElement(channel, "link").text = feed.get("home_page_url", "")
    SubElement(channel, "description").text = feed.get("description", "")

    # feed-level image
    if feed.get("icon"):
        image = SubElement(channel, "image")
        SubElement(image, "url").text = feed["icon"]
        SubElement(image, "title").text = feed.get("title", "")
        SubElement(image, "link").text = feed.get("home_page_url", "")

    # items
    for item in feed.get("items", []):
        it = SubElement(channel, "item")
        SubElement(it, "guid").text = item["id"]
        if item.get("url"):
            SubElement(it, "link").text = item["url"]
        if item.get("title"):
            SubElement(it, "title").text = item["title"]
        if item.get("summary"):
            SubElement(it, "description").text = item["summary"]
        elif item.get("content_text"):
            SubElement(it, "description").text = item["content_text"]
        elif item.get("content_html"):
            SubElement(it, "description").text = item["content_html"]

        if item.get("date_published"):
            if isinstance(item["date_published"], datetime):
                SubElement(it, "pubDate").text = format_rfc2822(item["date_published"])
            else:
                SubElement(it, "pubDate").text = str(item["date_published"])

        # 作者
        for author in item.get("authors", []):
            if author.get("name"):
                SubElement(it, "author").text = author["name"]

        # tags
        for tag in item.get("tags", []):
            SubElement(it, "category").text = tag

        # 主图
        if item.get("image"):
            SubElement(it, "enclosure", url=item["image"], type="image/jpeg")

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(rss, encoding="unicode")


def jsonfeed_to_atom(feed: dict[str, Any]) -> str:
    """将 JSONFeed (dict) 转换为 Atom 1.0 格式"""
    feed_elem = Element("feed", xmlns="http://www.w3.org/2005/Atom")

    # 必填
    SubElement(feed_elem, "title").text = feed.get("title", "")
    SubElement(feed_elem, "id").text = feed.get("feed_url", feed.get("home_page_url", "urn:uuid:dummy"))
    SubElement(feed_elem, "updated").text = format_rfc3339(datetime.now())

    if feed.get("home_page_url"):
        SubElement(feed_elem, "link", href=feed["home_page_url"], rel="alternate")
    if feed.get("feed_url"):
        SubElement(feed_elem, "link", href=feed["feed_url"], rel="self")

    # feed-level icon
    if feed.get("icon"):
        SubElement(feed_elem, "icon").text = feed["icon"]
    if feed.get("favicon"):
        SubElement(feed_elem, "logo").text = feed["favicon"]

    # feed-level authors
    for author in feed.get("authors", []):
        a = SubElement(feed_elem, "author")
        if author.get("name"):
            SubElement(a, "name").text = author["name"]
        if author.get("url"):
            SubElement(a, "uri").text = author["url"]
        if author.get("avatar"):
            SubElement(a, "email").text = author["avatar"]  # 没有标准字段，只能塞 email 位置或扩展

    # items
    for item in feed.get("items", []):
        entry = SubElement(feed_elem, "entry")
        SubElement(entry, "id").text = item["id"]

        if item.get("title"):
            SubElement(entry, "title").text = item["title"]
        if item.get("url"):
            SubElement(entry, "link", href=item["url"])

        if item.get("date_published"):
            if isinstance(item["date_published"], datetime):
                SubElement(entry, "updated").text = format_rfc3339(item["date_published"])
            else:
                SubElement(entry, "updated").text = str(item["date_published"])

        if item.get("summary"):
            SubElement(entry, "summary").text = item["summary"]
        elif item.get("content_text"):
            SubElement(entry, "content", type="text").text = item["content_text"]
        elif item.get("content_html"):
            SubElement(entry, "content", type="html").text = item["content_html"]

        # 作者
        for author in item.get("authors", []):
            a = SubElement(entry, "author")
            if author.get("name"):
                SubElement(a, "name").text = author["name"]
            if author.get("url"):
                SubElement(a, "uri").text = author["url"]

        # tags
        for tag in item.get("tags", []):
            SubElement(entry, "category", term=tag)

        # 主图
        if item.get("image"):
            SubElement(entry, "link", rel="enclosure", href=item["image"], type="image/jpeg")

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(feed_elem, encoding="unicode")
