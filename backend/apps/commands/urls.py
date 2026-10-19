from rest_framework.routers import DefaultRouter

from .views import CommandLibraryViewSet

router = DefaultRouter()
router.register("commands-library", CommandLibraryViewSet, basename="command-library")

urlpatterns = router.urls
