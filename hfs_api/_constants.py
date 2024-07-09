import enum

__all__ = ["UploadMode"]


class UploadMode(enum.Enum):
	SKIP = "skip"
	OVERWRITE = "overwrite"
