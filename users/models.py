import re

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField

NAME_ERROR = (
    "Имя не длиннее 15 символов: только буквы, точка и подчёркивание. "
    "Цифры и спецсимволы нельзя."
)


def validate_user_name(value):
    """Проверяет, что имя содержит только разрешённые символы и не длиннее 15 знаков."""
    if not re.fullmatch(r"[A-Za-zА-Яа-яЁё_.]{1,15}", value):
        raise ValidationError(NAME_ERROR)


class UserManager(BaseUserManager):
    """Создаёт пользователей проекта по номеру телефона."""

    use_in_migrations = True

    def create_user(self, phone, password=None, **extra_fields):
        """Создаёт обычного пользователя и отключает вход по паролю, если он не задан."""
        if not phone:
            raise ValueError("Номер телефона обязателен")
        if not extra_fields.get("name"):
            raise ValueError("Имя пользователя обязательно")
        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        """Создаёт администратора, которому разрешён вход в Django Admin."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", "superuser")
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("Суперпользователь должен иметь is_staff и is_superuser=True")
        return self.create_user(phone, password, **extra_fields)


class User(AbstractUser):
    username = None

    class Role(models.TextChoices):
        USER = "user", "Пользователь"
        AUTHOR = "author", "Автор"
        MODERATOR = "moderator", "Модератор"
        SUPERUSER = "superuser", "Суперпользователь"

    name = models.CharField(
        "Имя пользователя",
        max_length=15,
        validators=[validate_user_name],
    )
    phone = PhoneNumberField(region="RU", unique=True, verbose_name="Телефон")
    role = models.CharField(
        "Роль", max_length=16, choices=Role.choices, default=Role.USER
    )
    avatar = models.ImageField(
        "Аватар", upload_to="users/avatars/", blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата первой авторизации"
    )
    course = models.ManyToManyField(
        "publish.Course",
        blank=True,
        related_name="students",
        verbose_name="Доступные курсы",
    )

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["name"]
    objects = UserManager()

    def __str__(self):
        """Возвращает номер телефона как текстовое представление пользователя."""
        return str(self.phone)

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
