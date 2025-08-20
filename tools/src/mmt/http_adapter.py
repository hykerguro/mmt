import json
from typing import Any

from flask import Flask, request, jsonify
from loguru import logger

import litter
from confctl import config, util

util.default_arg_config_loggers("htt_adapter/logs")

app = Flask(__name__)
LITTER_HEADER_PREFIX = "x-litter-"


def _parse_request(_req) -> tuple[str, dict[str, str], dict[str, Any]]:
    channel = request.args["channel"]
    headers = {k[len(LITTER_HEADER_PREFIX):].lower(): v for k, v in request.headers.items() if
               k.lower().startswith(LITTER_HEADER_PREFIX)}
    data = request.json
    return channel, headers, data


def _logit(channel, headers, data):
    logger.debug("request {}\n\n{}\n\n{}".format(
        channel,
        "\n".join(f"{k}: {v}" for k, v in headers.items()),
        json.dumps(data, indent=2, ensure_ascii=False)
    ))


@app.route('/request', methods=['POST'])
def _request():
    channel, headers, data = _parse_request(request)
    _logit(channel, headers, data)
    try:
        resp = litter.request(channel, data, headers=headers)
    except litter.RequestTimeoutException:
        return jsonify({}), 500
    return jsonify(resp.json()), 200


@app.route("/publish", methods=['POST', 'GET'])
def _publish():
    if request.method == "POST":
        channel, headers, data = _parse_request(request)
    else:
        params = request.args.to_dict()
        channel = params.pop("channel")
        headers = {}
        data = params
    _logit(channel, headers, data)
    litter.publish(channel, data)
    return "", 200


if __name__ == '__main__':
    litter.connect(app_name="http_adapter")
    app.run(**config.get("http_adapter/server", {"host": "0.0.0.0", "port": 8080}))
