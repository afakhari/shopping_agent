from django.urls import path

from .views import create_contact_attempt, create_mission, get_mission, mission_turn

app_name = "missions"
urlpatterns = [
    path("missions/", create_mission, name="mission-create"),
    path("missions/<uuid:mission_id>/", get_mission, name="mission-detail"),
    path("missions/<uuid:mission_id>/turns/", mission_turn, name="mission-turn"),
    path(
        "missions/<uuid:mission_id>/contact-attempts/",
        create_contact_attempt,
        name="mission-contact-attempt",
    ),
]
