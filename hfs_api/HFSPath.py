from dataclasses import dataclass
from datetime import datetime


@dataclass
class HFSPath:
	"""
	Represents a file or folder on the server with HFS running.

	Attributes:
		name (str): The name of the file or folder.
		size (int): The size of the file in bytes.
		modified_at (datetime): The date and time when the file or folder was last modified.
		path (str): The full path of the file or folder.
		is_directory (bool): Whether the item is a directory.
		comment (str): An optional comment for the file or folder.
	"""

	name: str = ""
	size: int = 0
	modified_at: datetime = ...
	path: str = ""
	is_directory: bool = False
	comment: str = ""

	def __str__(self):
		return f"HFSPath {'folder' if self.is_directory else 'file'} \"{self.path}/{self.name}\", {f'size={self.size}, ' if not self.is_directory else ''}modified_at=<{self.modified_at}> {f'({self.comment})' if self.comment else ''} "
