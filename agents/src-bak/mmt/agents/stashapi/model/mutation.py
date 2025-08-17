from dataclasses import dataclass, field
from typing import Optional

from .common import StashObject


@dataclass
class ScanMetaDataFilterInput(StashObject):
    minModTime: Optional[str] = field(default=None)


@dataclass
class ScanMetadataInput(StashObject):
    paths: list[str] = field(default_factory=list)
    rescan: Optional[bool] = field(default=None)
    scanGenerateCovers: Optional[bool] = field(default=None)
    scanGeneratePreviews: Optional[bool] = field(default=None)
    scanGenerateImagePreviews: Optional[bool] = field(default=None)
    scanGenerateSprites: Optional[bool] = field(default=None)
    scanGeneratePhashes: Optional[bool] = field(default=None)
    scanGenerateThumbnails: Optional[bool] = field(default=None)
    scanGenerateClipPreviews: Optional[bool] = field(default=None)
    filter: Optional[ScanMetaDataFilterInput] = field(default=None)
