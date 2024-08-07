from typing import Literal
import os
import json
import requests
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
from datetime import datetime
import threading
from tqdm import tqdm

from ._exceptions import *
from ._constants import *
from .output import colorize_status_code
from ._file_walk import *

__all__ = ["HFS"]


class HFS:
	"""
	Represents an instance of the HFS server.

	Attributes:
		domain (str): The domain of the HFS server.
		__cookies (dict): The cookies used for authentication.

	Methods:
		- __init__(domain: str): Initializes an instance of the HFS server.
		- authorize(login: str, password: str) -> requests.Response: Authenticates the user by sending a login request to the server.
		- get_cookies() -> dict: Returns the cookies used for authentication.
		- set_cookies(cookies: dict): Sets the cookies used for authentication.
		- create_folder(folder_name: str, *, root: str = "/", cookies: dict | requests.cookies.RequestsCookieJar = None) -> requests.Response: Creates a new folder on the server with HFS running.
		- delete(path: str, force: bool = False, cookies: dict | requests.cookies.RequestsCookieJar = None) -> requests.Response: Deletes a file or folder on the server with HFS running.
		- upload_file(local_path: str, remote_path: str = "", exists: Literal[UploadMode.OVERWRITE.value, UploadMode.SKIP.value] = UploadMode.SKIP.value, cookies: dict | requests.cookies.RequestsCookieJar = None) -> requests.Response: Uploads a file from the local system to the server with HFS running.
		- list(path: str = "/", cookies: dict | requests.cookies.RequestsCookieJar = None) -> List[HFSPath]: Lists all files and folders in the specified path on the server with HFS running.
		- exists(path: str, cookies: dict | requests.cookies.RequestsCookieJar = None) -> bool: Checks if a file or folder exists in the specified path on the server with HFS running.
		- create_folders(path: str, *, root: str = "/", cookies: dict | requests.cookies.RequestsCookieJar = None) -> None: Creates multiple folders in the specified path on the server with HFS running.
		- upload_folder(local_path: str, remote_path: str = "/", cookies: dict | requests.cookies.RequestsCookieJar = None) -> None: Uploads a folder from the local system to the server with HFS running.
	"""

	def __init__(self, domain):
		self.domain = domain
		self.__cookies = requests.cookies.RequestsCookieJar()

	def __str__(self):
		return f"HFS instance at {self.domain}"

	def authorize(self, login: str, password: str) -> requests.Response:
		"""
	    Authorizes the user by sending a login request to the server.

	    :param login: The username to log in with.
	    :param password: The password to log in with.

	    :returns: The HTTP response from the server.

	    Raises:

	    - AuthorizationFailed: If the HTTP status code is not 200 or 302.
	    """

		url = f"https://{self.domain}/?login={login}:{password}"

		response = requests.get(url)

		if response.status_code not in (200, 302):  # 200 OK, 302 Found
			raise AuthorizationFailed(f"HTTP status code {response.status_code}")

		self.__cookies = response.cookies

		return response

	def get_cookies(self) -> dict:
		"""
		Returns the cookies used for authentication.

		:returns: A dictionary containing the cookies.
	    """
		return self.__cookies.get_dict()

	def set_cookies(self, cookies: dict):
		"""
		Sets the cookies used for authentication.

		:param cookies: The cookies to use for authentication. If not provided, the instance's cookies will be used.

	    :returns: None
	    """
		assert isinstance(cookies, dict)

		self.__cookies = cookies

	def _create_folder_one(self,
	                       folder_name: str,
	                       *,
	                       root: str = "/",
	                       cookies: dict | requests.cookies.RequestsCookieJar = None) -> requests.Response:

		"""
	    Creates a new folder on the server with HFS running.

	    :param folder_name: The name of the new folder.
	    :param root: The path of the parent folder. Default is "/".
	    :param cookies: The cookies to use for authentication. If not provided, the instance's cookies will be used.

	    :returns: The HTTP response from the server.

	    Raises:
	    
	    - AuthorizationFailed: If the HTTP status code is not 200 or 302.
	    - NotExistsError: If the parent folder does not exist.
	    """
		if cookies is None:
			cookies = self.__cookies

		url = f"https://{self.domain}/~/api/create_folder"

		headers = {"X-Hfs-Anti-Csrf": "1"}
		payload = {
			"uri": root,
			"name": folder_name
		}

		response = requests.post(
			url,
			headers=headers,
			cookies=cookies,
			data=json.dumps(payload)
		)

		match response.status_code:
			case 401:  # 401 Unauthorized
				raise AuthorizationFailed("Access denied")
			case 404:  # 404 Not Found
				raise NotExistsError(f"parent \"{root}\" does not exist")
		"""
			case 409:  # 409 Conflict
				raise AlreadyExistsError(f"folder \"{folder_name}\" already exists")
		"""
		return response

	def create_folder(self,
	                  folder_name: str,
	                  *,
	                  cookies: dict | requests.cookies.RequestsCookieJar = None) -> requests.Response:
		"""
		Creates a new folder on the server with HFS running. Supports creation of nested folders.

		:param folder_name: The name of the new folder.
		:param cookies: The cookies to use for authentication. If not provided, the instance's cookies will be used.

		:returns: The HTTP response from the server.

		Raises:

		- AuthorizationFailed: If the HTTP status code is not 200 or 302.
		- NotExistsError: If the parent folder does not exist.
		"""
		components = os.path.normpath(folder_name).split(os.sep)

		for i, name in enumerate(components):
			resp = self._create_folder_one(name, root=os.path.join('/', *components[:i]).replace(os.sep, '/'), cookies=cookies)
			print(colorize_status_code(resp.status_code), resp.text)

	def delete(self,
	           path: str,
	           *,
	           force: bool = False,
	           cookies: dict | requests.cookies.RequestsCookieJar = None) -> requests.Response:

		"""
		Delete a file or folder on the server with HFS running.

		:param path: The path of the file or folder to delete.
		:param force: If True, the function will delete the file or folder without asking for confirmation. Default is False.
		:param cookies: The cookies to use for authentication. If not provided, the instance's cookies will be used.

		:returns: The HTTP response from the server.

		Raises:

		- AuthorizationFailed: If the HTTP status code is not 200 or 302.
		- NotExistsError: If the specified path does not exist.
		"""
		if cookies is None:
			cookies = self.__cookies

		if not force and path == "/":
			input(f"are you sure you want to delete \"{path}\"? (y/[n])")
			if input().lower() not in {"y", "yes"}:
				return None

		url = f"https://{self.domain}/~/api/delete"

		headers = {"X-Hfs-Anti-Csrf": "1"}
		payload = {
			"uri": path,
		}

		response = requests.post(
			url,
			headers=headers,
			cookies=cookies,
			data=json.dumps(payload)
		)

		match response.status_code:
			case 401:  # 401 Unauthorized
				raise AuthorizationFailed("Access denied")
			case 500:  # 500 Internal Server Error
				raise NotExistsError(f"path \"{path}\" does not exist")

		return response

	def rename(self,
	           old_name: str,
	           new_name: str,
	           *,
	           cookies: dict | requests.cookies.RequestsCookieJar = None) -> requests.Response:

		"""
        Renames a file or folder on the server with HFS running.

        :param old_name: The original name of the file or folder.
        :param new_name: The new name for the file or folder.
        :param cookies: The cookies to use for authentication. If not provided, the instance's cookies will be used.

        :returns: The HTTP response from the server.

        Raises:

        - AuthorizationFailed: If the server denies access.
        - NotExistsError: If the specified 'old_name' does not exist on the server.
        - IsADirectoryError: If the specified 'new_name' is a directory.
        """
		if cookies is None:
			cookies = self.__cookies

		url = f"https://{self.domain}/~/api/rename"

		headers = {"X-Hfs-Anti-Csrf": "1"}
		payload = {
			"uri": old_name,
			"dest": new_name
		}

		response = requests.post(
			url,
			headers=headers,
			cookies=cookies,
			data=json.dumps(payload)
		)

		"""
		match response.status_code:
			case 401:  # 401 Unauthorized
				raise AuthorizationFailed("Access denied")
			case 404:  # 404 Not Found
				raise NotExistsError(f"path \"{path}\" does not exist")
			case 500:  # 500 Internal Server Error
				raise IsADirectoryError(f"path \"{new_name}\" is a directory")
		"""

		return response

	def list(self,
	         path: str = "/",
	         *,
	         cookies: dict | requests.cookies.RequestsCookieJar = None) -> list[HFSPath]:

		"""
		Lists all files and folders in the specified path on the server with HFS running.

		:param path: The path of the directory to list files and folders from. Default is "/" (root directory).
		:param cookies: The cookies to use for authentication. If not provided, the instance's cookies will be used.

		:returns: A list of `HFSPath` objects representing the files and folders in the specified path.

		Raises:

		- APIError: If the server returns an error response.
		"""

		if cookies is None:
			cookies = self.__cookies

		url = f"https://{self.domain}/~/api/get_file_list?uri={path}"

		response = requests.get(
			url,
			cookies=cookies,
		)
		if response.status_code != 200:
			raise APIError(f"HTTP status code {response.status_code}")

		response_text: str = response.text.split('\n')[0].removeprefix("data: ")
		json_response: dict = json.loads(response_text)

		# example: {'can_archive': True, 'can_upload': False, 'can_delete': False, 'can_overwrite': False, 'can_comment': False}
		permissions = {key: value for key, value in json_response.items() if key != "list"}
		files = json_response["list"]
		files_obj = []

		for i in range(len(files)):
			if files[i].get('n', None) is not None:
				files_obj.append(HFSPath(
					name=files[i]['n'],
					size=files[i].get('s', 0),
					modified_at=datetime.fromisoformat(files[i]['m']),
					path=path,
					is_directory=files[i]['n'].endswith('/'),
					comment=files[i].get('c', "")
				))

		return files_obj

	def exists(self,
	           path: str,
	           *,
	           cookies: dict | requests.cookies.RequestsCookieJar = None) -> bool:

		"""
		Checks if a file or folder exists in the specified path on the server with HFS running.

		:param path: The path of the directory to check for existence.
		:param cookies: The cookies to use for authentication. If not provided, the instance's cookies will be used.

		:returns: A boolean value indicating whether the specified path exists on the server.

		Raises:

		- APIError: If the server returns an error response.
		"""

		if cookies is None:
			cookies = self.__cookies

		url = f"https://{self.domain}/~/api/get_file_details"

		headers = {"X-Hfs-Anti-Csrf": "1"}
		payload = {
			"uris": [path]
		}

		response = requests.post(
			url,
			headers=headers,
			cookies=cookies,
			data=json.dumps(payload)
		)

		json_response = json.loads(response.text)

		return json_response["details"][0] != False  # noqa, don't reformat, `json_response["details"][0]` may be None, False or non-null object

	def move(self,
	         old_path: str,
	         new_path: str,
	         *,
	         cookies: dict | requests.cookies.RequestsCookieJar = None) -> requests.Response:

		"""
		Moves a file or folder from the specified 'old_path' to the specified 'new_path' on the server with HFS running.

		:param old_path: The path of the file or folder to be moved.
		:param new_path: The path where the file or folder will be moved on the server.
		:param cookies: The cookies to use for authentication. If not provided, the instance's cookies will be used.

		:returns: The HTTP response from the server.

		Raises:

		- AuthorizationFailed: If the server denies access.
		- NotExistsError: If the specified 'old_path' does not exist on the server.
		- IsADirectoryError: If the specified 'new_path' is a directory.
		"""

		if cookies is None:
			cookies = self.__cookies

		url = f"https://{self.domain}/~/api/move_files"

		headers = {"X-Hfs-Anti-Csrf": "1"}
		payload = {
			"uri_from": [old_path],
			"uri_to": new_path
		}

		print(payload)
		print(json.dumps(payload))

		response = requests.post(
			url,
			headers=headers,
			cookies=cookies,
			data=json.dumps(payload)
		)

		"""
		match response.status_code:
			case 401:  # 401 Unauthorized
				raise AuthorizationFailed("Access denied")
			case 404:  # 404 Not Found
				raise NotExistsError(f"path \"{path}\" does not exist")
			case 500:  # 500 Internal Server Error
				raise IsADirectoryError(f"path \"{new_name}\" is a directory")
		"""

		return response

	def _upload_file(self,
	                 local_path: str,
	                 remote_root: str = "",
	                 *,
	                 exists: Literal[UploadMode.OVERWRITE.value, UploadMode.SKIP.value] = UploadMode.SKIP.value,
	                 cookies: dict | requests.cookies.RequestsCookieJar = None) -> requests.Response:

		"""
		Upload a file from the local system to the server with HFS running.

		:param local_path: The path of the file to be uploaded on the local system.
		:param remote_root: The path where the file will be uploaded on the server. Default is "/" (root directory).
		:param exists: The action to be taken if the file already exists on the server. Can be either 'UploadMode.OVERWRITE.value' or 'UploadMode.SKIP.value'. Default is 'UploadMode.SKIP.value'.
		:param cookies: The cookies to use for authentication. If not provided, the instance's cookies will be used.

		:returns: The HTTP response from the server.

		Raises:

		- FileNotFoundError: If the specified file does not exist on the local system.
		- IsADirectoryError: If the specified path is a directory.
		- ValueError: If the 'exists' parameter is not 'UploadMode.OVERWRITE.value' or 'UploadMode.SKIP.value'.
		- AuthorizationFailed: If the server denies access.
		"""

		if cookies is None:
			cookies = self.__cookies

		if not os.path.exists(local_path):
			raise FileNotFoundError(f"file \"{local_path}\" does not exist")

		if not os.path.isfile(local_path):
			raise IsADirectoryError("path \"{path}\" is a directory")

		if exists not in (UploadMode.OVERWRITE.value, UploadMode.SKIP.value):
			raise ValueError("\"exists\" param should be 'UploadMode.OVERWRITE.value' or 'UploadMode.SKIP.value'")

		# url = f"https://{self.domain}/{os.path.join(remote_root, os.path.basename(local_path)).replace(os.sep, '/')}?existing={exists}"

		remote_root = remote_root.removeprefix('/')

		print(f"{str(exists)}")

		url = os.path.join(f"https://{self.domain}", remote_root, os.path.basename(local_path)).replace(os.sep, '/') + f"?existing={str(exists)}"

		file_size = os.path.getsize(local_path)

		file_size_threshold = 1024 * 1024  # 1 MB

		# plz dont take out `response = requests.put...` of conditional operator.
		# `MultipartEncoder` reads file dynamically, so request should be inside `with tqdm` block
		with open(local_path, 'rb') as f:
			if file_size < file_size_threshold:
				response = requests.put(
					url,
					cookies=cookies,
					data=f.read()
				)
			else:
				# thx Glen Thompson (https://stackoverflow.com/a/67726532/16815310)
				with tqdm(
						desc=os.path.basename(local_path),
						total=file_size,
						unit="B",
						unit_scale=True,
						unit_divisor=1024,
				) as bar:
					fields = {"file": ("filename", f)}
					e = MultipartEncoder(fields=fields)
					data = MultipartEncoderMonitor(
						e, lambda monitor: bar.update(monitor.bytes_read - bar.n)
					)

					response = requests.put(
						url,
						cookies=cookies,
						data=data
					)

		match response.status_code:
			case 401:  # 401 Unauthorized
				raise AuthorizationFailed("Access denied")

		return response

	def _upload_folder(self,
	                   local_path: str,
	                   remote_path: str = "/",
	                   *,
	                   exists: Literal[UploadMode.OVERWRITE.value, UploadMode.SKIP.value] = UploadMode.SKIP.value,
	                   cookies: dict | requests.cookies.RequestsCookieJar = None):

		"""
	    Uploads a folder from the local system to the server with HFS running.

	    :param local_path: The path of the folder to be uploaded on the local system.
	    :param remote_path: The path where the folder will be uploaded on the server. Default is "/" (root directory).
	    :param exists: The action to be taken if the folder already exists on the server. Can be either 'UploadMode.OVERWRITE.value' or 'UploadMode.SKIP.value'. Default is 'UploadMode.SKIP.value'.
	    :param cookies: The cookies to use for authentication. If not provided, the instance's cookies will be used.

	    :returns: None. The function prints the HTTP response from the server for each file uploaded.

	    Raises:

	    - FileNotFoundError: If the specified folder does not exist on the local system.
	    - IsADirectoryError: If the specified path is a directory.
	    - ValueError: If the 'exists' parameter is not 'UploadMode.OVERWRITE.value' or 'UploadMode.SKIP.value'.
	    - AuthorizationFailed: If the server denies access.
	    """

		if cookies is None:
			cookies = self.__cookies

		if not os.path.exists(local_path):
			raise FileNotFoundError(f"folder \"{local_path}\" does not exist")

		if not os.path.isdir(local_path):
			raise NotADirectoryError("path \"{path}\" is not a directory")

		remote_root = os.path.join(remote_path, os.path.normpath(local_path).split(os.sep)[-1]).replace(os.sep, "/")

		threads: list[threading.Thread] = []
		for local_file in _local_walk_gen(local_path):
			remote_file = os.path.normpath(os.path.join(remote_root, os.path.relpath(local_file, local_path))).replace(os.sep, '/')

			print(remote_file)
			if not self.exists(os.path.dirname(remote_file), cookies=cookies):
				self.create_folder(os.path.dirname(remote_file), cookies)
			resp = self._upload_file(local_file, os.path.dirname(remote_file), exists=exists, cookies=cookies)

			print(colorize_status_code(resp.status_code), resp.text)

	# threads.append(threading.Thread())

	def upload(self,
	           local_path: str,
	           remote_path: str = "",
	           *,
	           exists: Literal[UploadMode.OVERWRITE.value, UploadMode.SKIP.value] = UploadMode.SKIP.value,
	           cookies: dict | requests.cookies.RequestsCookieJar = None):

		"""
		Upload a file or folder from the local system to the server with HFS running.

		:param local_path: The path of the file or folder to be uploaded on the local system.
		:param remote_path: The path where the file or folder will be uploaded on the server. Default is "/" (root directory).
		:param exists: The action to be taken if the file or folder already exists on the server. Can be either 'UploadMode.OVERWRITE.value' or 'UploadMode.SKIP.value'. Default is 'UploadMode.SKIP.value'.
		:param cookies: The cookies to use for authentication. If not provided, the instance's cookies will be used.

		:returns: None. The function prints the HTTP response from the server for each file uploaded.

		Raises:

		- FileNotFoundError: If the specified file or folder does not exist on the local system.
		- IsADirectoryError: If the specified path is a directory.
		- ValueError: If the 'exists' parameter is not 'UploadMode.OVERWRITE.value' or 'UploadMode.SKIP.value'.
		- AuthorizationFailed: If the server denies access.
		"""

		if not os.path.exists(local_path):
			raise FileNotFoundError(f"file \"{local_path}\" does not exist")

		if os.path.isfile(local_path):
			return self._upload_file(local_path, remote_path, exists=exists, cookies=cookies)
		else:
			return self._upload_folder(local_path, remote_path, exists=exists, cookies=cookies)
