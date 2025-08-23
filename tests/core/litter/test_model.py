import json
from datetime import datetime
from pathlib import PurePath
from zoneinfo import ZoneInfo

from litter.model import serialize, deserialize


def test_serialize_and_deserialize_datetime():
    dt = datetime(2025, 8, 23, 12, 34, 56, tzinfo=ZoneInfo("Asia/Shanghai"))
    data = {"time": dt}
    s = serialize(data)
    result = deserialize(s)
    assert isinstance(result["time"], datetime)
    assert result["time"].isoformat() == dt.isoformat()


def test_serialize_and_deserialize_bytes():
    b = b"hello world"
    data = {"blob": b}
    s = serialize(data)
    result = deserialize(s)
    assert result["blob"] == b


def test_serialize_purepath():
    p = PurePath("/tmp/test.txt")
    s = serialize({"path": p})
    d = json.loads(s)
    assert d["path"] == str(p)


def test_serialize_exception():
    try:
        raise ValueError("boom")
    except Exception as e:
        s = serialize({"err": e})
        d = json.loads(s)
        assert "ValueError" in d["err"]
        assert "boom" in d["err"]


def test_serialize_fallback_str():
    class Dummy:
        def __str__(self):
            return "dummy"

    s = serialize({"obj": Dummy()})
    d = json.loads(s)
    assert d["obj"] == "dummy"
