import json
from django.db import transaction
from django.db.models import Avg, Count
from rest_framework import serializers
from rest_framework.utils import html
from django.utils import timezone

from author.serializers import AuthorSerializer
from author.models import Author
from .models import Course, CourseCategory, Lesson, LessonProgress, LessonReview


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
    image = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    is_completed = serializers.SerializerMethodField()
    last_viewed_at = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    my_review = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ["id", "title", "position", "body", "image", "video_url", "is_completed", "last_viewed_at", "average_rating", "review_count", "reviews", "my_review"]

    def get_body(self, obj):
        """Возвращает текст урока только пользователю с доступом."""
        request = self.context.get("request")
        user = request.user if request else None
        return obj.body if can_view_course_body(obj.course, user) else None

    def get_image(self, obj):
        """Отдаёт изображение только пользователю с доступом к курсу."""
        request = self.context.get("request")
        user = request.user if request else None
        return obj.image.url if obj.image and can_view_course_body(obj.course, user) else None

    def get_video_url(self, obj):
        """Отдаёт ссылку на видео только пользователю с доступом к курсу."""
        request = self.context.get("request")
        user = request.user if request else None
        return obj.video_url if can_view_course_body(obj.course, user) else ""

    def get_is_completed(self, obj):
        """Проверяет, отметил ли текущий пользователь урок завершённым."""
        request = self.context.get("request")
        user = request.user if request else None
        return bool(user and user.is_authenticated and LessonProgress.objects.filter(user=user, lesson=obj, completed_at__isnull=False).exists())

    def get_last_viewed_at(self, obj):
        """Возвращает время последнего открытия урока текущим пользователем."""
        request = self.context.get("request")
        user = request.user if request else None
        if not user or not user.is_authenticated:
            return None
        progress = LessonProgress.objects.filter(user=user, lesson=obj).values_list("last_viewed_at", flat=True).first()
        return progress

    def get_average_rating(self, obj):
        """Возвращает среднюю оценку урока с округлением до одного знака."""
        average = obj.reviews.aggregate(value=Avg("rating"))["value"]
        return round(average, 1) if average is not None else None

    def get_review_count(self, obj):
        """Возвращает количество отзывов на урок."""
        return obj.reviews.count()

    def get_reviews(self, obj):
        """Возвращает последние пять отзывов к уроку."""
        return LessonReviewReadSerializer(obj.reviews.select_related("user").all()[:5], many=True).data

    def get_my_review(self, obj):
        """Возвращает отзыв текущего пользователя, если он уже оставлен."""
        request = self.context.get("request")
        user = request.user if request else None
        if not user or not user.is_authenticated:
            return None
        review = LessonReview.objects.filter(user=user, lesson=obj).first()
        return LessonReviewReadSerializer(review).data if review else None


class LessonReviewReadSerializer(serializers.ModelSerializer):
    """Показывает отзыв, оценку и имя пользователя."""

    user_name = serializers.CharField(source="user.name", read_only=True)
    lesson_title = serializers.CharField(source="lesson.title", read_only=True)

    class Meta:
        model = LessonReview
        fields = ["id", "user_name", "lesson_title", "rating", "comment", "created_at"]


class LessonReviewWriteSerializer(serializers.ModelSerializer):
    """Проверяет оценку и текст отзыва перед сохранением."""

    class Meta:
        model = LessonReview
        fields = ["rating", "comment"]

    def validate_comment(self, value):
        """Обрезает пробелы по краям отзыва."""
        return value.strip()


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
    reviews_summary = serializers.SerializerMethodField()

    class Meta(CourseSummarySerializer.Meta):
        fields = CourseSummarySerializer.Meta.fields + ["preview", "body", "lessons", "reviews_summary"]

    def get_reviews_summary(self, obj):
        """Собирает среднюю оценку и три последних отзыва по всем урокам курса."""
        reviews = LessonReview.objects.filter(lesson__course=obj)
        stats = reviews.aggregate(average=Avg("rating"), count=Count("id"))
        latest = reviews.select_related("user", "lesson").order_by("-created_at", "-id")[:3]
        return {
            "average": round(stats["average"], 1) if stats["average"] is not None else None,
            "count": stats["count"],
            "latest": LessonReviewReadSerializer(latest, many=True).data,
        }

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
        fields = ["id", "title", "position", "body", "image", "video_url"]
        read_only_fields = ["id"]


class AuthorLessonsField(serializers.ListField):
    """Принимает список уроков как JSON, включая форму multipart с фото курса."""

    def get_value(self, dictionary):
        """Читает JSON-строку целиком из multipart, не разбивая её на символы/элементы."""
        if html.is_html_input(dictionary) and self.field_name in dictionary:
            return dictionary.get(self.field_name)
        return super().get_value(dictionary)

    def get_attribute(self, instance):
        """Преобразует Django RelatedManager в queryset для ответа API."""
        attribute = super().get_attribute(instance)
        return attribute.all() if hasattr(attribute, "all") else attribute

    def to_internal_value(self, data):
        """Разбирает JSON-строку из multipart и валидирует каждый урок."""
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Список уроков должен быть корректным JSON.")
        return super().to_internal_value(data)


class AuthorCourseSerializer(serializers.ModelSerializer):
    """Принимает содержание курса автора и показывает его статус проверки."""

    author = AuthorSerializer(read_only=True)
    author_id = serializers.PrimaryKeyRelatedField(
        source="author", queryset=Author.objects.all(), write_only=True, required=False
    )
    lessons = AuthorLessonsField(child=AuthorLessonSerializer(), required=False)
    photo = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Course
        fields = [
            "id", "name", "category", "author", "author_id", "excerpt", "preview",
            "access", "price", "photo", "status", "moderator_comment",
            "published_at", "lessons",
        ]
        read_only_fields = ["id", "status", "moderator_comment", "published_at"]

    @transaction.atomic
    def create(self, validated_data):
        """Создаёт публикацию и её уроки одной транзакцией для общей модерации."""
        lessons_data = validated_data.pop("lessons", [])
        course = Course.objects.create(**validated_data)
        request = self.context.get("request")
        for index, lesson_data in enumerate(lessons_data):
            lesson_image = request.FILES.get(f"lesson_image_{index}") if request else None
            if lesson_image:
                lesson_data["image"] = lesson_image
            Lesson.objects.create(course=course, **lesson_data)
        return course

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
        if self.instance is None and not attrs.get("lessons"):
            raise serializers.ValidationError({"lessons": "Добавьте хотя бы один урок перед отправкой публикации."})
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
