from django.urls import path

from . import views

urlpatterns = [
    path("bracket/<slug:slug>.json", views.api_bracket, name="api-bracket"),
]
