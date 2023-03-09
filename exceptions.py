class InvalidResponseCode(Exception):
    """Не верный код ответа."""

    pass


class JSONError(Exception):
    """Ошибка при декодировании сообщения JSON."""

    pass


class RequestAPIError(Exception):
    """Ошибка при запросе к API."""

    pass
