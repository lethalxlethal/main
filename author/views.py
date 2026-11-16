from rest_framework import generics
from rest_framework.filters import OrderingFilter, SearchFilter

from config.pagination import OptionalLimitPagination
from .models import Author
from .serializers import AuthorDetailSerializer, AuthorSerializer


def apply_category_filter(queryset, request):
    """Фильтрует авторов по коду категории или её отображаемому названию."""
    value = request.query_params.get("category")
    if not value or value == "all":
        return queryset
    for stored_value, label in Author._meta.get_field("category").choices:
        if value.casefold() in {stored_value.casefold(), label.casefold()}:
            return queryset.filter(category=stored_value)
    return queryset.none()


class AuthorListView(generics.ListAPIView):
    """Возвращает список авторов с поиском, сортировкой и фильтром категории."""

    serializer_class = AuthorSerializer
    pagination_class = OptionalLimitPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name"]
    ordering = ["name"]

    def get_queryset(self):
        """Подготавливает авторов и их курсы для выдачи списка."""
        queryset = Author.objects.prefetch_related("publish")
        return apply_category_filter(queryset, self.request)


class AuthorDetailView(generics.RetrieveAPIView):
    """Возвращает карточку одного автора вместе с его курсами."""

    serializer_class = AuthorDetailSerializer
    queryset = Author.objects.prefetch_related("publish__lessons")
