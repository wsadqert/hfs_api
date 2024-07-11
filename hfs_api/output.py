import colorama
import http.client

from .HFSPath import HFSPath

colorama.init(autoreset=True)
Fore = colorama.Fore


def colorize_status_code(status_code: int) -> str:
	"""
	This function takes an HTTP status code as input and returns a string with the status code
	colored according to its range. The coloring is as follows:

	- Status codes in the range 200-299 are colored green.
	- Status codes in the range 300-399 are colored cyan.
	- Status codes in the range 400-599 are colored red.
	- For status codes outside these ranges, a ValueError is raised.

	:param status_code: The HTTP status code to be colored.

	:returns: A string containing the colored status code and its corresponding HTTP response message.
	"""

	if status_code in range(200, 300):
		color = Fore.LIGHTGREEN_EX
	elif status_code in range(300, 400):
		color = Fore.CYAN
	elif status_code in range(400, 600):
		color = Fore.LIGHTRED_EX
	else:
		raise ValueError

	return f"{color}{status_code} {http.client.responses[status_code]}"


def ls(hfs_file: list[HFSPath]):
	"""
	This function lists the contents of the HFS paths provided, including directories and files.
	It prints the modified date, size (for files only), and name of each directory or file, along with its comment if any.

	:param hfs_file: A list of HFS paths to be listed.
	:type hfs_file: list

	:returns: None. The function prints the contents of the HFS paths to the console.
	:rtype: None
	"""
	dirs = [path for path in hfs_file if path.is_directory]
	files = [path for path in hfs_file if not path.is_directory]

	for path in dirs:
		modified_at = path.modified_at.strftime("%b %d %H:%M")
		name = path.name
		comment = path.comment

		print(f"{modified_at}          {name}{'  # ' + comment if comment else ''}")

	for path in files:
		modified_at = path.modified_at.strftime("%b %d %H:%M")
		name = path.name
		comment = path.comment
		size = path.size

		print(f"{modified_at} {size:>8} {name}{'  # ' + comment if comment else ''}")
