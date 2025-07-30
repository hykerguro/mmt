import base64
import io
import mimetypes
import os
import random
import re
from pathlib import Path

from flask import Flask, jsonify, send_file, request
from loguru import logger

import litter
from confctl import config, util
from mmt.agents.pixiv import api

util.default_arg_config_loggers()
litter.connect(config.get("redis/host"), config.get("redis/port"), "random_image_server")

HTTP_PORT = config.get("random_image_server/http/port", 8080)
HTTPS_PORT = config.get("random_image_server/https/port", 8443)
IMAGE_FOLDER = Path(config.get("random_image_server/images/folder", "./images"))
app = Flask(__name__)


@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'  # 允许所有来源
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


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
    resp = api.user_bookmarks()
    cnt = resp["total"]
    i = random.randint(0, int(cnt))
    offset = i // 48 * 48
    bias = i % 48
    illust_id = api.user_bookmarks(offset=offset)["works"][bias]["id"]
    pages = api.illust_pages(illust_id)
    p = random.randint(0, len(pages) - 1)
    url = pages[p]["urls"]["original"]
    image_data = api.download(url, None)
    return {
        "file_name": url.split("/")[-1],
        "source": f"https://www.pixiv.net/artworks/{illust_id}#{p}",
        "data": image_data,
        "online": True
    }


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
        except Exception as e:
            logger.error("在线获取图片失败", e)

    if result is None:
        logger.info("离线获取图片")
        result = random_image_offline()

    if result is not None:
        logger.info("图片信息：filename={}, source={}".format(result["file_name"], result["source"]))
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
    filename = request.get_data(as_text=True)
    if not filename:
        return jsonify({"error": "Filename is required"}), 400
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


def run_http():
    app.run(host='0.0.0.0', port=HTTP_PORT)


def run_https():
    app.run(host='0.0.0.0', port=HTTPS_PORT, ssl_context=('devhost+1.pem', 'devhost+1-key.pem'))  # 使用 SSL 证书


if __name__ == '__main__':
    from threading import Thread

    Thread(target=run_http).start()
    if os.getenv("ENABLE_HTTPS") == 'TRUE':
        Thread(target=run_https).start()
