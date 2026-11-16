from django.contrib import admin
from django.urls import reverse

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


# Добавляет отдельный пункт навигации для модераторов в боковое меню Django Admin.
# Это дополнительная ссылка на UserAdmin с фильтром роли, отдельная модель не нужна.
_original_get_app_list = admin.site.get_app_list


def get_app_list_with_moderators(request, app_label=None):
    """Выводит модераторов отдельной группой, сохраняя общий список пользователей."""
    app_list = _original_get_app_list(request, app_label)
    if app_label is not None:
        return app_list

    users_app = next((app for app in app_list if app["app_label"] == "users"), None)
    user_model = next((model for model in users_app["models"] if model["object_name"] == "User"), None) if users_app else None
    if not user_model:
        return app_list

    moderator_url = f'{reverse("admin:users_user_changelist")}?role__exact=moderator'
    moderator_model = {
        **user_model,
        "name": "Модераторы",
        "admin_url": moderator_url,
        "add_url": None,
    }
    app_list.append({
        "name": "Модераторы",
        "app_label": "moderator_accounts",
        "app_url": moderator_url,
        "has_module_perms": True,
        "models": [moderator_model],
    })
    app_list.sort(key=lambda app: app["name"].lower())
    return app_list


admin.site.get_app_list = get_app_list_with_moderators
