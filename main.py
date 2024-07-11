import code
import sys
from typing import Final
import os
import shlex
import colorama
import signal
from rich.traceback import install

from hfs_api import HFS, UploadMode
from hfs_api.output import colorize_status_code, ls

install(show_locals=True, width=300)
colorama.init(autoreset=True)
Fore = colorama.Fore

domain: Final[str] = os.environ["DOMAIN"]
hfs = HFS(domain)

hfs.authorize("admin", os.environ["ADMIN_PASSWORD"])
print(hfs.get_cookies())

signal.signal(signal.SIGINT, lambda _s, _f: (print(f"\n{Fore.LIGHTRED_EX}[E] KeyboardInterrupt"), sys.exit(0)))

N = 10


def mainloop():
	while True:
		try:
			raw_input = shlex.split(input(f"{Fore.LIGHTBLUE_EX}>> "))
		except (EOFError, UnicodeError):
			print(f"{Fore.LIGHTRED_EX}[E] EOF Error")
			sys.exit(0)
		print(Fore.RESET)

		if not raw_input:  # empty input
			continue

		raw_input.extend([''] * (N - len(raw_input)))

		command = raw_input[0]

		match command:
			case "upload":
				local_path = raw_input[1]
				remote_path = raw_input[2]

				if '' in (local_path, remote_path):
					print(Fore.LIGHTRED_EX + "[E] Not enough arguments")
					continue

				exists = UploadMode.SKIP.value
				if len(raw_input) == 4:
					match raw_input[3]:
						case "skip":
							exists = UploadMode.SKIP.value
						case "overwrite":
							exists = UploadMode.OVERWRITE.value
						case _:
							print(Fore.LIGHTRED_EX + "[E] Invalid 'exists' value")
							continue
					exists = {
						"skip": UploadMode.SKIP.value,
						"overwrite": UploadMode.OVERWRITE.value
					}.get(raw_input[3], UploadMode.SKIP.value)

				normpath = os.path.normpath(local_path).replace(os.sep, '/')
				hfs.upload(local_path, remote_path, exists=exists)

			case "mkdir":
				name = raw_input[1]
				normpath = os.path.normpath(name).split(os.sep)
				resp = hfs._create_folder_one(normpath[-1], root='/' + '/'.join(normpath[:-1]))
				print(colorize_status_code(resp.status_code), resp.text)

			case "ls" | "dir":
				comp = raw_input[1]

				ls_path = '/'
				if len(raw_input) == 3:
					ls_path = raw_input[2]
				match comp:
					case "local":
						raise NotImplementedError
					case "remote":
						ls(hfs.list(ls_path))

			case "exist" | "exists" | "is":
				name = raw_input[1]
				normpath = '/' + os.path.normpath(name).replace(os.sep, '/')
				resp = hfs.exists(normpath)
				print((Fore.LIGHTGREEN_EX if resp else Fore.LIGHTRED_EX) + str(resp))

			case "delete" | "del" | "remove" | "rem" | "rm":
				name = raw_input[1]
				normpath = '/' + os.path.normpath(name).replace(os.sep, '/')
				resp = hfs.delete(normpath)
				print(colorize_status_code(resp.status_code), resp.text)

			case "move" | "mv":
				old_path = raw_input[1]
				new_path = raw_input[2]
				old_path = os.path.normpath(old_path).replace(os.sep, '/')
				new_path = os.path.normpath(new_path).replace(os.sep, '/')
				resp = hfs.move(old_path, new_path)
				print(colorize_status_code(resp.status_code), resp.text)

			case "copy" | "cp":
				raise NotImplementedError

			case "rename":
				old_name = raw_input[1]
				new_name = raw_input[2]
				normpath = '/' + os.path.normpath(old_name).replace(os.sep, '/')
				resp = hfs.rename(old_name, new_name)
				print(colorize_status_code(resp.status_code), resp.text)

			case "console" | "inter" | "shell":
				code.interact(local=locals(), banner=f"{Fore.YELLOW}Python HFS Shell", exitmsg=f"{Fore.YELLOW}Exiting, goodbye...")

			case "quit" | "exit" | "q":
				return

			case "clear" | "cls":
				print("\33c")

			case _:
				print(Fore.LIGHTRED_EX + "[E] Unknown command")


# hfs.upload_file(r"D:\media\что-то умное\Книги по астре\ОБЩАЯ АСТРОНОМИЯ\Кононович Э.В., Мороз В.И. - Общий курс астрономии, 4-е изд. (2011).pdf", '/')
mainloop()
