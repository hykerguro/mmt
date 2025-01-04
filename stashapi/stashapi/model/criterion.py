from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .common import StashObject


class CriterionModifier(Enum):
    # >= AND <=
    BETWEEN = "BETWEEN"
    # =
    EQUALS = "EQUALS"
    EXCLUDES = "EXCLUDES"
    # >
    GREATER_THAN = "GREATER_THAN"
    INCLUDES = "INCLUDES"
    # INCLUDES ALL
    INCLUDES_ALL = "INCLUDES_ALL"
    # IS NULL
    IS_NULL = "IS_NULL"
    # <
    LESS_THAN = "LESS_THAN"
    # MATCHES REGEX
    MATCHES_REGEX = "MATCHES_REGEX"
    # < OR >
    NOT_BETWEEN = "NOT_BETWEEN"
    # !=
    NOT_EQUALS = "NOT_EQUALS"
    # NOT MATCHES REGEX
    NOT_MATCHES_REGEX = "NOT_MATCHES_REGEX"
    # IS NOT NULL
    NOT_NULL = "NOT_NULL"


class ResolutionEnum(Enum):
    # 8K
    EIGHT_K = "EIGHT_K"
    # 5K
    FIVE_K = "FIVE_K"
    # 4K
    FOUR_K = "FOUR_K"
    # 1080p
    FULL_HD = "FULL_HD"
    # 8K+
    HUGE = "HUGE"
    # 240p
    LOW = "LOW"
    # 1440p
    QUAD_HD = "QUAD_HD"
    # 360p
    R360P = "R360P"
    # 7K
    SEVEN_K = "SEVEN_K"
    # 6K
    SIX_K = "SIX_K"
    # 480p
    STANDARD = "STANDARD"
    # 720p
    STANDARD_HD = "STANDARD_HD"
    # 144p
    VERY_LOW = "VERY_LOW"
    # 1920p
    VR_HD = "VR_HD"  # deprecation_reason: Use 4K instead
    # 540p
    WEB_HD = "WEB_HD"


class OrientationEnum(Enum):
    LANDSCAPE = "LANDSCAPE"
    PORTRAIT = "PORTRAIT"
    SQUARE = "SQUARE"


@dataclass
class IntCriterionInput(StashObject):
    modifier: CriterionModifier
    value: int
    value2: Optional[int] = field(default=None)


@dataclass
class StringCriterionInput(StashObject):
    value: str
    modifier: CriterionModifier


@dataclass
class ResolutionCriterionInput(StashObject):
    value: ResolutionEnum
    modifier: CriterionModifier


@dataclass
class HierarchicalMultiCriterionInput(StashObject):
    modifier: CriterionModifier
    value: Optional[list[int]] = field(default_factory=list)
    depth: Optional[int] = None
    excludes: Optional[list[int]] = field(default_factory=list)


@dataclass
class DateCriterionInput(StashObject):
    modifier: CriterionModifier
    value: str
    value2: Optional[str] = field(default=None)


@dataclass
class MultiCriterionInput(StashObject):
    modifier: CriterionModifier
    value: Optional[list[int]] = field(default_factory=list)
    excludes: Optional[list[int]] = field(default_factory=list)


@dataclass
class TimestampCriterionInput(StashObject):
    modifier: CriterionModifier
    value: str
    value2: Optional[str] = field(default=None)


@dataclass
class OrientationCriterionInput(StashObject):
    value: list[OrientationEnum]
