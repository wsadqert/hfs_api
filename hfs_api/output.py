import colorama
import http.client

colorama.init(autoreset=True)
Fore = colorama.Fore


def colorize_status_code(status_code: int):
	if status_code in range(200, 300):
		color = Fore.LIGHTGREEN_EX
	elif status_code in range(300, 400):
		color = Fore.CYAN
	elif status_code in range(400, 600):
		color = Fore.YELLOW
	else:
		raise ValueError

	return f"{color}{status_code} {http.client.responses[status_code]}"
