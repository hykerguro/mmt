import math
import re
import ssl
from pathlib import Path
from typing import Iterator

import requests
from loguru import logger
from requests.adapters import HTTPAdapter
from requests.cookies import RequestsCookieJar

from . import exception
from . import text
from .exception import AuthenticationError, GalleryNotAvailable, GalleryNotFound
from .model import Image, Gallery
from .text import unquote

__all__ = [
    "get_gallery",
    "get_fav",
    "DataSource",
    "refresh_ds",
    "download_image",
    "auth",
    "ROOT",
    "AGENT"
]

_adapter_cache = {}


def parse_gid_token(url: str) -> tuple[int, str]:
    mat = re.match(r"https?://e[-x]hentai.org/g/(\d+)/(\w+)/?", url)
    if not mat:
        raise ValueError(f"Invalid Gallery URL: {url}")
    return int(mat.group(1)), mat.group(2)


class RequestsAdapter(HTTPAdapter):

    def __init__(self, ssl_context=None, source_address=None):
        self.ssl_context = ssl_context
        self.source_address = source_address
        HTTPAdapter.__init__(self)

    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = self.ssl_context
        kwargs["source_address"] = self.source_address
        return HTTPAdapter.init_poolmanager(self, *args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        kwargs["ssl_context"] = self.ssl_context
        kwargs["source_address"] = self.source_address
        return HTTPAdapter.proxy_manager_for(self, *args, **kwargs)


def _build_requests_adapter(ssl_options, ssl_ciphers, source_address):
    global _adapter_cache
    key = (ssl_options, ssl_ciphers, source_address)
    try:
        return _adapter_cache[key]
    except KeyError:
        pass

    if ssl_options or ssl_ciphers:
        ssl_context = ssl.create_default_context()
        if ssl_options:
            ssl_context.options |= ssl_options
        if ssl_ciphers:
            ssl_context.set_ecdh_curve("prime256v1")
            ssl_context.set_ciphers(ssl_ciphers)
    else:
        ssl_context = None

    adapter = _adapter_cache[key] = RequestsAdapter(
        ssl_context, source_address)
    return adapter


def language_to_code(lang, default=None):
    """Map a language name to its ISO 639-1 code"""
    CODES = {
        "ar": "Arabic",
        "bg": "Bulgarian",
        "ca": "Catalan",
        "cs": "Czech",
        "da": "Danish",
        "de": "German",
        "el": "Greek",
        "en": "English",
        "es": "Spanish",
        "fi": "Finnish",
        "fr": "French",
        "he": "Hebrew",
        "hu": "Hungarian",
        "id": "Indonesian",
        "it": "Italian",
        "ja": "Japanese",
        "ko": "Korean",
        "ms": "Malay",
        "nl": "Dutch",
        "no": "Norwegian",
        "pl": "Polish",
        "pt": "Portuguese",
        "ro": "Romanian",
        "ru": "Russian",
        "sv": "Swedish",
        "th": "Thai",
        "tr": "Turkish",
        "vi": "Vietnamese",
        "zh": "Chinese",
    }
    if lang is None:
        return default
    lang = lang.capitalize()
    for code, language in CODES.items():
        if language == lang:
            return code
    return default


class DataSource:

    def __init__(self,
                 credentials: dict[str, str] | None = None,
                 *,
                 headers: dict[str, str] | None = None,
                 proxies: dict[str, str] | None = None,
                 domain: str = "exhentai",
                 ):
        self.domain = domain
        self.credentials = credentials
        self.headers = headers
        self.proxies = proxies
        # TODO: check ua
        self.root = f"https://{domain}.org"
        if domain == "e-hentai":
            self.api_url = "https://api.e-hentai.org/api.php"
        elif domain == "exhentai":
            self.api_url = "https://s.exhentai.org/api.php"
        else:
            raise ValueError(f"Invalid domain: {domain}")
        self._init_session()

    def _init_session(self):
        logger.debug(f"init session")
        self.session = session = requests.Session()
        headers = session.headers
        headers.clear()
        ssl_options = 0

        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
        headers["Accept"] = "*/*"
        headers["Accept-Language"] = "en-US,en;q=0.5"
        headers["Accept-Encoding"] = "gzip, deflate"
        headers["Referer"] = self.root + "/"
        if self.headers:
            headers.update(self.headers)

        if self.proxies:
            session.proxies = self.proxies

        adapter = _build_requests_adapter(ssl_options, None, None)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

    def _auth_by_username(self, username: str, password: str) -> RequestsCookieJar:
        url = "https://forums.e-hentai.org/index.php?act=Login&CODE=01"
        headers = {
            "Referer": "https://e-hentai.org/bounce_login.php?b=d&bt=1-1",
        }
        data = {
            "CookieDate": "1",
            "b": "d",
            "bt": "1-1",
            "UserName": username,
            "PassWord": password,
            "ipb_login_submit": "Login!",
        }

        self.session.cookies.clear()

        response = self.session.post(url, headers=headers, data=data)
        if b"You are now logged in as:" not in response.content:
            raise exception.AuthenticationError()

        # collect more cookies
        url = self.root + "/favorites.php"
        response = self.session.get(url)
        if response.history:
            self.session.get(url)

        return self.session.cookies

    def _auth_by_cookies(self, cookies: dict | RequestsCookieJar):
        if isinstance(cookies, dict):
            for name, value in cookies.items():
                self.session.cookies.set(name, value, domain=f".{self.domain}.org")
        else:
            try:
                cookies = iter(cookies)
            except TypeError:
                self.session.cookies.set_cookie(cookies)
            else:
                for cookie in cookies:
                    self.session.cookies.set_cookie(cookie)

    def _gallery_page(self, gallery_id: int, gallery_token: str) -> str:
        url = f"{self.root}/g/{gallery_id}/{gallery_token}/"
        response = self.session.get(url)
        page = response.text
        logger.trace(f"GET {url}\n{page}")

        if response.status_code == 404 and "Gallery Not Available" in page:
            reason = text.extract(page, "This gallery is unavailable due to", "<br />Sorry about that.")
            raise GalleryNotAvailable(f"This gallery is unavailable due to {reason}")
        if page.startswith(("Key missing", "Gallery not found")):
            raise GalleryNotFound(f"gallery {gallery_id=}/{gallery_token=}")
        if "hentai.org/mpv/" in page:
            logger.warning("Enabled Multi-Page Viewer is not supported")
        return page

    def _image_page(self, image_token: str, gallery_id: int, image_num: int):
        url = "{}/s/{}/{}-{}".format(
            self.root, image_token, gallery_id, image_num
        )
        page = self.session.get(url).text

        if page.startswith(("Invalid page", "Keep trying")):
            raise ValueError("image page")
        return page

    def _metadata_from_page(self, gpage: str):
        extr = text.extract_from(gpage)
        metadata = {
            "thumb": extr("background:transparent url(", ")"),
            "title": text.unescape(extr('<h1 id="gn">', "</h1>")),
            "title_jpn": text.unescape(extr('<h1 id="gj">', "</h1>")),
            "_": extr('<div id="gdc"><div class="cs ct', '"'),
            "eh_category": extr(">", "<"),
            "uploader": extr('<div id="gdn">', "</div>"),
            "date": text.parse_datetime(
                extr('>Posted:</td><td class="gdt2">', "</td>"), "%Y-%m-%d %H:%M"
            ),
            "parent": extr('>Parent:</td><td class="gdt2"><a href="', '"'),
            "expunged": "Yes" != extr('>Visible:</td><td class="gdt2">', "<"),
            "language": extr('>Language:</td><td class="gdt2">', " "),
            "filesize": text.parse_bytes(
                extr('>File Size:</td><td class="gdt2">', "<").rstrip("Bbi")
            ),
            "filecount": text.parse_int(extr('>Length:</td><td class="gdt2">', " ")),
            "favorites": extr('id="favcount">', " "),
            "rating": text.parse_float(extr(">Average: ", "<")),
            "torrentcount": extr(">Torrent Download (", ")"),
            "newer": []
        }

        if metadata["uploader"].startswith("<"):
            metadata["uploader"] = text.unescape(text.extr(metadata["uploader"], ">", "<"))

        f = metadata["favorites"][0]
        if f == "N":
            metadata["favorites"] = "0"
        elif f == "O":
            metadata["favorites"] = "1"
        metadata["favorites"] = text.parse_int(metadata["favorites"])

        metadata["lang"] = language_to_code(metadata["language"])
        metadata["tags"] = [
            text.unquote(tag.replace("+", " "))
            for tag in text.extract_iter(gpage, "hentai.org/tag/", '"')
        ]

        # successor galleries
        newer_div = extr("There are newer versions of this gallery available:", "</div>")
        newer_div_extr = text.extract_from(newer_div)
        while newer_url := newer_div_extr('<a href="', '"'):
            newer_datetime = newer_div_extr('added ', '<br />')
            metadata["newer"].append((newer_url, text.parse_datetime(newer_datetime, "%Y-%m-%d %H:%M")))

        return metadata

    def auth(self, credentials: dict[str, str] | None = None):
        """
        使用 用户名/密码 或 cookies 认证
        :param credentials: 如果包含 'username' 键，则使用 用户名+密码认证；否则使用cookies认证
        :return:
        """
        if credentials is None:
            credentials = self.credentials
            if credentials is None:
                raise AuthenticationError()

        if "username" in credentials:
            # 使用 用户名+密码认证
            logger.info(f"You are logining as {credentials['username']} ...")
            cookies = self._auth_by_username(credentials["username"], credentials["password"])
        else:
            logger.info(f"You are logining by cookies ...")
            cookies = credentials

        self._auth_by_cookies(cookies)

    @staticmethod
    def _parse_original_info(info):
        parts = info.lstrip().split(" ")
        size = text.parse_bytes(parts[3] + parts[4][0])

        return {
            # 1 initial point + 1 per 0.1 MB
            "cost": 1 + math.ceil(size / 100000),
            "size": size,
            "width": text.parse_int(parts[0]),
            "height": text.parse_int(parts[2]),
        }

    @staticmethod
    def _parse_image_info(url):
        for part in url.split("/")[4:]:
            try:
                _, size, width, height, _ = part.split("-")
                break
            except ValueError:
                pass
        else:
            size = width = height = 0

        return {
            "cost": 1,
            "size": text.parse_int(size),
            "width": text.parse_int(width),
            "height": text.parse_int(height),
        }

    def _iter_gallery_images_from_page(self, gpage: str, gallery_id: int) -> Iterator[Image]:
        count = text.parse_int(text.extr(gpage, '>Length:</td><td class="gdt2">', " "))

        data = {}
        # Get first image from image webpage
        image_token = text.extr(gpage, "hentai.org/s/", '"')
        if not image_token:
            logger.debug(f"Page content:\n{gpage}")
            raise ValueError("Failed to extract initial image token")
        ipage = self._image_page(image_token, gallery_id, 1)

        pos = ipage.index('<div id="i3"><a onclick="return load_image(') + 26
        extr = text.extract_from(ipage, pos)

        nextkey = extr("'", "'")
        iurl = extr('<img id="img" src="', '"')
        nl = extr(" nl(", ")").strip("\"'")
        orig = extr("hentai.org/fullimg", '"')

        url = self.root + "/fullimg" + text.unescape(orig)
        try:
            data.update(self._parse_original_info(extr("ownload original", "<")))
        except IndexError:
            logger.error(f"Unable to parse image info for {url}. Page content:\n{ipage}", ipage)
            raise ValueError("Unable to parse image info for '%s'", url)

        data["num"] = 1
        data["image_token"] = extr('var startkey="', '";')
        data["_url_1280"] = iurl
        data["_nl"] = nl
        key_show = extr('var showkey="', '";')

        # TODO: check 509
        # self._check_509(iurl)
        logger.debug(f"Parsed No.{data['num']} image data for gallery {gallery_id}: {data}")
        yield Image(token=data["image_token"], gid=gallery_id, num=data["num"], origin_url=url, url=iurl)

        # Get other images from api
        request = {
            "method": "showpage",
            "gid": gallery_id,
            "page": 0,
            "imgkey": nextkey,
            "showkey": key_show,
        }

        for request["page"] in range(2, count + 1):
            page = self.session.post(self.api_url, json=request).json()

            i3 = page["i3"]
            i6 = page["i6"]

            imgkey = nextkey
            nextkey, pos = text.extract(i3, "'", "'")
            imgurl, pos = text.extract(i3, 'id="img" src="', '"', pos)
            nl, pos = text.extract(i3, " nl(", ")", pos)
            nl = (nl or "").strip("\"'")

            try:
                pos = i6.find("hentai.org/fullimg")
                if pos >= 0:
                    origurl, pos = text.rextract(i6, '"', '"', pos)
                    url = text.unescape(origurl)
                    data = self._parse_original_info(
                        text.extract(i6, "ownload original", "<", pos)[0]
                    )
                else:
                    url = imgurl
                    data = self._parse_image_info(url)
            except IndexError:
                logger.debug(f"Page content:\n{page}")
                raise ValueError(
                    "Unable to parse image info for '%s'", url
                )

            data["num"] = request["page"]
            data["image_token"] = imgkey
            data["_url_1280"] = imgurl
            data["_nl"] = nl

            # TODO: check 509
            # self._check_509(imgurl)
            logger.debug(f"Parsed No.{data['num']} image data for gallery {gallery_id}: {data}")
            yield Image(token=data["image_token"], gid=gallery_id, num=data["num"], origin_url=url, url=imgurl)

            request["imgkey"] = nextkey

    def download_image(self, image: Image | str, directory: Path | str, original: bool = True):
        if isinstance(image, Image):
            url = image.origin_url if original else image.url
        else:
            url = image
        logger.debug(f"Download {url}")
        resp = self.session.get(url)
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        name, _, ext = unquote(url.partition("?")[0].rpartition("/")[2]).rpartition(".")
        with (directory / f"{image.num} {image.token} {image.gid} {name}.{ext}").open('wb') as fp:
            fp.write(resp.content)

    def get_gallery(self, gallery_id_or_url: int | str, gallery_token: str | None = None) -> Gallery:
        if isinstance(gallery_id_or_url, str) and gallery_id_or_url.startswith("http"):
            gallery_id, gallery_token = parse_gid_token(gallery_id_or_url)
        elif isinstance(gallery_token, str):
            gallery_id, gallery_token = int(gallery_id_or_url), gallery_token
        else:
            raise ValueError(f"Unrecognized param: {gallery_id_or_url=}, {gallery_token=}")
        logger.debug(f"get_gallery {gallery_id}/{gallery_token} ...")

        gpage = self._gallery_page(gallery_id, gallery_token)
        metadata = self._metadata_from_page(gpage)
        logger.debug(f"\t{metadata=}")
        it = self._iter_gallery_images_from_page(gpage, gallery_id)

        return Gallery.from_dict({"gid": gallery_id, "token": gallery_token, "images_iter": it, **metadata})

    def _fav_page(self, next: int | None = None, prev: int | None = None) -> str:
        params = []
        if next is not None:
            params.append(f"next={next}")
        if prev is not None:
            params.append(f"prev={prev}")

        url = "{}/favorites.php{}".format(
            self.root, (('?' + "&".join(params)) if params else '')
        )
        page = self.session.get(url).text

        if page.startswith(("Invalid page", "Keep trying")):
            raise ValueError("fav page")
        return page

    def _parse_fav(self, page: str) -> tuple[list[str], int | None, int | None]:
        urls = [
            text.extract(block, 'a href="', '"><span')
            for block
            in text.extract_iter(page, 'class="gl4t glname glft"', '</div>')
        ]
        urls = [url[0] for url in urls if url[0] is not None]

        prev_block = text.extract(page, 'id="dprev"', '< Prev')
        prev = int(text.extract(prev_block, '?prev=', '"')) if "href" in prev_block else None
        next_block = text.extract(page, 'id="dnext"', 'Next >')
        next = int(text.extract(next_block, '?next=', '"')) if "href" in next_block else None
        return urls, prev, next

    def get_fav(self) -> list[tuple[int, str]]:
        fav_galleries = []
        next = None
        while True:
            page = self._fav_page(next=next)
            urls, _, next = self._parse_fav(page)
            fav_galleries.extend(urls)
            if next is None:
                break
        fav_galleries = [url.split('/') for url in fav_galleries]
        return [(int(p[-3]), p[-2]) for p in fav_galleries]


AGENT: DataSource | None = None
ROOT: str | None = None


# confctl配置
def refresh_ds():
    raise ValueError("需要配置confctl")


try:
    from confctl import config


    def _refresh_ds():
        global AGENT, ROOT
        AGENT = DataSource(**config.get("eh_api"))
        AGENT.auth()
        ROOT = AGENT.root


    refresh_ds = _refresh_ds
    refresh_ds()
except (ImportError, KeyError, TypeError):
    pass

# litter配置
_lp = lambda *_args, **_kwargs: None
try:
    import litter
    from confctl import config

    litter.connect(config.get("redis/host"), config.get("redis/port"))
    _lp = litter.publish
except (ImportError, KeyError, TypeError):
    pass


def get_gallery(gallery_id_or_url: int | str, gallery_token: str | None = None, *,
                agent: DataSource | None = None) -> Gallery:
    try:
        result = (agent or AGENT).get_gallery(gallery_id_or_url, gallery_token)
    except Exception as exc:
        _lp("eh_api.get_gallery.error",
            {"gallery_id_or_url": gallery_id_or_url, "gallery_token": gallery_token, "error": exc})
        raise exc
    else:
        _lp("eh_api.get_gallery.success",
            {"gallery_id_or_url": gallery_id_or_url, "gallery_token": gallery_token, "result": result})
        return result


def get_fav(*, agent: DataSource | None = None) -> list[tuple[int, str]]:
    try:
        result = (agent or AGENT).get_fav()
    except Exception as exc:
        _lp("eh_api.get_fav.error", {"error": exc})
        raise exc
    else:
        _lp("eh_api.get_fav.success", {"result": result})
        return result


def download_image(image: Image | str, directory: Path | str, original: bool = True, agent: DataSource | None = None):
    try:
        (agent or AGENT).download_image(image, directory, original)
    except Exception as exc:
        _lp("eh_api.download_image.error", {"image": image, "directory": directory, "original": original, "error": exc})
        raise exc
    else:
        _lp("eh_api.download_image.success", {"image": image, "directory": directory, "original": original})


def auth(credentials: dict[str, str] | None = None, *, agent: DataSource | None = None):
    try:
        (agent or AGENT).auth(credentials)
    except Exception as exc:
        _lp("eh_api.auth.error", {"credentials": credentials, "error": exc})
        raise exc
    else:
        _lp("eh_api.auth.success", {"credentials": credentials})
