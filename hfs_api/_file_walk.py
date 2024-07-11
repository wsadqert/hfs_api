import os

__all__ = ["_local_walk_gen", "_local_walk"]


def _local_walk_gen(path: str, include_dirs: bool = False):
	"""
	Generator function that yields full paths of all files and directories in the specified path.

	:param path: The root directory to start the walk from.
	:param include_dirs: If True, also yield the directories. Default is False.
	:return: A generator that yields full paths of all files and directories in the specified path.
	"""
	for root, dirs, files in os.walk(path):
		for file in files:
			full_path = os.path.join(root, file)
			yield os.path.normpath(full_path).replace(os.sep, '/')

		if include_dirs:
			for dir in dirs:
				yield os.path.normpath(os.path.join(root, dir)).replace(os.sep, '/')


def _local_walk(path: str, include_dirs: bool = False):
	res = [i for i in _local_walk_gen(path, include_dirs)]

	return res
