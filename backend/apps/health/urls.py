from django.urls import path

from .views import live, ready

app_name = "health"
urlpatterns = [
    path("health/live/", live, name="live"),
    path("health/ready/", ready, name="ready"),
]
