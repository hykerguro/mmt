import enum
from dataclasses import dataclass, asdict, field
from typing import Sequence, Optional, Self, Any


def get_origin_type(t) -> tuple[type, type | None]:
    if hasattr(t, "__origin__"):
        if t.__origin__ is list:
            return list, t.__args__[0]
        elif repr(t.__origin__).startswith("typing.Union"):
            assert len(t.__args__) == 2
            return t.__args__[0], None
    return t, None


def to_fields(f) -> str:
    if hasattr(f, "__origin__") and issubclass(f.__origin__, Sequence) \
            and hasattr(f, "__args__") and len(f.__args__) == 1:
        f = f.__args__[0]
    if f is IDPlaceholder:
        return "{id}"
    elif issubclass(f, StashObject):
        res = []
        for attr, t in vars(f)["__annotations__"].items():
            if attr.startswith("_"):
                continue
            f_type = t
            if hasattr(t, "__origin__") and repr(t.__origin__).startswith("typing.Union") \
                    and hasattr(t, "__args__") and len(t.__args__) == 2:
                f_type = t.__args__[0]
            res.append(f"{attr}{to_fields(f_type)}")
        return '{' + ','.join(res) + '}'
    else:
        return ""


def to_params(obj) -> str:
    if obj is None:
        return "{}"
    elif isinstance(obj, (StashObject, dict)):
        if isinstance(obj, StashObject):
            obj = asdict(obj)
        return '{' + ",".join(
            f"{k}:{to_params(v)}" for k, v in obj.items() if v is not None
        ) + '}'
    elif isinstance(obj, str):
        return f'"{obj}"'
    elif isinstance(obj, list):
        return '[' + ",".join(map(to_params, obj)) + ']'
    elif isinstance(obj, (int, float)):
        return str(obj)
    elif isinstance(obj, enum.Enum):
        return obj.name
    else:
        raise TypeError(f"Unsupported type {type(obj)}")


def from_dict(cls, data):
    f_type, sub_type = get_origin_type(cls)
    if issubclass(f_type, StashObject):
        args = {}
        for attr, t in vars(cls)["__annotations__"].items():
            if attr.startswith("_"):
                continue
            args[attr] = from_dict(t, data.get(attr))
            # if issubclass(f_type, list):
            #     sub_data_list = data.get(attr, [])
            #     assert isinstance(sub_data_list, list)
            #     assert sub_type is not None
            #     args[attr] = [from_dict(sub_type, sub_data) for sub_data in sub_data_list]
            # if issubclass(f_type, StashObject):
            #     sub_data = data.get(attr, {})
            #     assert isinstance(sub_data, dict)
            #     args[attr] = from_dict(f_type, sub_data)
            # else:
            #     args[attr] = data.get(attr, None)
        return f_type(**args)
    elif issubclass(f_type, list):
        return [from_dict(sub_type, sub_data) for sub_data in data]
    # elif f_type is int:
    #     return int(data or 0)
    # elif f_type is str:
    #     return str(data or 0.)
    else:
        return data


@dataclass
class StashObject:
    def to_params(self) -> str:
        return to_params(self)

    @classmethod
    def to_fields(cls) -> str:
        return to_fields(cls)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return from_dict(cls, data)


class IDPlaceholder(int):
    pass


class SortDirectionEnum(enum.Enum):
    ASC = "ASC"
    DESC = "DESC"


@dataclass
class FindFilterType(StashObject):
    page: Optional[int] = field(default=None)
    # use per_page = -1 to indicate all results. Defaults to 25.
    per_page: Optional[int] = field(default=None)
    q: Optional[str] = field(default=None)
    sort: Optional[str] = field(default=None)
    direction: Optional[SortDirectionEnum] = field(default=None)
