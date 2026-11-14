from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from users.apps import UsersConfig
from users.views import LogoutView, RegisterView, UserProfileView, VerifyCodeView


app_name = UsersConfig.name

urlpatterns = [
    path("phone/request-code/", RegisterView.as_view(), name="request_code"),
    path("phone/verify/", VerifyCodeView.as_view(), name="verify_code"),
    path("me/", UserProfileView.as_view(), name="user_profile"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
