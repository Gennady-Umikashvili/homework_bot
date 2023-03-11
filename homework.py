import telegram
import os
import sys
import logging
import requests
import time
from json.decoder import JSONDecodeError
from dotenv import load_dotenv
from http import HTTPStatus
from exceptions import RequestAPIError, JSONError


load_dotenv()

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_PERIOD = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}


HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}

FIRST_STATUS_REQUEST_LAST_SECONDS = 5


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляет сообщение в чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as error:
        logging.error(f"Сообщение не отправлено!: {error}")
    else:
        logging.debug("Сообщение отправлено")


def get_api_answer(timestamp):
    """Отправляет запрос о статусе домашней работы."""
    params_request = {
        "url": ENDPOINT,
        "headers": HEADERS,
        "params": {"from_date": timestamp},
    }
    try:
        homework_status = requests.get(**params_request)
    except requests.exceptions.RequestException as error:
        raise RequestAPIError(f"Ошибка при запросе к основному API: {error}")

    if homework_status.status_code != HTTPStatus.OK:
        raise requests.HTTPError("Статус страницы != 200 ")
    try:
        homework_json = homework_status.json()
    except JSONDecodeError as error:
        raise JSONError(f"Ошибка при декодировании JSON: {error}")
    return homework_json


def check_response(response):
    """Проверяет ответ."""
    logging.debug("Проверка ответа")
    if not isinstance(response, dict):
        raise TypeError("Ошибка в типе ответа API")
    homeworks = response.get("homeworks")
    if homeworks is None:
        raise KeyError("В ответе API отсутствует ключ homework")
    if not isinstance(homeworks, list):
        raise TypeError("Homework не является списком")
    return homeworks


def parse_status(homework):
    """Проверяет статус работы."""
    if "homework_name" not in homework:
        raise KeyError("В ответе отсутсвует ключ")
    homework_name = homework.get("homework_name")
    homework_status = homework.get("status")
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(f"Неизвестный статус работы - {homework_status}")
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}" {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = "Отсутствует переменная"
        logging.critical(message)
        sys.exit(message)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - FIRST_STATUS_REQUEST_LAST_SECONDS
    previous_message = ""

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                send_message(bot, parse_status(homeworks[0]))
            timestamp = response.get("current_date", int(time.time()))
        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            logging.error(message)
            if message != previous_message:
                send_message(bot, message)
                previous_message = message
            else:
                previous_message = ""

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s, %(levelname)s, %(message)s",
        handlers=[
            logging.FileHandler("log.txt"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    main()
