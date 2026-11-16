from django.db import migrations


def set_superuser_role(apps, schema_editor):
    """Помечает существующие аккаунты суперпользователей соответствующей ролью."""
    User = apps.get_model("users", "User")
    User.objects.filter(is_superuser=True).update(role="superuser")


def reset_superuser_role(apps, schema_editor):
    """Возвращает роль user суперпользователям при откате миграции."""
    User = apps.get_model("users", "User")
    User.objects.filter(is_superuser=True, role="superuser").update(role="user")


class Migration(migrations.Migration):
    dependencies = [("users", "0003_user_avatar_user_role")]

    operations = [
        migrations.RunPython(set_superuser_role, reset_superuser_role),
    ]
