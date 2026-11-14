from rest_framework.permissions import BasePermission


class IsAuthor(BasePermission):
    """Разрешает доступ авторам; superuser сохраняет административный доступ."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_superuser or user.role == "author"))


class IsModerator(BasePermission):
    """Разрешает проверку публикаций модераторам и superuser."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_superuser or user.role == "moderator"))
