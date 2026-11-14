from rest_framework import serializers
from django.utils import timezone

from author.serializers import AuthorSerializer
from author.models import Author
from .models import Course, CourseCategory, Lesson


def can_view_course_body(course, user):
    """Проверяет, может ли пользователь читать закрытое содержимое курса."""
    if course.access == "free":
        return True
    return bool(
        user
        and user.is_authenticated
        and course.students.filter(pk=user.pk).exists()
    )


class LessonSerializer(serializers.ModelSerializer):
    """Отдаёт поля урока и скрывает его текст, если нет доступа к курсу."""

    body = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ["id", "title", "position", "body"]

    def get_body(self, obj):
        """Возвращает текст урока только пользователю с доступом."""
        request = self.context.get("request")
        user = request.user if request else None
        return obj.body if can_view_course_body(obj.course, user) else None


class CourseSummarySerializer(serializers.ModelSerializer):
    """Преобразует Course в краткую карточку post, которую ожидает frontend."""

    title = serializers.CharField(source="name", read_only=True)
    category = serializers.SerializerMethodField()
    publishedAt = serializers.DateTimeField(source="published_at", read_only=True)
    hasAccess = serializers.SerializerMethodField()
    creator = AuthorSerializer(source="author", read_only=True)
    excerpt = serializers.SerializerMethodField()
    photo = serializers.ImageField(read_only=True)

    class Meta:
        model = Course
        fields = [
            "id", "title", "excerpt", "category", "access", "price",
            "publishedAt", "hasAccess", "creator", "photo",
        ]

    def get_category(self, obj):
        """Возвращает отображаемое название категории курса."""
        return obj.get_category_display()

    def get_hasAccess(self, obj):
        """Возвращает признак наличия доступа к содержимому курса."""
        request = self.context.get("request")
        user = request.user if request else None
        return can_view_course_body(obj, user)

    def get_excerpt(self, obj):
        """Формирует краткое описание, используя превью как запасной вариант."""
        return obj.excerpt or obj.preview[:500]


class CourseDetailSerializer(CourseSummarySerializer):
    """Добавляет к карточке превью, уроки и доступное пользователю содержимое."""

    preview = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta(CourseSummarySerializer.Meta):
        fields = CourseSummarySerializer.Meta.fields + ["preview", "body", "lessons"]

    def get_preview(self, obj):
        """Возвращает превью курса или начало первого урока."""
        if obj.preview:
            return obj.preview
        first_lesson = obj.lessons.first()
        if not first_lesson:
            return ""
        return first_lesson.body[:300]

    def get_body(self, obj):
        """Собирает тексты уроков в массив body или скрывает их без доступа."""
        request = self.context.get("request")
        user = request.user if request else None
        if not can_view_course_body(obj, user):
            return None
        return list(obj.lessons.order_by("position", "id").values_list("body", flat=True))


def course_categories():
    """Возвращает список названий категорий, используемых каталогом фронтенда."""
    return [label for _value, label in CourseCategory.choices]


class AuthorLessonSerializer(serializers.ModelSerializer):
    """Отдаёт автору полный текст его урока для панели управления курсом."""

    class Meta:
        model = Lesson
        fields = ["id", "title", "position", "body"]
        read_only_fields = ["id"]


class AuthorCourseSerializer(serializers.ModelSerializer):
    """Принимает содержание курса автора и показывает его статус проверки."""

    author = AuthorSerializer(read_only=True)
    author_id = serializers.PrimaryKeyRelatedField(
        source="author", queryset=Author.objects.all(), write_only=True, required=False
    )
    lessons = AuthorLessonSerializer(many=True, read_only=True)
    photo = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Course
        fields = [
            "id", "name", "category", "author", "author_id", "excerpt", "preview",
            "access", "price", "photo", "status", "moderator_comment",
            "published_at", "lessons",
        ]
        read_only_fields = ["id", "status", "moderator_comment", "published_at"]

    def validate_author_id(self, author):
        """Запрещает автору привязывать публикацию к чужой карточке автора."""
        request = self.context.get("request")
        if request and not (request.user.is_superuser or author.users.filter(pk=request.user.pk).exists()):
            raise serializers.ValidationError("Эта карточка автора не связана с вашим аккаунтом.")
        return author

    def validate(self, attrs):
        """Проверяет согласованность типа доступа и цены курса."""
        access = attrs.get("access", getattr(self.instance, "access", Course._meta.get_field("access").default))
        price = attrs.get("price", getattr(self.instance, "price", None))
        if price is not None and ((access == "free" and price != 0) or (access == "paid" and price <= 0)):
            raise serializers.ValidationError({"price": "Для бесплатной публикации цена 0, для платной — больше 0."})
        return attrs


class ModerationDecisionSerializer(serializers.Serializer):
    """Проверяет решение модератора и комментарий автору."""

    decision = serializers.ChoiceField(choices=["approve", "reject", "revision"])
    comment = serializers.CharField(required=False, allow_blank=True, max_length=5000)

    def validate(self, attrs):
        """Требует пояснение для отклонения или возврата на доработку."""
        if attrs["decision"] in {"reject", "revision"} and not attrs.get("comment", "").strip():
            raise serializers.ValidationError({"comment": "Добавьте пояснение автору."})
        return attrs
