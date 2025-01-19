import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .common import *
from .criterion import StringCriterionInput, IntCriterionInput, DateCriterionInput, ResolutionCriterionInput, \
    OrientationCriterionInput, HierarchicalMultiCriterionInput, MultiCriterionInput, TimestampCriterionInput
from .gallery import GalleryFilterType


@dataclass
class ImageFilterType(StashObject):
    AND: Optional["ImageFilterType"] = field(default=None)
    OR: Optional["ImageFilterType"] = field(default=None)
    NOT: Optional["ImageFilterType"] = field(default=None)
    title: Optional[StringCriterionInput] = field(default=None)
    details: Optional[StringCriterionInput] = field(default=None)
    id: Optional[IntCriterionInput] = field(default=None)
    checksum: Optional[StringCriterionInput] = field(default=None)
    path: Optional[StringCriterionInput] = field(default=None)
    file_count: Optional[IntCriterionInput] = field(default=None)
    rating100: Optional[IntCriterionInput] = field(default=None)
    date: Optional[DateCriterionInput] = field(default=None)
    url: Optional[StringCriterionInput] = field(default=None)
    organized: Optional[bool] = field(default=None)
    o_counter: Optional[IntCriterionInput] = field(default=None)
    resolution: Optional[ResolutionCriterionInput] = field(default=None)
    orientation: Optional[OrientationCriterionInput] = field(default=None)
    is_missing: Optional[str] = field(default=None)
    studios: Optional[HierarchicalMultiCriterionInput] = field(default=None)
    tags: Optional[HierarchicalMultiCriterionInput] = field(default=None)
    tag_count: Optional[IntCriterionInput] = field(default=None)
    performer_tags: Optional[HierarchicalMultiCriterionInput] = field(default=None)
    performers: Optional[MultiCriterionInput] = field(default=None)
    performer_count: Optional[IntCriterionInput] = field(default=None)
    performer_favorite: Optional[bool] = field(default=None)
    performer_age: Optional[IntCriterionInput] = field(default=None)
    galleries: Optional[MultiCriterionInput] = field(default=None)
    created_at: Optional[TimestampCriterionInput] = field(default=None)
    updated_at: Optional[TimestampCriterionInput] = field(default=None)
    code: Optional[StringCriterionInput] = field(default=None)
    photographer: Optional[StringCriterionInput] = field(default=None)
    galleries_filter: Optional[GalleryFilterType] = field(default=None)
    # TODO: performer, studio, tag
    # performers_filter: Optional[PerformerFilterType] = field(default=None)
    # studios_filter: Optional[StudioFilterType] = field(default=None)
    # tags_filter: Optional[TagFilterType] = field(default=None)


@dataclass
class ImagePathsType(StashObject):
    thumbnail: Optional[str] = field(default=None)
    preview: Optional[str] = field(default=None)
    image: Optional[str] = field(default=None)


@dataclass
class Fingerprint(StashObject):
    type: str
    value: str


@dataclass
class ImageFile(StashObject):
    height: int
    width: int
    basename: str
    created_at: datetime
    fingerprints: list[Fingerprint]
    id: int
    mod_time: datetime
    parent_folder_id: int
    path: str
    size: int
    updated_at: datetime
    # fingerprint: Optional[str] = field(default=None)
    zip_file_id: Optional[int] = field(default=None)


@dataclass
class VideoFile(StashObject):
    audio_codec: str
    bit_rate: int
    duration: float
    format: str
    frame_rate: float
    height: int
    video_codec: str
    width: int
    basename: str
    created_at: datetime
    fingerprints: list[Fingerprint]
    id: int
    mod_time: datetime
    parent_folder_id: int
    path: str
    size: int
    updated_at: datetime
    # fingerprint: Optional[str] = field(default=None)
    zip_file_id: Optional[int] = field(default=None)


class VisualFilePlaceholder(Placeholder):
    param_expression = " {... on ImageFile{id, path} ... on VideoFile{id,path}}"


@dataclass
class Image(StashObject):
    created_at: datetime
    # files: list["ImageFile"]  # deprecation_reason: Use visual_files
    galleries: list[IDPlaceholder]
    id: int
    organized: bool
    paths: ImagePathsType
    performers: list[IDAndNamePlaceholder]
    tags: list[IDAndNamePlaceholder]
    updated_at: datetime
    urls: list[str]
    visual_files: list[VideoFile | ImageFile]
    code: Optional[str] = field(default=None)
    date: Optional[str] = field(default=None)
    details: Optional[str] = field(default=None)
    o_counter: Optional[int] = field(default=None)
    photographer: Optional[str] = field(default=None)
    rating100: Optional[int] = field(default=None)
    studio: Optional[IDAndNamePlaceholder] = field(default=None)
    title: Optional[str] = field(default=None)
    # url: Optional[str] = field(default=None)  # deprecation_reason: Use urls


@dataclass
class FindImagesResultType(StashObject):
    count: int
    # Total file size in bytes
    filesize: float
    images: list[Image]
    # Total megapixels of the images
    megapixels: float


class BulkUpdateIdMode(enum.Enum):
    SET = "SET"
    ADD = "ADD"
    REMOVE = "REMOVE"


@dataclass
class BulkUpdateStrings(StashObject):
    mode: BulkUpdateIdMode
    values: list[str] = field(default_factory=list)


@dataclass
class BulkUpdateIds(StashObject):
    mode: BulkUpdateIdMode
    ids: list[int] = field(default_factory=list)


@dataclass
class BulkImageUpdateInput(StashObject):
    clientMutationId: Optional[str] = field(default=None)
    ids: Optional[list[int]] = field(default=None)
    title: Optional[str] = field(default=None)
    code: Optional[str] = field(default=None)
    rating100: Optional[int] = field(default=None)
    organized: Optional[bool] = field(default=None)
    url: Optional[str] = field(default=None)
    urls: Optional[BulkUpdateStrings] = field(default=None)
    date: Optional[str] = field(default=None)
    details: Optional[str] = field(default=None)
    photographer: Optional[str] = field(default=None)
    studio_id: Optional[int] = field(default=None)
    performer_ids: Optional[BulkUpdateIds] = field(default=None)
    tag_ids: Optional[BulkUpdateIds] = field(default=None)
    gallery_ids: Optional[BulkUpdateIds] = field(default=None)
