from django.db import models


class AuthorCategory(models.TextChoices):
    """Список допустимых категорий. Это не таблица в базе.

    В базу у автора попадает короткая строка, например "programming".
    В формах и админке Django показывает подпись "Программирование".
    """

    PROGRAMMING = "programming", "Программирование"
    DESIGN = "design", "Дизайн"
    FINANCE = "finance", "Финансы"
    MARKETING = "marketing", "Маркетинг"
    BUSINESS = "business", "Бизнес"
    LANGUAGES = "languages", "Языки"
    OTHER = "other", "Другое"


class Author(models.Model):
    """Карточка автора.

    Профиль можно связать с одним или несколькими аккаунтами авторов.
    Курсы читаются так: author.publish.all().
    Отдельной колонки «курсы» у автора нет. Каждый курс сам хранит
    ссылку на автора (Course.author), а related_name="publish"
    открывает эту связь со стороны автора.
    """

    name = models.CharField("Имя автора", max_length=150)
    users = models.ManyToManyField(
        "users.User",
        blank=True,
        related_name="author_profiles",
        verbose_name="Аккаунты авторов",
        help_text="Пользователи с ролью «Автор», которым принадлежит этот профиль.",
    )
    description = models.TextField(
        "Описание",
        help_text="В какой области разбирается и чем полезен ученикам",
    )
    category = models.CharField(
        "Категория",
        max_length=32,
        choices=AuthorCategory.choices,
        default=AuthorCategory.OTHER,
    )
    avatar = models.ImageField(
        "Аватар",
        upload_to="authors/avatars/",
        blank=True,
    )

    class Meta:
        verbose_name = "Автор"
        verbose_name_plural = "Авторы"
        ordering = ["name"]

    def __str__(self):
        return self.name
