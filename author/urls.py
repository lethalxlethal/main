from django.urls import path

from .views import AuthorDetailView, AuthorListView

urlpatterns = [
    path("authors/", AuthorListView.as_view(), name="author-list"),
    path("authors/<int:pk>/", AuthorDetailView.as_view(), name="author-detail"),
    # Совместимые адреса с текущим frontend API-клиентом.
    path("creators/", AuthorListView.as_view(), name="creator-list"),
    path("creators/<int:pk>/", AuthorDetailView.as_view(), name="creator-detail"),
]
