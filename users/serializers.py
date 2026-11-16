from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from publish.models import Course
from .models import NAME_ERROR, NAME_TAKEN_ERROR, User, validate_user_name


def name_is_taken(value, *, exclude_user_id=None, exclude_phone=None):
    """Проверяет уникальность имени без учёта регистра для Unicode-имён."""
    users = User.objects.only("id", "name", "phone")
    if exclude_user_id is not None:
        users = users.exclude(pk=exclude_user_id)
    if exclude_phone is not None:
        users = users.exclude(phone=exclude_phone)
    normalized = value.casefold()
    return any(user.name.casefold() == normalized for user in users.iterator())


class ProfileCourseSerializer(serializers.ModelSerializer):
    """Формирует короткую карточку курса для списка курсов в профиле."""

    class Meta:
        model = Course
        fields = ["id", "name", "category", "price"]


class UserSerializer(serializers.ModelSerializer):
    """Преобразует профиль и доступные пользователю курсы в JSON."""

    course = ProfileCourseSerializer(many=True, read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    authorProfiles = serializers.SerializerMethodField()
    isSuperuser = serializers.BooleanField(source="is_superuser", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "phone",
            "createdAt",
            "role",
            "isSuperuser",
            "avatar",
            "authorProfiles",
            "course",
        ]
        read_only_fields = ["id", "phone", "createdAt", "role", "isSuperuser", "authorProfiles", "course"]

    def get_authorProfiles(self, obj):
        """Возвращает связанные профили автора без персональных данных аккаунта."""
        return [{"id": profile.id, "name": profile.name} for profile in obj.author_profiles.all()]

    def to_representation(self, instance):
        """Показывает аватар автора, если личное фото пользователя не задано."""
        data = super().to_representation(instance)
        if not instance.avatar:
            author = instance.author_profiles.exclude(avatar="").first()
            if author and author.avatar:
                avatar_url = author.avatar.url
                request = self.context.get("request")
                data["avatar"] = request.build_absolute_uri(avatar_url) if request else avatar_url
        return data

    def update(self, instance, validated_data):
        """Сохраняет редактируемые данные профиля, включая загруженный аватар."""
        if "name" in validated_data:
            validated_data["name"] = validated_data["name"].strip()
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if validated_data:
            instance.save(update_fields=list(validated_data))
        return instance

    def validate_name(self, value):
        """Очищает и проверяет имя перед записью в профиль."""
        value = value.strip()
        try:
            validate_user_name(value)
        except DjangoValidationError:
            raise serializers.ValidationError(NAME_ERROR)
        if name_is_taken(value, exclude_user_id=self.instance.pk if self.instance else None):
            raise serializers.ValidationError(NAME_TAKEN_ERROR)
        return value


class RegisterSerializer(serializers.Serializer):
    """Проверяет имя и российский номер перед отправкой кода."""

    name = serializers.CharField(max_length=15)
    phone = serializers.RegexField(r"^\+7\d{10}$", max_length=12)

    def validate_name(self, value):
        """Проверяет имя по тем же правилам, что и поле модели пользователя."""
        value = value.strip()
        try:
            validate_user_name(value)
        except DjangoValidationError:
            raise serializers.ValidationError(NAME_ERROR)
        return value

    def validate(self, attrs):
        """Не позволяет запросить вход под именем другого аккаунта."""
        if name_is_taken(attrs["name"], exclude_phone=attrs["phone"]):
            raise serializers.ValidationError({"name": "Это имя уже занято. Выберите другое."})
        return attrs


class VerifyCodeSerializer(serializers.Serializer):
    """Проверяет формат телефона и четырёхзначного кода подтверждения."""

    phone = serializers.RegexField(r"^\+7\d{10}$", max_length=12)
    code = serializers.RegexField(r"^\d{4}$", max_length=4)
