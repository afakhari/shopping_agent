from django.urls import path

from .views import create_contact_attempt, create_mission, get_mission, get_visit_plan, mission_focus, mission_turn

app_name = "missions"
urlpatterns = [
    path("missions/", create_mission, name="mission-create"),
    path("missions/<uuid:mission_id>/", get_mission, name="mission-detail"),
    path("missions/<uuid:mission_id>/visit-plan/", get_visit_plan, name="mission-visit-plan"),
    path("missions/<uuid:mission_id>/turns/", mission_turn, name="mission-turn"),
    path("missions/<uuid:mission_id>/focus/", mission_focus, name="mission-focus"),
    path(
        "missions/<uuid:mission_id>/contact-attempts/",
        create_contact_attempt,
        name="mission-contact-attempt",
    ),
]
