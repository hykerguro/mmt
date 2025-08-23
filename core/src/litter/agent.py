import atexit
import threading
import traceback
import uuid
from concurrent.futures import Executor, ThreadPoolExecutor, Future
from datetime import datetime
from threading import Lock
from typing import Callable, Collection, Any, Iterator

import redis
from loguru import logger

from litter.model import Message, serialize, RequestTimeoutException, Response, RemoteFunctionRaisedException

__all__ = [
    "connect",
    "disconnect",
    "subscribe",
    "publish",
    "listen",
    "listen_bg",
    "get_appname",
    "request",
    "iter_request"
]

_redis_client: redis.client.Redis | None = None
_lock = Lock()
_sub_entity: redis.client.PubSub | None = None
_register_map: dict[str, list[Callable]] = {}
_litter_thread: threading.Thread | None = None
_app_name: str | None = None
_executor: Executor | None = None
_RESPONSE_QUEUE_PREFIX = "LRQ:"  # lt response queue


def connected() -> bool:
    with _lock:
        return _redis_client is not None


def get_appname() -> str:
    global _app_name
    if _app_name is None:
        set_appname(f"<unknown_client:{uuid.uuid4().hex}>")
    return _app_name


def set_appname(app_name: str) -> None:
    global _app_name
    if app_name != _app_name:
        _app_name = app_name
        logger.info(f"AppName changed to {_app_name}")


def connect(host: str | None = None, port: int | str | None = None, password: str | None = None, db: int = 0,
            *, redis_credentials: dict[str, Any] | None = None, app_name: str | None = None):
    """
    redis_credentials > (host, port, password) > config.get("redis")
    """
    if redis_credentials is None:
        if host is None and port is None and password is None:
            from confctl import config
            redis_credentials = config.get("redis")
            redis_credentials["password"] = redis_credentials.get("password", None)
            redis_credentials["db"] = redis_credentials.get("db", 0)
        else:
            redis_credentials = {
                "host": host,
                "port": port,
                "password": password,
                "db": db,
            }

    global _redis_client
    if app_name is not None:
        set_appname(app_name)

    if _redis_client is None:
        with _lock:
            _redis_client = redis.StrictRedis(decode_responses=True, **redis_credentials)
            _redis_client.client()
        redis_credentials.pop("password", None)
        logger.info(
            f"Redis connected {redis_credentials} with name {get_appname()}")

    atexit.register(disconnect)


def disconnect() -> None:
    global _redis_client, _sub_entity
    if _redis_client is not None:
        _redis_client.close()
        _redis_client = None
        logger.info("Redis disconnected")


def subscribe(pattern: str | Collection[str], func: Callable[[Message], Message | None] | None = None):
    if func is not None:
        global _register_map
        if isinstance(pattern, str):
            pattern = [pattern]
        for p in pattern:
            if p not in _register_map:
                _register_map[p] = []
            _register_map[p].append(func)
        return None
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


def request(channel: str, body, *, headers: dict[str, Any] | None = None, timeout: int = 15) -> Response:
    assert timeout > 0

    request_id = str(uuid.uuid4().hex.replace("-", ""))
    response_queue = f"{_RESPONSE_QUEUE_PREFIX}{channel}:{request_id}"

    if headers is None:
        headers = {}
    headers["litter-request-id"] = request_id
    headers["litter-response-queue"] = response_queue
    headers.setdefault("litter-request-timeout", timeout)
    publish(channel, body, headers=headers)

    result = _redis_client.brpop([response_queue], timeout=headers["litter-request-timeout"])
    if result is None:
        publish(f"{channel}:timeout", body, headers=headers)
        raise RequestTimeoutException(f"Request {channel} timed out. ({timeout}s)")

    resp = Response.from_redis_response(result[1])
    if resp.exception_type is not None:
        raise RemoteFunctionRaisedException(resp)
    return resp


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
            # 函数报错，返回错误response
            logger.error(f"Exception while handling message {message}:")
            traceback.print_exc()
            if "litter-request-id" in message.headers:
                headers = {
                    "litter-exception-type": f"{e.__class__.__module__}.{e.__class__.__name__}",
                    "litter-exception-message": str(e)
                }
                resp = _build_response(message, None, headers=headers)
                _do_response(resp, message.headers["litter-request-timeout"])
        else:
            # 函数正常返回
            if "litter-request-id" in message.headers:
                # is litter-request, litter-response is required
                if ret is None:
                    resp = _build_response(message, None)
                elif isinstance(ret, Response):
                    resp = _build_response(message, ret.body, headers=ret.headers)
                else:
                    resp = _build_response(message, ret, headers=None)
                _do_response(resp, message.headers["litter-request-timeout"])
            elif ret is not None:
                logger.warning(f"Unhandled response: {ret}")

    return _handler


def listen(*, app_name: str | None = None, redis_credentials: dict[str, Any] | None = None, executor_workers: int = 4):
    global _litter_thread, _sub_entity, _executor

    if not connected() or redis_credentials is not None:
        connect(app_name=app_name, redis_credentials=redis_credentials)

    if not connected():
        raise RuntimeError("Redis is not connected, you must connect first by calling 'connect(host, port)'")

    if _executor is None:
        _executor = ThreadPoolExecutor(executor_workers, thread_name_prefix=get_appname())

    if len(_register_map) == 0:
        logger.warning(f"No channel to listen.")

    if _sub_entity is None:
        _sub_entity = _redis_client.pubsub()
    _sub_entity.psubscribe(list(_register_map.keys()))
    logger.debug(f"Registered channels: {_register_map.keys()}")

    if _litter_thread is None:
        _litter_thread = threading.current_thread()
    logger.info(f"Thread {_litter_thread.name} listening.")

    while connected():
        try:
            redis_msg = _sub_entity.get_message(timeout=0.5)
            if redis_msg is None:
                continue
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
        except KeyboardInterrupt:
            disconnect()
            break


def listen_bg(*, app_name: str | None = None, redis_credentials: dict[str, Any] | None = None,
              executor_workers: int = 4):
    global _litter_thread
    if _litter_thread is not None:
        raise RuntimeError(f"listen thread had been already running")

    _litter_thread = threading.Thread(target=listen, kwargs=dict(
        app_name=app_name, redis_credentials=redis_credentials, executor_workers=executor_workers))
    _litter_thread.name = "LITTER_AGENT_LISTEN_DAEMON"
    _litter_thread.daemon = True
    _litter_thread.start()
