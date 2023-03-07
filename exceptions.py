class InvalidResponseCode(Exception):
    """Не верный код ответа."""

    pass


class ConnectionError(Exception):
    """Не верный статус ответа."""

    pass


class NotForSend(Exception):
    """Не для пересылки в телеграм."""

    pass
