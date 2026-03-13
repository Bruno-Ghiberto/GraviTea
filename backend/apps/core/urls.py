from rest_framework.routers import DefaultRouter

from apps.core.views.customization import FieldDefinitionViewSet, ModuleConfigViewSet

router = DefaultRouter()
router.register("field-definitions", FieldDefinitionViewSet, basename="field-definitions")
router.register("module-config", ModuleConfigViewSet, basename="module-config")

urlpatterns = router.urls
