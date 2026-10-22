from django.urls import path

from .views import catalog_search

app_name = "search"
urlpatterns = [path("search/", catalog_search, name="catalog-search")]
