import enum
from dataclasses import dataclass, asdict, field
from typing import Sequence, Optional, Self, Any

__all__ = [
    "to_fields",
    "to_params",
    "from_dict",
    "get_origin_type",
    "StashObject",
    "IDPlaceholder",
    "IDAndNamePlaceholder",
    "SortDirectionEnum",
    "FindFilterType",
    "Placeholder"
]


def get_origin_type(t) -> tuple[type, type | None]:
    if hasattr(t, "__origin__"):
        if t.__origin__ is list:
            return list, t.__args__[0]
        elif repr(t.__origin__).startswith("typing.Union"):
            assert len(t.__args__) == 2
            return t.__args__[0], None
    return t, None


import types


def to_fields(f: type) -> str:
    if f is None:
        return ""

    # wrapped type
    if (isinstance(f, types.UnionType)
            or (hasattr(f, "__origin__") and repr(f.__origin__).startswith(("typing.Union", "typing.Optional")))):
        valid_types = [x for x in f.__args__ if x is not type(None)]
        if len(valid_types) == 1:
            return to_fields(valid_types[0])
        else:
            return ('{__typename, ' + ' '.join(
                "... on {}{}".format(sub_type.__name__, to_fields(sub_type)) for sub_type in valid_types)
                    + '}')

    if hasattr(f, "__origin__") and hasattr(f, "__args__") and issubclass(f.__origin__, Sequence):
        return to_fields(f.__args__[0])

    if issubclass(f, Placeholder):
        return f.param_expression
    elif issubclass(f, StashObject):
        return ('{' + ','.join(
            f"{attr}{to_fields(t)}" for attr, t in vars(f)["__annotations__"].items() if
            not attr.startswith('_')) + '}')
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
    elif isinstance(obj, bool):
        return "true" if obj else "false"
    elif isinstance(obj, (int, float)):
        return str(obj)
    elif isinstance(obj, enum.Enum):
        return obj.name
    else:
        raise TypeError(f"Unsupported type {type(obj)}")


def from_dict(cls, data):
    f_type, sub_type = get_origin_type(cls)

    # A | B
    if (isinstance(f_type, types.UnionType)
            or (hasattr(f_type, "__origin__") and repr(f_type.__origin__).startswith(
                ("typing.Union", "typing.Optional")))):
        name_type_map = {x.__name__: x for x in f_type.__args__ if x is not type(None)}
        return from_dict(name_type_map[data["__typename"]], data)

    if issubclass(f_type, StashObject):
        args = {}
        for attr, t in vars(cls)["__annotations__"].items():
            if attr.startswith("_"):
                continue
            args[attr] = from_dict(t, data.get(attr))
        return f_type(**args)
    elif issubclass(f_type, list):
        return [from_dict(sub_type, sub_data) for sub_data in data]
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


class Placeholder(dict):
    param_expression: str


class IDPlaceholder(Placeholder):
    param_expression = "{id}"


class IDAndNamePlaceholder(Placeholder):
    param_expression = "{id,name}"


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
