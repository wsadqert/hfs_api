import code
from typing import Final
import os
import colorama

from hfs_api import HFS, UploadMode
from hfs_api.output import colorize_status_code

colorama.init(autoreset=True)
Fore = colorama.Fore

domain: Final[str] = os.environ["DOMAIN"]
hfs = HFS(domain)

hfs.authorize("admin", os.environ["ADMIN_PASSWORD"])
print(hfs.get_cookies())


def mainloop():
	while True:
		raw_input = input(f"{Fore.LIGHTBLUE_EX}>> ").split()
		command = raw_input[0]

		match command:
			case "upload":
				local_path = raw_input[1]
				remote_path = raw_input[2]
				exists = UploadMode.SKIP
				if len(raw_input) == 4:
					exists = {
						"skip": UploadMode.SKIP,
						"overwrite": UploadMode.OVERWRITE
					}.get(raw_input[3], UploadMode.SKIP)

				normpath = os.path.normpath(local_path).replace(os.sep, '/')
				hfs.upload(local_path, remote_path, exists=exists)

			case "mkdir":
				name = raw_input[1]
				normpath = os.path.normpath(name).split(os.sep)
				resp = hfs.create_folder(normpath[-1], root='/' + '/'.join(normpath[:-1]))
				print(colorize_status_code(resp.status_code), resp.text)

			case "ls" | "dir":
				comp = raw_input[1]

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
