from django.urls import path

from .views import (
    AuthorCoursesView,
    CategoriesView,
    CourseDetailView,
    CourseLessonsView,
    CourseListView,
    LessonDetailView,
    AuthorCourseListCreateView,
    AuthorCourseDetailView,
    AuthorLessonListCreateView,
    AuthorLessonDetailView,
    ModerationQueueView,
    ModerationDecisionView,
)

urlpatterns = [
    path("author/courses/", AuthorCourseListCreateView.as_view(), name="author-course-list-create"),
    path("author/courses/<int:pk>/", AuthorCourseDetailView.as_view(), name="author-course-detail"),
    path("author/courses/<int:course_id>/lessons/", AuthorLessonListCreateView.as_view(), name="author-lesson-list-create"),
    path("author/courses/<int:course_id>/lessons/<int:pk>/", AuthorLessonDetailView.as_view(), name="author-lesson-detail"),
    path("moderation/courses/", ModerationQueueView.as_view(), name="moderation-course-queue"),
    path("moderation/courses/<int:pk>/review/", ModerationDecisionView.as_view(), name="moderation-course-review"),
    path("categories/", CategoriesView.as_view(), name="categories"),
    # API aliases keep current frontend's publication vocabulary while each
    # record remains a Course with separately stored Lesson content.
    path("posts/", CourseListView.as_view(), name="post-list"),
    path("posts/<int:pk>/", CourseDetailView.as_view(), name="post-detail"),
    path("courses/", CourseListView.as_view(), name="course-list"),
    path("courses/<int:pk>/", CourseDetailView.as_view(), name="course-detail"),
    path("courses/<int:course_id>/lessons/", CourseLessonsView.as_view(), name="course-lessons"),
    path("lessons/<int:pk>/", LessonDetailView.as_view(), name="lesson-detail"),
    path("authors/<int:author_id>/courses/", AuthorCoursesView.as_view(), name="author-courses"),
]
