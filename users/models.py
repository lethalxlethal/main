from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models
from users.services import generate_invite_code
from phonenumber_field.modelfields import PhoneNumberField
import secrets
from django.core.cache import cache
from loguru import logger


class User(AbstractUser):
    name = None
    phone = PhoneNumberField(region="RU", unique=True, verbose_name="Телефон")
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата первой авторизации"
    )
    course = models.CharField()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    def generate_code(self):
        code = str(secrets.randbelow(10000)).zfill(4)  # Генерация 4-значного кода
        cache.set(
            f"user_{self.phone}_code", code, timeout=300
        )  # Сохраняем код в кэше на 5 минут
        return code

    def check_code(self, code):
        cached_code = cache.get(f"user_{self.phone}_code")
        logger.debug(f"Совпадение кодов: представленный={code}, кэшированный={cached_code}")
        return cached_code == code

    def __str__(self):
        return str(self.phone)

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
