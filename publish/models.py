from django.db import models


class CourseCategory(models.TextChoices):
    """Тот же приём, что AuthorCategory: закрытый список значений поля category."""

    PROGRAMMING = "programming", "Программирование"
    DESIGN = "design", "Дизайн"
    FINANCE = "finance", "Финансы"
    LANGUAGES = "languages", "Языки"
    OTHER = "other", "Другое"


class Course(models.Model):
    """Карточка курса для каталога: название, цена, автор."""

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
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Курс"
        verbose_name_plural = "Курсы"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


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
        return self.title
