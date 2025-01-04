from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .common import StashObject, IDPlaceholder
from .criterion import IntCriterionInput, StringCriterionInput, ResolutionCriterionInput, \
    HierarchicalMultiCriterionInput, DateCriterionInput, MultiCriterionInput, TimestampCriterionInput


@dataclass
class GalleryPathsType(StashObject):
    cover: str
    preview: str


@dataclass
class Gallery(StashObject):
    """
    Gallery type
    """

    chapters: list[IDPlaceholder]
    created_at: datetime
    files: list[IDPlaceholder]
    id: int
    image_count: int
    organized: bool
    performers: list[IDPlaceholder]
    scenes: list[IDPlaceholder]
    tags: list[IDPlaceholder]
    updated_at: datetime
    urls: list[str]
    paths: GalleryPathsType
    code: Optional[str] = field(default=None)
    cover: Optional[IDPlaceholder] = field(default=None)
    date: Optional[str] = field(default=None)
    details: Optional[str] = field(default=None)
    folder: Optional[IDPlaceholder] = field(default=None)
    photographer: Optional[str] = field(default=None)
    rating100: Optional[int] = field(default=None)
    studio: Optional[IDPlaceholder] = field(default=None)
    title: Optional[str] = field(default=None)
    # url: Optional[str] = field(default=None)  # deprecation_reason: Use urls


@dataclass
class GalleryFilterType(StashObject):
    AND: Optional["GalleryFilterType"] = field(default=None)
    OR: Optional["GalleryFilterType"] = field(default=None)
    NOT: Optional["GalleryFilterType"] = field(default=None)

    id: Optional[IntCriterionInput] = field(default=None)
    title: Optional[StringCriterionInput] = field(default=None)
    details: Optional[StringCriterionInput] = field(default=None)

    # Filter by file checksum
    checksum: Optional[StringCriterionInput] = field(default=None)
    # Filter by path
    path: Optional[StringCriterionInput] = field(default=None)
    # Filter by zip-file count
    file_count: Optional[IntCriterionInput] = field(default=None)
    # Filter to only include galleries missing this property
    is_missing: Optional[str] = field(default=None)
    # Filter to include/exclude galleries that were created from zip
    is_zip: Optional[bool] = field(default=None)
    # rating expressed as 1-100
    rating100: Optional[IntCriterionInput] = field(default=None)
    # Filter by organized
    organized: Optional[bool] = field(default=None)
    # Filter by average image resolution
    average_resolution: Optional[ResolutionCriterionInput] = field(default=None)
    # Filter to only include galleries that have chapters. `true` or `false`
    has_chapters: Optional[str] = field(default=None)
    # Filter to only include galleries with this studio
    studios: Optional[HierarchicalMultiCriterionInput] = field(default=None)
    # Filter to only include galleries with these tags
    tags: Optional[HierarchicalMultiCriterionInput] = field(default=None)
    # Filter by tag count
    tag_count: Optional[IntCriterionInput] = field(default=None)
    # Filter to only include galleries with performers with these tags
    performer_tags: Optional[HierarchicalMultiCriterionInput] = field(default=None)
    # Filter to only include galleries with these performers
    performers: Optional[MultiCriterionInput] = field(default=None)
    # Filter by performer count
    performer_count: Optional[IntCriterionInput] = field(default=None)
    # Filter galleries that have performers that have been favorited
    performer_favorite: Optional[bool] = field(default=None)
    # Filter galleries by performer age at time of gallery
    performer_age: Optional[IntCriterionInput] = field(default=None)
    # Filter by number of images in this gallery
    image_count: Optional[IntCriterionInput] = field(default=None)
    # Filter by url
    url: Optional[StringCriterionInput] = field(default=None)
    # Filter by date
    date: Optional[DateCriterionInput] = field(default=None)
    # Filter by creation time
    created_at: Optional[TimestampCriterionInput] = field(default=None)
    # Filter by last update time
    updated_at: Optional[TimestampCriterionInput] = field(default=None)
    # Filter by studio code
    code: Optional[StringCriterionInput] = field(default=None)
    # Filter by photographer
    photographer: Optional[StringCriterionInput] = field(default=None)


@dataclass
class FindGalleriesResultType(StashObject):
    count: int
    galleries: list[Gallery]
