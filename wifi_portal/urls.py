from django.contrib import admin
from django.urls import include, path

from portal import views

urlpatterns = [
    path("", views.index, name="index"),
    path("", include("portal.urls")),
    path("admin/", admin.site.urls),
]
