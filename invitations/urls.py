from django.urls import path

from . import views

urlpatterns = [
    path("<str:token>/", views.invite, name="invite"),
    path("<str:token>/badge/", views.invite_badge, name="invite-badge"),
]
