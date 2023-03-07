import telegram
import os
import sys
import logging
import requests
import time
import exceptions
from dotenv import load_dotenv
from http import HTTPStatus

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
        logging.debug(f"Сообщение отправлено")


def get_api_answer(timestamp):
    """Отправляет запрос о статусе домашней работы."""
    timestamp = timestamp or int(time.time())
    params_request = {
        "url": ENDPOINT,
        "headers": HEADERS,
        "params": {"from_date": timestamp},
    }
    try:
        homework_status = requests.get(**params_request)
        if homework_status.status_code != HTTPStatus.OK:
            raise exceptions.InvalidResponseCode(
                "Не удалось получить ответ API"
            )
        return homework_status.json()
    except Exception:
        raise exceptions.ConnectionError("Не верный код ответа запроса")


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
    homework_verdicts = homework.get("status")
    if homework_verdicts not in HOMEWORK_VERDICTS:
        raise ValueError(f"Неизвестный статус работы - {homework_verdicts}")
    verdict = HOMEWORK_VERDICTS[homework_verdicts]
    return f'Изменился статус проверки работы "{homework_name}" {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = "Отсутствует переменная"
        logging.critical(message)
        sys.exit(message)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    previous_message = ""

    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get("current_date", int(time.time()))
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
            else:
                message = "Нет новых статусов"
            if message != previous_message:
                send_message(bot, message)
                previous_message = message
            else:
                logging.info(message)

        except NotForSend as error:
            message = f"Сбой в работе программы: {error}"
            logging.error(message)

        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            logging.error(message)
            if message != previous_message:
                send_message(bot, message)
                previous_message = message
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
