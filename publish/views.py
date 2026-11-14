from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics
from rest_framework.exceptions import NotFound
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from author.models import Author
from config.pagination import OptionalLimitPagination
from .models import Course, Lesson
from .serializers import (
    CourseDetailSerializer,
    CourseSummarySerializer,
    LessonSerializer,
    AuthorCourseSerializer,
    AuthorLessonSerializer,
    ModerationDecisionSerializer,
    course_categories,
)
from .permissions import IsAuthor, IsModerator


def filtered_courses(request):
    """Фильтрует курсы по категории и автору из query-параметров запроса."""
    queryset = Course.objects.select_related("author").prefetch_related("lessons")
    queryset = queryset.filter(status=Course.Status.PUBLISHED)
    category = request.query_params.get("category")
    if category and category != "all":
        match = next(
            (
                value
                for value, label in Course._meta.get_field("category").choices
                if category.casefold() in {value.casefold(), label.casefold()}
            ),
            None,
        )
        queryset = queryset.filter(category=match) if match else queryset.none()
    author_id = request.query_params.get("creator") or request.query_params.get("author")
    if author_id:
        queryset = queryset.filter(author_id=author_id)
    return queryset


class CourseListView(generics.ListAPIView):
    """Возвращает каталог курсов с поиском, фильтрами, сортировкой и limit."""

    serializer_class = CourseSummarySerializer
    pagination_class = OptionalLimitPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "excerpt", "preview", "author__name"]
    ordering_fields = ["published_at", "price", "name"]
    ordering = ["-published_at", "-id"]

    def get_queryset(self):
        """Подготавливает набор курсов для списка или адреса posts."""
        return filtered_courses(self.request)


class CourseDetailView(generics.RetrieveAPIView):
    """Возвращает карточку курса и его уроки с учётом прав доступа."""

    serializer_class = CourseDetailSerializer
    queryset = Course.objects.select_related("author").prefetch_related("lessons")
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Показывает публичные курсы и скрывает все материалы на проверке."""
        return Course.objects.filter(status=Course.Status.PUBLISHED).select_related("author").prefetch_related("lessons")


class CourseLessonsView(generics.ListAPIView):
    """Возвращает упорядоченный список уроков выбранного курса."""

    serializer_class = LessonSerializer
    pagination_class = OptionalLimitPagination

    def get_queryset(self):
        """Находит уроки курса и возвращает 404, если курса нет."""
        course_id = self.kwargs["course_id"]
        if not Course.objects.filter(pk=course_id, status=Course.Status.PUBLISHED).exists():
            raise NotFound("Курс не найден")
        return Lesson.objects.filter(
            course_id=course_id, course__status=Course.Status.PUBLISHED
        ).select_related("course").order_by("position", "id")


class LessonDetailView(generics.RetrieveAPIView):
    """Возвращает один урок, скрывая текст при отсутствии доступа к курсу."""

    serializer_class = LessonSerializer
    queryset = Lesson.objects.filter(course__status=Course.Status.PUBLISHED).select_related("course")


class CategoriesView(APIView):
    """Отдаёт список названий категорий для фильтра каталога."""

    permission_classes = [AllowAny]

    def get(self, request):
        """Возвращает категории курсов простым JSON-массивом."""
        return Response(course_categories())


class AuthorCoursesView(generics.ListAPIView):
    """Возвращает курсы выбранного автора как карточки публикаций."""

    serializer_class = CourseSummarySerializer
    pagination_class = OptionalLimitPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "excerpt", "preview"]
    ordering = ["-published_at", "-id"]

    def get_queryset(self):
        """Находит автора и выбирает его курсы с параметрами фильтрации."""
        author = get_object_or_404(Author, pk=self.kwargs["author_id"])
        return filtered_courses(self.request).filter(author=author)


class MockCourseAccessView(APIView):
    """Выдаёт доступ к курсу для локальной демонстрационной оплаты в DEBUG."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Добавляет курс в доступы текущего пользователя; только для тестирования."""
        from django.conf import settings

        if not settings.DEBUG:
            raise NotFound()
        course_id = request.data.get("course_id")
        course = get_object_or_404(Course, pk=course_id)
        request.user.course.add(course)
        return Response({"detail": "Тестовый доступ к курсу открыт."})


class AuthorCourseListCreateView(generics.ListCreateAPIView):
    """Возвращает курсы автора и создаёт новую публикацию на проверке."""

    serializer_class = AuthorCourseSerializer
    permission_classes = [IsAuthor]

    def get_queryset(self):
        """Ограничивает список курсов профилями автора, связанными с аккаунтом."""
        queryset = Course.objects.select_related("author").prefetch_related("lessons")
        if self.request.user.is_superuser:
            return queryset
        return queryset.filter(author__users=self.request.user)

    def perform_create(self, serializer):
        """Сохраняет курс автора со статусом проверки, недоступным в публичном каталоге."""
        author = serializer.validated_data.get("author")
        if author is None:
            profiles = self.request.user.author_profiles.all()
            if profiles.count() != 1:
                from rest_framework.exceptions import ValidationError

                raise ValidationError({"author_id": "Укажите связанную карточку автора."})
            author = profiles.first()
        if not self.request.user.is_superuser and not author.users.filter(pk=self.request.user.pk).exists():
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Карточка автора не связана с вашим аккаунтом.")
        serializer.save(author=author, status=Course.Status.PENDING, moderator_comment="")


class AuthorCourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Показывает, меняет или удаляет курс, принадлежащий автору."""

    serializer_class = AuthorCourseSerializer
    permission_classes = [IsAuthor]

    def get_queryset(self):
        """Не позволяет автору получать или менять чужие курсы."""
        queryset = Course.objects.select_related("author").prefetch_related("lessons")
        return queryset if self.request.user.is_superuser else queryset.filter(author__users=self.request.user)

    def perform_update(self, serializer):
        """Возвращает изменённую публикацию на проверку и очищает прошлый комментарий."""
        serializer.save(
            status=Course.Status.PENDING,
            moderator_comment="",
            reviewed_by=None,
            reviewed_at=None,
        )


class AuthorLessonListCreateView(generics.ListCreateAPIView):
    """Возвращает и добавляет уроки к собственному курсу автора."""

    serializer_class = AuthorLessonSerializer
    permission_classes = [IsAuthor]

    def get_course(self):
        """Проверяет, что курс принадлежит профилю текущего автора."""
        queryset = Course.objects.all() if self.request.user.is_superuser else Course.objects.filter(author__users=self.request.user)
        return get_object_or_404(queryset, pk=self.kwargs["course_id"])

    def get_queryset(self):
        """Возвращает уроки выбранного собственного курса по порядку."""
        return Lesson.objects.filter(course=self.get_course()).order_by("position", "id")

    def perform_create(self, serializer):
        """Сохраняет урок и отправляет родительский курс на повторную проверку."""
        course = self.get_course()
        serializer.save(course=course)
        course.status = Course.Status.PENDING
        course.moderator_comment = ""
        course.reviewed_by = None
        course.reviewed_at = None
        course.save(update_fields=["status", "moderator_comment", "reviewed_by", "reviewed_at"])


class AuthorLessonDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Позволяет автору менять или удалять урок своего курса."""

    serializer_class = AuthorLessonSerializer
    permission_classes = [IsAuthor]

    def get_queryset(self):
        """Ограничивает уроки курсами, связанными с текущим автором."""
        queryset = Lesson.objects.select_related("course", "course__author")
        if self.request.user.is_superuser:
            return queryset.filter(course_id=self.kwargs["course_id"])
        return queryset.filter(course_id=self.kwargs["course_id"], course__author__users=self.request.user)

    def _send_course_to_review(self, lesson):
        """Возвращает курс на проверку после изменения его урока."""
        course = lesson.course
        course.status = Course.Status.PENDING
        course.moderator_comment = ""
        course.reviewed_by = None
        course.reviewed_at = None
        course.save(update_fields=["status", "moderator_comment", "reviewed_by", "reviewed_at"])

    def perform_update(self, serializer):
        """Сохраняет изменения урока и повторно отправляет курс модератору."""
        lesson = serializer.save()
        self._send_course_to_review(lesson)

    def perform_destroy(self, instance):
        """Удаляет урок и отправляет оставшийся курс на повторную проверку."""
        course = instance.course
        instance.delete()
        course.status = Course.Status.PENDING
        course.moderator_comment = ""
        course.reviewed_by = None
        course.reviewed_at = None
        course.save(update_fields=["status", "moderator_comment", "reviewed_by", "reviewed_at"])


class ModerationQueueView(generics.ListAPIView):
    """Возвращает модератору публикации, ожидающие проверки."""

    serializer_class = AuthorCourseSerializer
    permission_classes = [IsModerator]
    queryset = Course.objects.filter(status=Course.Status.PENDING).select_related("author").prefetch_related("lessons")


class ModerationDecisionView(APIView):
    """Принимает публикацию, отклоняет её или возвращает автору на доработку."""

    permission_classes = [IsModerator]

    def post(self, request, pk):
        """Сохраняет решение модератора и его комментарий к публикации."""
        course = get_object_or_404(Course, pk=pk, status=Course.Status.PENDING)
        serializer = ModerationDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data["decision"]
        course.status = {
            "approve": Course.Status.PUBLISHED,
            "reject": Course.Status.REJECTED,
            "revision": Course.Status.REVISION,
        }[decision]
        course.moderator_comment = serializer.validated_data.get("comment", "").strip()
        course.reviewed_by = request.user
        course.reviewed_at = timezone.now()
        course.save(update_fields=["status", "moderator_comment", "reviewed_by", "reviewed_at"])
        return Response(AuthorCourseSerializer(course, context={"request": request}).data)
