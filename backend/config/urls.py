"""Root URL configuration."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.health.urls")),
    path("api/v1/catalog/", include("apps.search.urls")),
    path("api/v1/", include("apps.catalog.urls")),
    path("api/v1/", include("apps.missions.urls")),
]
