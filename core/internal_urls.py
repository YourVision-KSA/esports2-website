from django.urls import path

from . import views

urlpatterns = [
    path("outbox/", views.internal_outbox, name="internal-outbox"),
]
