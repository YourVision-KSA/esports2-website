from django.urls import path

from . import views

urlpatterns = [
    path("<str:token>/", views.manage, name="manage"),
    path("<str:token>/withdraw/", views.withdraw, name="manage-withdraw"),
]
