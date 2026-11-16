from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth import get_user_model

from .models import Author


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    """Показывает список авторов с поиском, категориями и предпросмотром фото."""

    list_display = ("name", "category", "linked_user_phones", "course_count", "linked_users", "avatar_preview")
    list_filter = ("category",)
    search_fields = ("name", "description", "users__phone")
    ordering = ("name",)
    list_per_page = 30
    readonly_fields = ("avatar_preview",)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Предлагает обычные аккаунты и поясняет, что роль назначится автоматически."""
        if db_field.name == "users":
            user_model = get_user_model()
            kwargs["queryset"] = user_model.objects.filter(
                is_active=True,
                role__in=[user_model.Role.USER, user_model.Role.AUTHOR],
            )
            kwargs["help_text"] = (
                "Выберите телефонный аккаунт автора. После сохранения ему автоматически "
                "назначится роль «Автор»; если убрать последнюю связь, роль станет «Пользователь»."
            )
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def save_related(self, request, form, formsets, change):
        """Синхронизирует роль аккаунта при добавлении или удалении связи с автором."""
        user_model = get_user_model()
        previous_ids = set(form.instance.users.values_list("pk", flat=True))
        super().save_related(request, form, formsets, change)
        current_ids = set(form.instance.users.values_list("pk", flat=True))

        added_ids = current_ids - previous_ids
        removed_ids = previous_ids - current_ids
        for user in user_model.objects.filter(pk__in=added_ids, role=user_model.Role.USER):
            user.role = user_model.Role.AUTHOR
            user.save(update_fields=["role"])

        for user in user_model.objects.filter(pk__in=removed_ids, role=user_model.Role.AUTHOR):
            if not user.author_profiles.exists():
                user.role = user_model.Role.USER
                user.save(update_fields=["role"])

    def delete_model(self, request, obj):
        """После удаления карточки снимает роль автора, если у аккаунта не осталось профилей."""
        user_ids = list(obj.users.values_list("pk", flat=True))
        super().delete_model(request, obj)
        self._restore_user_role(user_ids)

    def delete_queryset(self, request, queryset):
        """Обрабатывает снятие роли при массовом удалении карточек авторов."""
        user_ids = list(
            get_user_model().objects.filter(author_profiles__in=queryset)
            .values_list("pk", flat=True)
            .distinct()
        )
        super().delete_queryset(request, queryset)
        self._restore_user_role(user_ids)

    @staticmethod
    def _restore_user_role(user_ids):
        """Возвращает роль user аккаунтам author без оставшихся карточек автора."""
        user_model = get_user_model()
        for user in user_model.objects.filter(pk__in=user_ids, role=user_model.Role.AUTHOR):
            if not user.author_profiles.exists():
                user.role = user_model.Role.USER
                user.save(update_fields=["role"])

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
        return super().get_queryset(request).prefetch_related("publish", "users")

    @admin.display(description="Курсов")
    def course_count(self, obj):
        """Показывает количество курсов, связанных с автором."""
        return obj.publish.count()

    @admin.display(description="Аккаунты")
    def linked_users(self, obj):
        """Показывает число связанных аккаунтов авторов."""
        return obj.users.count()

    @admin.display(description="Телефоны аккаунтов")
    def linked_user_phones(self, obj):
        """Показывает номера телефонов всех аккаунтов, привязанных к автору."""
        phones = [str(user.phone) for user in obj.users.all()]
        return ", ".join(phones) if phones else "Аккаунт не привязан"

    @admin.display(description="Аватар")
    def avatar_preview(self, obj):
        """Показывает миниатюру загруженного аватара в админке."""
        if not obj or not obj.avatar:
            return "Фото не загружено"
        return format_html('<img src="{}" width="72" height="72" style="object-fit:cover;border-radius:50%" />', obj.avatar.url)
