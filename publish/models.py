from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class CourseCategory(models.TextChoices):
    """Тот же приём, что AuthorCategory: закрытый список значений поля category."""

    PROGRAMMING = "programming", "Программирование"
    DESIGN = "design", "Дизайн"
    FINANCE = "finance", "Финансы"
    MARKETING = "marketing", "Маркетинг"
    LANGUAGES = "languages", "Языки"
    OTHER = "other", "Другое"


class Course(models.Model):
    """Продаваемый материал. API также отдаёт его как карточку публикации."""

    name = models.CharField("Название", max_length=200)
    category = models.CharField(
        "Категория",
        max_length=32,
        choices=CourseCategory.choices,
        default=CourseCategory.OTHER,
    )
    author = models.ForeignKey(
        "author.Author",
        on_delete=models.CASCADE,
        related_name="publish",
        verbose_name="Автор",
    )
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    published_at = models.DateTimeField("Дата публикации", default=timezone.now)
    excerpt = models.CharField("Краткое описание", max_length=500, blank=True)
    preview = models.TextField("Открытый фрагмент", blank=True)
    access = models.CharField(
        "Тип доступа",
        max_length=8,
        choices=(("free", "Бесплатный"), ("paid", "Платный")),
        default="paid",
    )
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    photo = models.ImageField(
        "Фото публикации", upload_to="courses/photos/", blank=True
    )

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        PENDING = "pending", "На проверке"
        REVISION = "revision", "На доработке"
        REJECTED = "rejected", "Отклонена"
        PUBLISHED = "published", "Опубликована"

    # Текущие публикации сохраняют публичность после миграции; авторский API
    # принудительно переводит новые и изменённые материалы на проверку.
    status = models.CharField(
        "Статус модерации",
        max_length=16,
        choices=Status.choices,
        default=Status.PUBLISHED,
    )
    moderator_comment = models.TextField("Комментарий модератора", blank=True)
    reviewed_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_courses",
        verbose_name="Проверил",
    )
    reviewed_at = models.DateTimeField("Дата проверки", null=True, blank=True)

    class Meta:
        verbose_name = "Курс"
        verbose_name_plural = "Курсы"
        ordering = ["-created_at"]

    def __str__(self):
        """Возвращает название курса для админки и журналов."""
        return self.name

    def clean(self):
        """Проверяет, что цена соответствует бесплатному или платному доступу."""
        super().clean()
        if self.access == "free" and self.price != 0:
            raise ValidationError({"price": "У бесплатного материала цена должна быть 0."})
        if self.access == "paid" and self.price <= 0:
            raise ValidationError({"price": "У платного материала цена должна быть больше 0."})


class Lesson(models.Model):
    """Один кусок содержания курса.

    Длинный текст лежит здесь, в PostgreSQL, а не на карточке курса.
    У курса таких записей сколько угодно: author.publish и course.lessons.
    """

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="lessons",
        verbose_name="Курс",
    )
    title = models.CharField("Заголовок", max_length=200)
    body = models.TextField("Текст урока")
    position = models.PositiveIntegerField("Порядок", default=1)

    class Meta:
        verbose_name = "Урок"
        verbose_name_plural = "Уроки"
        ordering = ["position", "id"]

    def __str__(self):
        """Возвращает заголовок урока."""
        return self.title
