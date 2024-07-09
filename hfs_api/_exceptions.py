class APIError(Exception):
	pass


class AuthorizationFailed(APIError):
	pass


class NotExistsError(APIError):
	pass
