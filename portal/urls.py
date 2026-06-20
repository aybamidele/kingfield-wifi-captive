from django.urls import path

from . import views

urlpatterns = [
    path("portal/", views.portal_form, name="portal"),
    path("portal/submit/", views.portal_submit, name="portal_submit"),
    path("success/", views.success, name="success"),
    path("terms/", views.terms, name="terms"),
    path("privacy/", views.privacy, name="privacy"),
    path("health/", views.health, name="health"),
]
