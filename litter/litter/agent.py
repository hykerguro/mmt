import threading
import traceback
import uuid
from concurrent.futures import Executor, ThreadPoolExecutor, Future
from datetime import datetime
from typing import Callable, Collection, Any, Iterator

import redis
from loguru import logger

from .model import Message, serialize, LitterRequestTimeoutException, Response

__all__ = [
    "connect",
    "subscribe",
    "publish",
    "listen",
    "listen_bg",
    "get_appname",
    "request",
    "iter_request"
]

_redis_client: redis.client.Redis | None = None
_sub_entity: redis.client.PubSub | None = None
_register_map: dict[str, list[Callable]] = {}
_litter_thread: threading.Thread | None = None
_app_name: str | None = None
_executor: Executor | None = None
_RESPONSE_QUEUE_PREFIX = "LRQ:"  # lt response queue


def get_appname() -> str:
    global _app_name
    if _app_name is None:
        set_appname(f"<unknown_client:{uuid.uuid4().hex}>")
    return _app_name


def set_appname(app_name: str) -> None:
    global _app_name
    _app_name = app_name


def connect(host: str, port: int | str, app_name: str | None = None):
    global _redis_client
    if app_name is not None:
        set_appname(app_name)
        logger.info(f"App Name changed to {get_appname()}")

    port = int(port)
    if _redis_client is None:
        _redis_client = redis.StrictRedis(host=host, port=port, decode_responses=True)
        _redis_client.client()
        logger.info(f"Redis connected with name {get_appname()}: {host=}, {port=}")
    else:
        # logger.warning(f"Redis had already connected: {host=}, {port=}")
        pass


def subscribe(pattern: str | Collection[str], func: Callable[[Message], Message | None] | None = None):
    if func is not None:
        global _register_map
        if isinstance(pattern, str):
            pattern = [pattern]
        for p in pattern:
            if p not in _register_map:
                _register_map[p] = []
            _register_map[p].append(func)
    else:
        def warp(_func):
            subscribe(pattern, _func)
            return _func

        return warp


def publish(channel: str, body, *, headers: dict[str, Any] | None = None):
    if _redis_client is None:
        raise RuntimeError("Redis is not connected, you must connect first by calling 'connect(host, port)'")

    if headers is None:
        headers = {}

    headers["litter-name"] = get_appname()
    headers["litter-datetime"] = datetime.now().isoformat()

    message = {
        "headers": headers,
        "body": body,
    }

    return _redis_client.publish(channel, serialize(message))


def request(channel: str, body, *, headers: dict[str, Any] | None = None, timeout: int = 5) -> Response:
    assert timeout > 0

    request_id = str(uuid.uuid4().hex.replace("-", ""))
    response_queue = f"{_RESPONSE_QUEUE_PREFIX}{channel}:{request_id}"

    if headers is None:
        headers = {}
    headers["litter-request-id"] = request_id
    headers["litter-request-timeout"] = timeout
    headers["litter-response-queue"] = response_queue
    publish(channel, body, headers=headers)

    try:
        _, resp = _redis_client.brpop([response_queue], timeout=timeout)
    except:
        traceback.print_exc()
        publish(f"{channel}:timeout", body, headers=headers)
        raise LitterRequestTimeoutException()

    return Response.from_redis_response(resp)


def iter_request(channel: str, body, *, headers: dict[str, Any] | None = None, timeout: int = 5,
                 n: int | None = None) -> Iterator[Response]:
    assert timeout > 0

    request_id = str(uuid.uuid4().hex.replace("-", ""))
    response_queue = f"{_RESPONSE_QUEUE_PREFIX}{channel}:{request_id}"

    if headers is None:
        headers = {}
    headers["litter-request-id"] = request_id
    headers["litter-request-timeout"] = timeout
    headers["litter-response-queue"] = response_queue
    publish(channel, body, headers=headers)

    if n is None:
        n = float("inf")
    i = 0
    while i < n:
        result = _redis_client.brpop([response_queue], timeout=timeout)
        if result is None:
            break
        yield Response.from_redis_response(result[1])
        i += 1


