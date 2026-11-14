from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth import get_user_model

from .models import Author


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    """Показывает список авторов с поиском, категориями и предпросмотром фото."""

    list_display = ("name", "category", "course_count", "linked_users", "avatar_preview")
    list_filter = ("category",)
    search_fields = ("name", "description")
    ordering = ("name",)
    list_per_page = 30
    readonly_fields = ("avatar_preview",)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Предлагает для связи только аккаунты, которым назначена роль автора."""
        if db_field.name == "users":
            kwargs["queryset"] = get_user_model().objects.filter(role="author")
        return super().formfield_for_manytomany(db_field, request, **kwargs)
    fieldsets = (
        (
            "Карточка автора",
            {
                "fields": ("name", "category", "description", "avatar", "avatar_preview", "users"),
                "description": "Эти данные отображаются в каталоге и на странице автора.",
            },
        ),
    )

    def get_queryset(self, request):
        """Подгружает связанные курсы, чтобы список авторов работал быстрее."""
        return super().get_queryset(request).prefetch_related("publish")

    @admin.display(description="Курсов")
    def course_count(self, obj):
        """Показывает количество курсов, связанных с автором."""
        return obj.publish.count()

    @admin.display(description="Аккаунты")
    def linked_users(self, obj):
        """Показывает число связанных аккаунтов авторов."""
        return obj.users.count()

    @admin.display(description="Аватар")
    def avatar_preview(self, obj):
        """Показывает миниатюру загруженного аватара в админке."""
        if not obj or not obj.avatar:
            return "Фото не загружено"
        return format_html('<img src="{}" width="72" height="72" style="object-fit:cover;border-radius:50%" />', obj.avatar.url)
