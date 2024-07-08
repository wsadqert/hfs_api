import json
import os
from dataclasses import dataclass
from typing import Literal
import requests
from datetime import datetime
import threading
from code import interact

from ._exceptions import *
from ._constants import *

__all__ = ["HFSPath", "HFS"]


def _local_walk_gen(path: str, include_dirs: bool = False):
	for root, dirs, files in os.walk(path):
		for file in files:
			full_path = os.path.join(root, file)
			yield full_path

		if include_dirs:
			for dir in dirs:
				yield os.path.join(root, dir)


def _local_walk(path: str, include_dirs: bool = False):
	res = [i for i in _local_walk_gen(path, include_dirs)]

	return res


@dataclass
class HFSPath:
	name: str = ""
	size: int = 0
	modified_at: datetime = ...
	path: str = ""
	is_directory: bool = False
	comment: str = ""

	def __str__(self):
		return f"HFSPath {'folder' if self.is_directory else 'file'} \"{self.path}/{self.name}\", {f'size={self.size}, ' if not self.is_directory else ''}modified_at=<{self.modified_at}> {f'({self.comment})' if self.comment else ''} "


class HFS:
	def __init__(self, domain):
		self.domain = domain
		self.__cookies = {}

	def __str__(self):
		return f"HFS instance at {self.domain}"

	def authorize(self, login: str, password: str):
		url = f"https://{self.domain}/?login={login}:{password}"

		response = requests.get(url)

		if response.status_code not in (200, 302):  # 200 OK, 302 Found
			raise AuthorizationFailed(f"HTTP status code {response.status_code}")

		self.__cookies = response.cookies

		return response

	def get_cookies(self):
		return self.__cookies

	def set_cookies(self, cookies: dict):
		assert isinstance(cookies, dict)

		self.__cookies = cookies

	def create_folder(self,
	                  folder_name: str,
	                  *,
	                  root: str = "/",
	                  cookies: dict | requests.cookies.RequestsCookieJar = None):
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

	def delete(self,
	           path: str,
	           force: bool = False,
	           cookies: dict | requests.cookies.RequestsCookieJar = None):
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

	def upload_file(self,
	                local_path: str,
	                remote_path: str = "",
	                exciting: Literal[OVERWRITE, SKIP] = SKIP,
	                cookies: dict | requests.cookies.RequestsCookieJar = None):

		if cookies is None:
			cookies = self.__cookies

		if not os.path.exists(local_path):
			raise FileNotFoundError(f"file \"{local_path}\" does not exist")

		if not os.path.isfile(local_path):
			raise IsADirectoryError("path \"{path}\" is a directory")

		if remote_path == "":
			remote_path = f"/{os.path.basename(local_path)}"

		if exciting not in (OVERWRITE, SKIP):
			raise ValueError("\"exciting\" param should be 'overwrite' or 'skip'")

		remote_folder = os.path.dirname(remote_path)
		remote_file = os.path.basename(remote_path)

		print(remote_folder, remote_file)

		url = f"https://{self.domain}/{remote_folder}/{remote_file}?existing={exciting}"

		with open(local_path, 'rb') as f:
			response = requests.put(
				url,
				cookies=cookies,
				data=f.read()
			)

		match response.status_code:
			case 401:  # 401 Unauthorized
				raise AuthorizationFailed("Access denied")

		return response

	def list(self,
	         path: str = "/",
	         cookies: dict | requests.cookies.RequestsCookieJar = None):

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
				print(files_obj[-1])

	def exists(self,
	           path: str,
	           cookies: dict | requests.cookies.RequestsCookieJar = None):

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

	def create_folders(self,
	                   path: str,
	                   *,
	                   root: str = "/",
	                   cookies: dict | requests.cookies.RequestsCookieJar = None):

		if cookies is None:
			cookies = self.__cookies

		components = os.path.normpath(path).split(os.sep)

		for i in range(len(components)):
			rootpath = os.path.normpath(os.path.join(root, *components[:i])).replace(os.sep, '/')
			resp = self.create_folder(
				components[i],
				root=rootpath,
				cookies=cookies
			)

	def upload_folder(self,
	                  local_path: str,
	                  remote_path: str = "/",
	                  cookies: dict | requests.cookies.RequestsCookieJar = None):

		if cookies is None:
			cookies = self.__cookies

		if not os.path.exists(local_path):
			raise FileNotFoundError(f"folder \"{local_path}\" does not exist")

		if not os.path.isdir(local_path):
			raise NotADirectoryError("path \"{path}\" is not a directory")

		local_folder = os.path.basename(local_path)
		remote_root = os.path.join(remote_path, local_folder)

		threads: list[threading.Thread] = []
		for local_file in _local_walk_gen(local_path):
			remote_file = os.path.join(remote_root, local_file)

			if os.path.isfile(local_file):
				pass

			threads.append(threading.Thread())
