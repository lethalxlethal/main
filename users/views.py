from users.services import generate_login_code, send_sms
from django.core.cache import cache
from django.contrib.auth.hashers import make_password
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated

from users.models import User
from users.serializers import UserSerializer, RegisterSerializer, VerifyCodeSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from config.settings import DEBUG
from users.throttles import PhoneCodeThrottle, VerifyCodeThrottle


def get_or_create_login_user(phone, name):
    """Находит подтверждённого пользователя по телефону или создаёт новую запись."""
    user, created = User.objects.get_or_create(
        phone=phone,
        defaults={"name": name, "password": make_password(None)},
    )
    if not created and user.name != name:
        user.name = name
        user.save(update_fields=["name"])
    return user


class RegisterView(APIView):
    """
    Вход по имени и телефону.
    В случае успеха отправляет код в SMS.
    """
    permission_classes = [AllowAny]
    throttle_classes = [PhoneCodeThrottle]  # Ограничение запросов

    def post(self, request):
        """Проверяет имя и телефон, сохраняет временный код и отправляет SMS."""
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data["phone"]
            name = serializer.validated_data["name"].strip()
            try:
                message_code = generate_login_code(phone, name)
                if DEBUG:
                    return Response(
                        {
                            "message": "Тестовый режим: SMS не отправляется",
                            "debug_code": message_code,
                        },
                        status=status.HTTP_200_OK,
                    )

                code = send_sms(phone, message_code)
                if code:
                    return Response(
                        {"message": "Код отправлен"},
                        status=status.HTTP_200_OK,
                    )
                cache.delete(f"user_{phone}_code")
                return Response(
                    {"message": "Ошибка отправки SMS. Попробуйте позже."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            except Exception:
                cache.delete(f"user_{phone}_code")
                return Response(
                    {"message": "Ошибка отправки SMS. Попробуйте позже."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyCodeView(APIView):
    """
    Эндпоинт для проверки кода подтверждения.
    Ожидает номер телефона и код подтверждения.
    Проверяет корректность кода и, в случае успеха, выдаёт JWT-токены.
    """

    permission_classes = [AllowAny]
    throttle_classes = [VerifyCodeThrottle]

    def post(self, request):
        """Проверяет одноразовый код и возвращает JWT вместе с данными пользователя."""
        serializer = VerifyCodeSerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data["phone"]
            code = serializer.validated_data["code"]
            pending = cache.get(f"user_{phone}_code")
            if pending and pending.get("code") == code:
                user = get_or_create_login_user(phone, pending["name"])
                cache.delete(f"user_{phone}_code")
                refresh = RefreshToken.for_user(user)
                return Response(
                    {
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                        "user": UserSerializer(user).data,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "detail": "Неверный код или срок действия истёк",
                        "code": "invalid_code",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Эндпоинт для получения информации о пользователе.
    Ожидает access_token.
    После чего выдает информации о пользователе
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Возвращает профиль пользователя, определённого access-токеном."""
        return self.request.user


class LogoutView(APIView):
    """Отзывает refresh-токен текущего пользователя."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Проверяет владельца refresh-токена и заносит токен в список отозванных."""
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "Передайте refresh-токен", "code": "refresh_required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            if str(token.get("user_id")) != str(request.user.pk):
                return Response(
                    {"detail": "Токен принадлежит другому пользователю", "code": "wrong_user"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            token.blacklist()
        except TokenError:
            return Response(
                {"detail": "Refresh-токен недействителен", "code": "invalid_token"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


