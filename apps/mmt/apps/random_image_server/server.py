import base64
import io
import mimetypes
import os
import random
import re
from pathlib import Path
from queue import Queue
from threading import Thread
from traceback import print_exc

from flask import Flask, jsonify, send_file, request
from loguru import logger

import litter
from confctl import config, util
from mmt.agents.pixiv import api
from . import APP_NAME

util.default_arg_config_loggers()
litter.connect(app_name=APP_NAME)

HTTP_PORT = config.get("random_image_server/http/port", 8080)
IMAGE_FOLDER = Path(config.get("random_image_server/images/folder", "./images"))
app = Flask(__name__)


@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'  # 允许所有来源
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

cache = {}

def populate_bm_cache():
    q: Queue = cache["bm_illusts"]
    if q.full():
        return 
    logger.debug("开始填充缓存")
    try:
        resp = api.user_bookmarks()
    except litter.RequestTimeoutException as e:
        logger.error(f"获取Pixiv收藏失败: {e}")
        return
    
    cnt = resp["total"]
    while not q.full():
        i = random.choice(range(cnt))
        offset, bias = i // 48 * 48, i % 48
        try:
            illust_id = api.user_bookmarks(offset=offset)["works"][bias]["id"]
            pages = api.illust_pages(illust_id)
            if pages is None:
                continue
            p = random.randint(0, len(pages) - 1)
            url = pages[p]["urls"]["original"]
            image_data = api.download(url, None)
        except litter.RequestTimeoutException:
            pass
        else:
            data = {
                "file_name": url.split("/")[-1],
                "source": f"https://www.pixiv.net/artworks/{illust_id}#{p+1}",
                "data": image_data,
                "online": True
            }
            q.put(data)
            logger.debug(f"缓存数据已填充：{data['file_name']}")
        
def random_image_online() -> dict[str, str | bytes]:
    """
    从Pixiv收藏读取图片
    :return: {
        "file_name": url.split("/")[-1],
        "source": f"https://www.pixiv.net/artworks/{illust_id}#{p}",
        "data": image_data,
        "online": True
    }
    """
    if "bm_illusts" not in cache:
        # 初始化缓存
        cache["bm_illusts"] = Queue(config.get("random_image_server/cache/capacity", 10))
        cache["bm_updating"] = False
        logger.debug("初始化数据缓存")
        
    with cache["bm_illusts"].mutex:
        logger.debug("当前缓存：{}".format(", ".join(x["file_name"] for x in list(cache["bm_illusts"].queue))))
    if len(cache["bm_illusts"].queue) < config.get("random_image_server/cache/threshold", 3):
        # 缓存即将用尽
        Thread(target=populate_bm_cache).start()

    result = cache["bm_illusts"].get(timeout=5)
    
    return result
    


def random_image_offline() -> dict[str, str | bytes] | None:
    """
    从本地文件夹读取图片

    :return: {
        "file_name": selected_file.name,
        "source": source,
        "data": open(selected_file, 'rb').read(),
        "online": False
    }
    """
    if (IMAGE_FOLDER / "exclude.txt").exists():
        with open(IMAGE_FOLDER / "exclude.txt", "r") as f:
            excluded_files = [line.strip() for line in f if line.strip()]
    else:
        excluded_files = []

    image_files = [
        f for f in IMAGE_FOLDER.iterdir()
        if f.is_file()
           and f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.gif', '.bmp')
           and f.name not in excluded_files
    ]
    if not image_files:
        return

    selected_file: Path = random.choice(image_files)

    mat = re.match(r"(\d+)_p(\d+)", selected_file.name)
    if mat:
        source = f"https://www.pixiv.net/artworks/{mat.group(1)}#{int(mat.group(2)) + 1}"
    else:
        source = None

    return {
        "file_name": selected_file.name,
        "source": source,
        "data": open(selected_file, 'rb').read(),
        "online": False
    }


@app.route('/random', methods=['GET'])
def get_random():
    ratio = float(request.args.get("r", 0.5))
    if ratio < 0 or ratio > 1:
        return jsonify({"error": "Invalid ratio"}), 400

    result = None
    if random.random() < ratio:
        logger.info("在线获取图片")
        try:
            result = random_image_online()
            result["online"] = True
        except Exception as e:
            print_exc()
            logger.error("在线获取图片失败")

    if result is None:
        logger.info("离线获取图片")
        result = random_image_offline()

    if result is not None:
        if "online" not in result:
            result['online'] = False
        logger.info("图片信息：filename={}, source={}, online={}".format(result["file_name"], result["source"], result["online"]))
        if request.args.get("binary", "false") == "true":
            mime_type, _ = mimetypes.guess_type(result["source"])
            if not mime_type:
                mime_type = 'application/octet-stream'
            return send_file(io.BytesIO(result["data"]), mimetype=mime_type)
        else:
            data = result.pop("data")
            result["base64"] = base64.b64encode(data).decode()
            return jsonify(result), 200
    else:
        return jsonify({"error": "File not found"}), 404

@app.route('/exclude', methods=['POST'])
def exclude():
    req = request.json
    filename = req["filename"]
    online = req["online"]
    if not filename:
        return jsonify({"error": "Filename is required"}), 400

    if online:
        illust_id = re.match(r"(\d+_p(\d+)?)", filename).group(1)
        ret = api.bookmarks_delete(illust_id=illust_id)
        if not ret or ret.get("error"):
            return jsonify({"error": "Illust not found"}), 404
    else:
        with open(os.path.join(IMAGE_FOLDER, "exclude.txt"), "a+") as f:
            f.seek(0)
            rs = [l.strip() for l in f.readlines() if l]
            if filename not in rs:
                f.write(filename + "\n")
    return jsonify({"message": "File excluded successfully"})


@app.route('/upload', methods=['POST'])
def upload():
    req = request.json
    logger.info(req.keys())
    if 'name' not in req or 'data' not in req:
        return jsonify({"error": "Name and data are required"}), 400
    filename = req['name']
    data = req['data']
    with open(os.path.join(IMAGE_FOLDER, filename), "wb") as f:
        f.write(base64.b64decode(data))
    return jsonify({"message": "File uploaded successfully"})


@app.route('/bookmarks_add', methods=['POST'])
def bookmarks_add():
    req = request.json
    res = api.bookmarks_add(req["illust_id"])
    logger.info(res)
    return jsonify(res)


@app.route('/bookmarks_delete', methods=['POST'])
def bookmarks_delete():
    req = request.json
    return jsonify(api.bookmarks_delete(req["illust_id"]))


def run():
    app.run(host='0.0.0.0', port=HTTP_PORT)