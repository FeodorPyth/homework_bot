import logging
import os
import sys
import time

import requests

from dotenv import load_dotenv
import telegram


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


HOMEWORK_KEYS = [
    'id',
    'status',
    'homework_name',
    'reviewer_comment',
    'date_updated',
    'lesson_name',
]


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class WrongAPIResponseError(Exception):
    """Error with requesting API."""

    pass


def check_tokens():
    """The function checks the availability of environment variables."""
    env_variables = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    if all(env_variables):
        return True


def send_message(bot, message):
    """The function sends a message to Telegram chat."""
    logger.info('Начало работы функции отправки сообщения в чат Telegram.')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Сообщение было успешно отправлено: {message}')
    except telegram.error.TelegramError as error:
        logger.error(
            f'Произошла ошибка при отправке сообщения: {error}'
        )


def get_api_answer(timestamp):
    """The function makes a request to the API service endpoint."""
    logger.info('Начало работы функции на получение ответа API.')
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except Exception as error:
        logger.error(f'Эндпоинт недоступен: {ENDPOINT}. {error}')
    if response.status_code != 200:
        error_message = (f'Ошибка соединения.'
                         f'Код соединения {response.status_code}')
        logger.error(error_message)
        raise WrongAPIResponseError(error_message)
    return response.json()


def check_response(response):
    """The function checks the API response for compliance."""
    logger.info('Начало работы функции на проверку ответа API.')
    if not response:
        raise ValueError('Не был получен ответ от API.')
    if type(response) is not dict:
        raise TypeError(
            f'Тип данных {type(response)} не соответствует ожидаемому.'
            f'Ожидался тип данных {dict}.'
        )
    if not (response.get('current_date') and response.get('homeworks')):
        raise KeyError('Ответ API не вернул оба ключа:'
                       '"homeworks" и "current_date".')
    if type(response.get('homeworks')) is not list:
        raise TypeError(f'Тип данных {type(response.get("homeworks"))}'
                        f'не соответствует ожидаемому.'
                        f'Ожидался тип данных {list}.')
    return response.get('homeworks')[0]


def parse_status(homework):
    """The function retrieves information about the status of homework."""
    logger.info('Начало работы функции на проверку статуса работы.')
    if (homework.get('status') not in HOMEWORK_VERDICTS
       or homework.get('status') is None):
        error_message = 'Передан неверный статус!'
        logger.error(error_message)
        raise KeyError(error_message)
    if not homework.get('homework_name'):
        error_message = 'В ответе API нет ключа "homework_name"'
        logger.error(error_message)
        raise KeyError(error_message)
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Basic logic of the bot."""
    if not check_tokens():
        error_message = 'Нет доступа к необходимым переменным окружения!'
        logger.critical(error_message)
        raise ValueError(error_message)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            if message != last_message:
                send_message(bot, message)
                last_message = message
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
