from rest_framework.routers import DefaultRouter

from .views import TemplateViewSet

router = DefaultRouter()
router.register("templates", TemplateViewSet, basename="template")

urlpatterns = router.urls
