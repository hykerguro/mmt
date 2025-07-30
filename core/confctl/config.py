from typing import Any, Union

__all__ = [
    "load_config",
    "update_config",
    "SubConf",
    "get",
    "set",
]

_CONFIG_VALUE_GUARD = object()

_root_config: dict[str, Any] = {}


def load_config(path: str, update: bool = False):
    """
    加载配置文件
    :param path: 配置文件路径
    :param update: True: 更新；False：替换
    :return:
    """
    if path.endswith('.yml') or path.endswith('.yaml'):
        import yaml
        with open(path, 'r', encoding="utf8") as f:
            conf = yaml.safe_load(f.read())
    elif path.endswith('.json'):
        import json
        with open(path, 'r', encoding="utf8") as f:
            conf = json.load(f)
    else:
        raise ValueError(f"不支持的配置格式：{path.rsplit('.', maxsplit=1)[-1]}")

    if update:
        global _root_config
        update_config(conf)
    else:
        _root_config = conf


def update_config(config: dict[str, Any]):
    global _root_config

    def update(origin: dict[str, Any], new_conf: dict[str, Any]):
        for k, v in new_conf.items():
            if k in origin and isinstance(origin[k], dict) and isinstance(new_conf[k], dict):
                update(origin[k], new_conf[k])
            else:
                origin[k] = new_conf[k]

    update(_root_config, config)


def _get(key: str, default: Any = _CONFIG_VALUE_GUARD, conf=None):
    global _root_config
    if conf is None:
        conf = _root_config

    *path, k = key.split("/")
    try:
        for p in path:
            conf = conf[p]
        return conf[k]
    except (KeyError, TypeError):
        if default is _CONFIG_VALUE_GUARD:
            raise KeyError(f"no config {key}")
        else:
            return default


def get(key: str, default: Any = _CONFIG_VALUE_GUARD):
    return _get(key, default)


def _set(key: str, value: Any, conf=None) -> None:
    global _root_config
    if conf is None:
        conf = _root_config
    *path, k = key.split("/")
    for p in path:
        try:
            conf = conf[p]
        except KeyError:
            conf[p] = conf = {}
    conf[k] = value


def set(key: str, value: Any) -> None:
    _set(key, value)


class SubConf:
    parent: str
    conf: dict[str, Any]

    def __init__(self, node: Union[str, "SubConf"]):
        self.parent = node if isinstance(node, str) else node.parent
        self.conf = get(self.parent)
        if not isinstance(self.conf, dict):
            raise ValueError(f"{self.parent} 不是合法的配置子集")

    def get(self, key: str, default: Any = _CONFIG_VALUE_GUARD):
        return _get(key, default, self.conf)

    def set(self, key: str, value: Any):
        return _set(key, value, self.conf)

    def __str__(self):
        return f"SubConf({self.parent})"
