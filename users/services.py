import random
import string
import requests
from urllib.parse import quote
from django.conf import settings
from loguru import logger
from config.settings import DEBUG


def send_sms(phone: str, message: str) -> bool:
    """
    Отправляет SMS сообщение через SMS Aero API используя HTTP-запросы
    Args:
        phone (str): Номер телефона получателя
        message (str): Текст сообщения
    Returns:
        bool: True если сообщение успешно отправлено, False в противном случае
    """
    try:
        logger.info(f"Отправка SMS на номер {phone}")

        # Форматируем номер телефона (убираем +)
        formatted_phone = phone.lstrip("+")
        logger.debug(f"Форматированный номер: {formatted_phone}")

        # Кодируем текст сообщения и подпись
        encoded_text = quote(message)
        encoded_sign = quote(settings.SMSAERO_SIGN)

        if DEBUG:
            api_sms = "testsend?"
        else:
            api_sms = "send?"

        # Формируем URL для запроса
        url = (
            f"https://{settings.SMSAERO_EMAIL}:{settings.SMSAERO_API_KEY}"
            f"@gate.smsaero.ru/v2/sms/{api_sms}"
            f"number={formatted_phone}&"
            f"text={encoded_text}&"
            f"sign={encoded_sign}&"
            f"channel=DIRECT"
        )

        logger.debug("Отправка запроса к SMS Aero API")
        response = requests.get(
            requests.utils.requote_uri(url),
            headers={"Accept": "application/json"},
            timeout=5,
        )

        if response.status_code == 200:
            result = response.json()
            success = result.get("success", False)
            if success:
                logger.info("SMS успешно отправлено")
                return True
            else:
                logger.error(f"Ошибка от SMS Aero API: {result}")
                return False

        logger.error(f"Ошибка HTTP: {response.status_code} - {response.text}")
        return False

    except Exception as e:
        logger.error(f"Неожиданная ошибка при отправке SMS: {str(e)}")
        return False


def generate_invite_code() -> str:
    """
    Генерирует 6-значный инвайт-код
    Returns:
        str: Сгенерированный инвайт-код
    """
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))