from django.urls import path

from . import views

urlpatterns = [
    path("", views.choose, name="register-choose"),
    path("<slug:slug>/", views.register_form, name="register-form"),
]
