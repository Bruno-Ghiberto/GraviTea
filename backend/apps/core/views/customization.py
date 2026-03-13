from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.core.models import TenantFieldDefinition, TenantModuleConfig
from apps.core.serializers.customization import (
    FieldDefinitionSerializer,
    ModuleConfigSerializer,
)


class FieldDefinitionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FieldDefinitionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = TenantFieldDefinition.objects.filter(
            tenant_id=self.request.user.tenant_id,
            active=True,
        )
        entity_type = self.request.query_params.get("entity_type")
        if entity_type:
            qs = qs.filter(entity_type=entity_type)
        return qs.order_by("section", "position", "field_key")


class ModuleConfigViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ModuleConfigSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TenantModuleConfig.objects.filter(
            tenant_id=self.request.user.tenant_id,
        )