def _build_response(req_message: Message, body, *, headers: dict[str, str] | None = None) -> Response:
    response_queue = f'{_RESPONSE_QUEUE_PREFIX}{req_message.channel}:{req_message.headers["litter-request-id"]}'
    if headers is None:
        headers = {}
    headers["litter-publish-channel"] = req_message.channel
    headers["litter-request-id"] = req_message.headers["litter-request-id"]
    headers["litter-name"] = get_appname()
    headers["litter-response-queue"] = response_queue
    headers["litter-datetime"] = datetime.now().isoformat()
    resp = serialize({
        "headers": headers,
        "body": body,
    })
    return Response.from_redis_response(resp)


def _do_response(resp: Response, timout):
    _redis_client.lpush(resp.response_queue, resp.serialize())
    _redis_client.expire(resp.response_queue, int(timout))
    publish(f"{resp.headers['litter-publish-channel']}:response", {"headers": resp.headers, "body": resp.body})


def handler_callback(message: Message):
    def _handler(f: Future):
        try:
            ret = f.result()
        except Exception as e:
            logger.error(f"Exception while handling message {message}:")
            traceback.print_exc()
            if "litter-request-id" in message.headers:
                headers = {
                    "litter-exception-type": str(type(e)),
                    "litter-exception-message": str(e)
                }
                resp = _build_response(message, None, headers=headers)
                _do_response(resp, message.headers["litter-request-timeout"])
        else:
            if "litter-request-id" in message.headers:
                # is litter-request, litter-response is required
                if ret is None:
                    resp = _build_response(message, None)
                elif isinstance(ret, Response):
                    resp = _build_response(message, ret.body, headers=ret.headers)
                else:
                    resp = _build_response(message, ret, headers=None)
                _do_response(resp, message.headers["litter-request-timeout"])
            else:
                logger.warning(f"Unhandled response: {ret}")

    return _handler


def listen(host: str | None = None, port: int | str | None = None, app_name: str | None = None,
           *, executor_workers: int = 4):
    global _litter_thread, _sub_entity, _executor

    if host is not None and port is not None:
        connect(host, int(port))

    if _redis_client is None:
        raise RuntimeError("Redis is not connected, you must connect first by calling 'connect(host, port)'")

    if app_name is not None:
        set_appname(app_name)
        logger.info(f"App Name changed to {get_appname()}")

    if _executor is None:
        _executor = ThreadPoolExecutor(executor_workers, thread_name_prefix=get_appname())

    if len(_register_map) == 0:
        logger.warning(f"No channel to be listened.")
        return

    if _sub_entity is None:
        _sub_entity = _redis_client.pubsub()
    _sub_entity.psubscribe(list(_register_map.keys()))
    logger.debug(f"Registered channels: {_register_map.keys()}")

    if _litter_thread is None:
        _litter_thread = threading.current_thread()
    logger.info(f"Thread {_litter_thread.name} listening.")

    for redis_msg in _sub_entity.listen():
        logger.trace(f"Received redis message: {redis_msg}")
        message = Message.from_redis_message(redis_msg)

        if message.type in ('message', 'pmessage'):
            key = {
                "message": message.channel,
                "pmessage": message.pattern
            }[message.type]
            funcs = _register_map.get(key, [])
            for func in funcs:
                _executor.submit(func, message).add_done_callback(handler_callback(message))


def listen_bg(host: str | None = None, port: int | str | None = None, app_name: str | None = None,
              *, executor_workers: int = 4):
    global _litter_thread
    if _litter_thread is not None:
        raise RuntimeError(f"listen thread had been already running")

    _litter_thread = threading.Thread(target=listen, args=(host, port, app_name),
                                      kwargs={"executor_workers": executor_workers})
    _litter_thread.name = "LITTER_AGENT_LISTEN_DAEMON"
    _litter_thread.daemon = True
    _litter_thread.start()
