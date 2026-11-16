from django import forms
from django.contrib import admin
from django.db import models
from django.utils.html import format_html

from .models import Course, Lesson, LessonProgress, LessonReview


class LessonInlineForm(forms.ModelForm):
    """Делает поле текста урока удобным для редактирования внутри курса."""

    class Meta:
        model = Lesson
        fields = "__all__"
        widgets = {
            "body": forms.Textarea(attrs={"rows": 5, "cols": 100}),
        }


class LessonInline(admin.StackedInline):
    """Позволяет создавать и менять уроки прямо на странице курса."""

    model = Lesson
    form = LessonInlineForm
    extra = 1
    show_change_link = True
    ordering = ("position", "id")
    fields = ("position", "title", "body", "image", "video_url")
    verbose_name = "Урок курса"
    verbose_name_plural = "Уроки курса"


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """Организует каталог курсов и редактирование их уроков в админке."""

    list_display = (
        "name",
        "author",
        "category",
        "access",
        "price",
        "status",
        "photo_preview",
        "published_at",
        "lesson_count",
    )
    list_filter = ("status", "category", "access", "author", "published_at")
    search_fields = ("name", "excerpt", "preview", "author__name", "moderator_comment")
    ordering = ("-published_at", "name")
    list_select_related = ("author",)
    list_per_page = 30
    readonly_fields = ("created_at", "photo_preview")
    inlines = (LessonInline,)
    fieldsets = (
        (
            "Карточка публикации",
            {
                "fields": ("name", "author", "category", "excerpt", "preview", "photo", "photo_preview"),
                "description": "Курс отображается в каталоге как публикация. Заполните описание и открытый фрагмент.",
            },
        ),
        ("Доступ и цена", {"fields": ("access", "price")}),
        ("Публикация и проверка", {"fields": ("status", "moderator_comment", "reviewed_by", "reviewed_at", "published_at", "created_at")}),
    )

    def get_queryset(self, request):
        """Подгружает уроки, чтобы не выполнять отдельный запрос для каждого курса."""
        return super().get_queryset(request).prefetch_related("lessons")

    @admin.display(description="Уроков")
    def lesson_count(self, obj):
        """Показывает количество уроков в строке курса."""
        return obj.lessons.count()

    @admin.display(description="Фото")
    def photo_preview(self, obj):
        """Показывает миниатюру загруженного изображения публикации."""
        if not obj or not obj.photo:
            return "Фото не загружено"
        return format_html('<img src="{}" width="120" height="80" style="object-fit:cover;border-radius:8px" />', obj.photo.url)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    """Предоставляет отдельный список уроков для поиска и точечного редактирования."""

    list_display = ("title", "course", "position")
    list_filter = ("course__category", "course__author")
    search_fields = ("title", "body", "course__name", "course__author__name")
    ordering = ("course__name", "position", "id")
    list_select_related = ("course", "course__author")
    list_per_page = 30
    fields = ("course", "position", "title", "body", "image", "video_url")
    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 12, "cols": 100})},
    }


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    """Позволяет просматривать сохранённый прогресс пользователей."""

    list_display = ("user", "lesson", "last_viewed_at", "completed_at")
    list_filter = ("completed_at", "last_viewed_at", "lesson__course")
    search_fields = ("user__name", "user__phone", "lesson__title", "lesson__course__name")
    list_select_related = ("user", "lesson", "lesson__course")


@admin.register(LessonReview)
class LessonReviewAdmin(admin.ModelAdmin):
    """Позволяет модерировать оценки и отзывы к урокам."""

    list_display = ("lesson", "user", "rating", "created_at")
    list_filter = ("rating", "created_at", "lesson__course")
    search_fields = ("user__name", "user__phone", "lesson__title", "comment")
    list_select_related = ("user", "lesson", "lesson__course")
