from django.urls import path

from . import views

urlpatterns = [
    path("", views.overview, name="bracket-overview"),
    path("<slug:slug>/", views.detail, name="bracket-detail"),
]
