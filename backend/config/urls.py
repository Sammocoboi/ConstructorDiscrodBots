
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include([
        path("", include("backend.apps.bots.urls")),
        path("", include("backend.apps.modules.urls")),
        path("", include("backend.apps.commands.urls")),
        path("", include("backend.apps.notifications.urls")),
    ])),
]
