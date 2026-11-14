from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Упрощает поиск пользователей и управление их доступом к курсам."""

    list_display = ("name", "phone", "role", "created_at", "is_active", "course_count")
    list_filter = ("role", "is_active", "is_staff", "created_at")
    search_fields = ("name", "phone")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "last_login", "date_joined")
    filter_horizontal = ("course", "groups", "user_permissions")

    fieldsets = (
        ("Профиль", {"fields": ("name", "phone", "role", "avatar", "course")}),
        (
            "Права в админке",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Даты", {"fields": ("created_at", "date_joined", "last_login")}),
    )
    add_fieldsets = (("Новый пользователь", {"fields": ("name", "phone")}),)

    def get_fieldsets(self, request, obj=None):
        """Показывает короткую форму при создании и полную — при редактировании."""
        if obj is None:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def save_model(self, request, obj, form, change):
        """Создаёт пароль, который нельзя использовать для входа по паролю."""
        if obj.is_superuser:
            obj.role = User.Role.SUPERUSER
        elif obj.role == User.Role.SUPERUSER:
            obj.role = User.Role.USER
        if not change and not obj.password:
            obj.set_unusable_password()
        super().save_model(request, obj, form, change)

    @admin.display(description="Курсов")
    def course_count(self, obj):
        """Считает курсы, доступные пользователю."""
        return obj.course.count()
