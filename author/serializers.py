from rest_framework import serializers

from .models import Author


class AuthorSerializer(serializers.ModelSerializer):
    """Формирует публичную карточку автора в формате frontend API."""

    bio = serializers.CharField(source="description", read_only=True)
    category = serializers.SerializerMethodField()
    postsCount = serializers.SerializerMethodField()

    class Meta:
        model = Author
        fields = ["id", "name", "bio", "category", "avatar", "postsCount"]

    def get_category(self, obj):
        """Возвращает читаемое название категории автора."""
        return obj.get_category_display()

    def get_postsCount(self, obj):
        """Считает количество курсов автора для карточки каталога."""
        from publish.models import Course

        return obj.publish.filter(status=Course.Status.PUBLISHED).count()


class AuthorDetailSerializer(AuthorSerializer):
    """Добавляет к карточке автора список его публикаций и курсов."""

    posts = serializers.SerializerMethodField()
    courses = serializers.SerializerMethodField()

    class Meta(AuthorSerializer.Meta):
        fields = AuthorSerializer.Meta.fields + ["posts", "courses"]

    def get_posts(self, obj):
        """Сериализует курсы автора как карточки публикаций фронтенда."""
        from publish.serializers import CourseSummarySerializer

        return CourseSummarySerializer(
            obj.publish.filter(status="published").order_by("-published_at", "-id"), many=True, context=self.context
        ).data

    def get_courses(self, obj):
        """Возвращает список курсов автора в формате карточек курса."""
        return self.get_posts(obj)
