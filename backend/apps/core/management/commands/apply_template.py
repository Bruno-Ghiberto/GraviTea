import uuid

from django.core.management.base import BaseCommand, CommandError

from apps.core.models import TenantFieldDefinition, TenantModuleConfig, BusinessTemplate
from apps.core.models.customization import EntityType, FieldType, ModuleChoice

# Embedded template data for "ferreteria"
FERRETERIA_TEMPLATE = {
    "modules": [
        {"module": ModuleChoice.INVENTARIO, "enabled": True},
        {"module": ModuleChoice.VENTAS, "enabled": True},
        {"module": ModuleChoice.FACTURACION, "enabled": True},
    ],
    "field_definitions": [
        {
            "field_key": "peso_kg",
            "label": "Peso (kg)",
            "entity_type": EntityType.PRODUCT,
            "field_type": FieldType.DECIMAL,
            "section": "dimensiones",
            "position": 0,
        },
        {
            "field_key": "largo_cm",
            "label": "Largo (cm)",
            "entity_type": EntityType.PRODUCT,
            "field_type": FieldType.DECIMAL,
            "section": "dimensiones",
            "position": 1,
        },
        {
            "field_key": "ancho_cm",
            "label": "Ancho (cm)",
            "entity_type": EntityType.PRODUCT,
            "field_type": FieldType.DECIMAL,
            "section": "dimensiones",
            "position": 2,
        },
        {
            "field_key": "alto_cm",
            "label": "Alto (cm)",
            "entity_type": EntityType.PRODUCT,
            "field_type": FieldType.DECIMAL,
            "section": "dimensiones",
            "position": 3,
        },
        {
            "field_key": "material",
            "label": "Material",
            "entity_type": EntityType.PRODUCT,
            "field_type": FieldType.SELECT,
            "section": "caracteristicas",
            "position": 0,
            "choices": ["acero", "aluminio", "bronce", "cobre", "hierro", "plastico", "madera"],
        },
        {
            "field_key": "marca",
            "label": "Marca",
            "entity_type": EntityType.PRODUCT,
            "field_type": FieldType.TEXT,
            "section": "caracteristicas",
            "position": 1,
        },
        {
            "field_key": "codigo_proveedor",
            "label": "Código de Proveedor",
            "entity_type": EntityType.PRODUCT,
            "field_type": FieldType.TEXT,
            "section": "caracteristicas",
            "position": 2,
        },
    ],
}

TEMPLATES = {
    "ferreteria": FERRETERIA_TEMPLATE,
}


class Command(BaseCommand):
    help = "Apply a business template to a tenant (creates module configs and field definitions)"

    def add_arguments(self, parser):
        parser.add_argument("slug", type=str, help="Template slug (e.g., ferreteria)")
        parser.add_argument("--tenant-id", type=str, required=True, help="Tenant UUID")

    def handle(self, *args, **options):
        slug = options["slug"]
        tenant_id_str = options["tenant_id"]

        try:
            tenant_id = uuid.UUID(tenant_id_str)
        except ValueError:
            raise CommandError(f"Invalid UUID: {tenant_id_str}")

        # First try embedded templates, then DB
        template_data = TEMPLATES.get(slug)
        if template_data is None:
            try:
                bt = BusinessTemplate.objects.get(slug=slug)
                template_data = {
                    "modules": bt.modules,
                    "field_definitions": bt.field_definitions,
                }
            except BusinessTemplate.DoesNotExist:
                raise CommandError(f"Template '{slug}' not found")

        # Also verify tenant exists
        from apps.core.models import Tenant
        if not Tenant.objects.filter(pk=tenant_id).exists():
            raise CommandError(f"Tenant {tenant_id} not found")

        # Create module configs
        for mod_data in template_data.get("modules", []):
            _, created = TenantModuleConfig.objects.get_or_create(
                tenant_id=tenant_id,
                module=mod_data["module"],
                defaults={"enabled": mod_data.get("enabled", True)},
            )
            status = "Created" if created else "Already exists"
            self.stdout.write(f"  {status}: ModuleConfig {mod_data['module']}")

        # Create field definitions
        for fd_data in template_data.get("field_definitions", []):
            lookup = {
                "tenant_id": tenant_id,
                "entity_type": fd_data["entity_type"],
                "field_key": fd_data["field_key"],
            }
            defaults = {
                "label": fd_data["label"],
                "field_type": fd_data["field_type"],
                "section": fd_data.get("section", "custom_fields"),
                "position": fd_data.get("position", 0),
            }
            if "choices" in fd_data:
                defaults["choices"] = fd_data["choices"]
            _, created = TenantFieldDefinition.objects.get_or_create(
                **lookup, defaults=defaults,
            )
            status = "Created" if created else "Already exists"
            self.stdout.write(f"  {status}: FieldDefinition {fd_data['field_key']}")

        self.stdout.write(self.style.SUCCESS(f"Template '{slug}' applied to tenant {tenant_id}"))
