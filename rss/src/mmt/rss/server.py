import importlib
import pkgutil

from flask import Flask, Response, request

import litter
from confctl import config, util
from mmt.rss.feed import FEEDS

util.default_arg_config_loggers()
litter.connect(app_name="mmt.rss")
SERVER_URL = config.get("rss/server_url")

app = Flask(__name__)


def register_suppliers(name: str = "mmt.rss.feed", package: str | None = None) -> None:
    _package = importlib.import_module(name, package=package)
    for loader, module_name, is_pkg in pkgutil.iter_modules(_package.__path__):
        full_module_name = f"{_package.__name__}.{module_name}"
        importlib.import_module(full_module_name)


@app.route("/resolve/<channel>", methods=["GET"])
def resolve(channel: str):
    url = request.args.get("url")
    assert url
    supplier = FEEDS.get(channel, None)
    if supplier is None:
        return Response(status=404)
    if hasattr(supplier, "resolve") and callable(getattr(supplier, "resolve")):
        return Response(supplier.resolve(url))
    return Response(status=406)


@app.route("/feed/<channel>", methods=["GET"])
def json_feed(channel: str):
    supplier = FEEDS.get(channel, None)
    if supplier is None:
        return f"{channel} not found", 404
    feed = supplier.feed()
    resp_text = feed.json()
    return Response(resp_text, mimetype="application/json")


register_suppliers()
app.run(**config.get("rss/server", {"host": "0.0.0.0", "port": 5000, "debug": True}))
