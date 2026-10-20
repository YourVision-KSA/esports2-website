from django.urls import path

from . import views

urlpatterns = [
    path("", views.vote, name="vote"),
    path("results/", views.results, name="vote-results"),
]
