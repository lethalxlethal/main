from rest_framework.pagination import LimitOffsetPagination


class OptionalLimitPagination(LimitOffsetPagination):
    """Применяет пагинацию только при переданном `?limit=` и ограничивает максимум 100 записями."""

    default_limit = None
    max_limit = 100
