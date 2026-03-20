"""
Management command to seed mock data for development and testing.

Supports both legacy hardcoded seeding and scenario-based seeding
with deterministic UUIDs for reproducible test data.

Per spec.md FR-025 through FR-028 requirements:
- T065-T067: Scenario-based seeding with deterministic UUIDs
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.auth.models import AppUser, Role
from apps.core.managers.tenant_bound import set_current_tenant_id
from apps.core.models import Branch, Tenant
from apps.inventario.models import (
    PriceList,
    Product,
    ProductCategory,
    StockSnapshot,
    Supplier,
)

from .seed_utils import (
    list_available_scenarios,
    load_scenario,
)

# Development-only seed password for demo/test users.  # NOSONAR
# This command is never used in production; passwords are intentionally weak
# for local development convenience.
_SEED_PASSWORD = "testpass123"  # NOSONAR


class Command(BaseCommand):
    help = "Seed the database with mock data for development and testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before seeding",
        )
        parser.add_argument(
            "--scenario",
            type=str,
            default=None,
            help=(
                "Name of the seed scenario to use (e.g., 'minimal', 'standard', "
                "'multi_tenant'). If not specified, uses legacy hardcoded data."
            ),
        )
        parser.add_argument(
            "--list-scenarios",
            action="store_true",
            help="List available seed scenarios and exit",
        )

    def handle(self, *args, **options):
        # Handle --list-scenarios flag
        if options.get("list_scenarios"):
            self.list_scenarios()
            return

        scenario_name = options.get("scenario")

        if scenario_name:
            self.handle_scenario_seeding(scenario_name, options)
        else:
            self.handle_legacy_seeding(options)

    def list_scenarios(self):
        """List all available seed scenarios."""
        scenarios = list_available_scenarios()

        if not scenarios:
            self.stdout.write(self.style.WARNING("No scenarios found."))
            return

        self.stdout.write("\n=== Available Seed Scenarios ===\n")
        for name in sorted(scenarios):
            try:
                scenario = load_scenario(name)
                self.stdout.write(f"  {name}: {scenario.description}")
            except Exception:
                self.stdout.write(f"  {name}: (unable to load description)")

    def handle_scenario_seeding(self, scenario_name, options):
        """Handle scenario-based seeding with deterministic UUIDs."""
        self.stdout.write(f"Loading scenario: {scenario_name}")

        try:
            scenario = load_scenario(scenario_name)
        except FileNotFoundError:
            available = list_available_scenarios()
            self.stderr.write(
                self.style.ERROR(f"Scenario '{scenario_name}' not found.")
            )
            self.stderr.write(f"Available scenarios: {', '.join(available)}")
            return

        self.stdout.write(f"Seeding database with scenario: {scenario.name}")
        self.stdout.write(f"Description: {scenario.description}")

        with transaction.atomic():
            if options["clear"]:
                self.clear_data()

            stats = self.seed_from_scenario(scenario)

        self.stdout.write(self.style.SUCCESS(f"Scenario '{scenario_name}' seeded successfully!"))
        self.stdout.write("\n=== Summary ===")
        for entity_type, count in stats.items():
            self.stdout.write(f"{entity_type.capitalize()}: {count}")

    def seed_from_scenario(self, scenario):
        """Seed database from a scenario definition.

        Returns:
            dict: Statistics of created entities by type.
        """
        stats = {
            "tenants": 0,
            "roles": 0,
            "users": 0,
            "branches": 0,
            "categories": 0,
            "products": 0,
            "suppliers": 0,
            "price_lists": 0,
            "stock_levels": 0,
        }

        # Track created entities for dependency resolution
        created_entities = {}

        # Create tenants first
        for entity_config in scenario.tenants:
            tenant_uuid = scenario.get_uuid("tenant", entity_config.identifier)
            tenant, created = Tenant.objects.get_or_create(
                id=tenant_uuid,
                defaults={
                    "name": entity_config.data.get("name", entity_config.identifier),
                    "is_active": entity_config.data.get("is_active", True),
                },
            )
            created_entities[f"tenant:{entity_config.identifier}"] = tenant
            if created:
                stats["tenants"] += 1
                self.stdout.write(f"  Created tenant: {tenant.name}")
            else:
                self.stdout.write(f"  Exists tenant: {tenant.name}")

        # Create branches (depend on tenants)
        for entity_config in scenario.branches:
            tenant_key = self._get_dependency(entity_config.dependencies, "tenant")
            if tenant_key and tenant_key in created_entities:
                tenant = created_entities[tenant_key]
                set_current_tenant_id(tenant.id)

                branch_uuid = scenario.get_uuid("branch", entity_config.identifier)
                branch, created = Branch.all_objects.get_or_create(
                    id=branch_uuid,
                    defaults={
                        "tenant": tenant,
                        "tenant_id": tenant.id,
                        "name": entity_config.data.get("name", entity_config.identifier),
                        "address": entity_config.data.get("address", ""),
                        "is_active": entity_config.data.get("is_active", True),
                    },
                )
                created_entities[f"branch:{entity_config.identifier}"] = branch
                if created:
                    stats["branches"] += 1
                    self.stdout.write(f"  Created branch: {branch.name}")
                else:
                    self.stdout.write(f"  Exists branch: {branch.name}")

        # Create roles (depend on tenants)
        for entity_config in scenario.roles:
            tenant_key = self._get_dependency(entity_config.dependencies, "tenant")
            if tenant_key and tenant_key in created_entities:
                tenant = created_entities[tenant_key]
                set_current_tenant_id(tenant.id)

                role_uuid = scenario.get_uuid("role", entity_config.identifier)
                role, created = Role.all_objects.get_or_create(
                    id=role_uuid,
                    defaults={
                        "tenant": tenant,
                        "tenant_id": tenant.id,
                        "name": entity_config.data.get("name", entity_config.identifier),
                        "permissions": entity_config.data.get("permissions", []),
                    },
                )
                created_entities[f"role:{entity_config.identifier}"] = role
                if created:
                    stats["roles"] += 1
                    self.stdout.write(f"  Created role: {role.name}")
                else:
                    self.stdout.write(f"  Exists role: {role.name}")

        # Create categories (depend on tenants)
        for entity_config in scenario.categories:
            tenant_key = self._get_dependency(entity_config.dependencies, "tenant")
            if tenant_key and tenant_key in created_entities:
                tenant = created_entities[tenant_key]
                set_current_tenant_id(tenant.id)

                cat_uuid = scenario.get_uuid("category", entity_config.identifier)
                category, created = ProductCategory.all_objects.get_or_create(
                    id=cat_uuid,
                    defaults={
                        "tenant": tenant,
                        "tenant_id": tenant.id,
                        "name": entity_config.data.get("name", entity_config.identifier),
                    },
                )
                created_entities[f"category:{entity_config.identifier}"] = category
                if created:
                    stats["categories"] += 1
                    self.stdout.write(f"  Created category: {category.name}")
                else:
                    self.stdout.write(f"  Exists category: {category.name}")

        # Create suppliers (depend on tenants)
        for entity_config in scenario.suppliers:
            tenant_key = self._get_dependency(entity_config.dependencies, "tenant")
            if tenant_key and tenant_key in created_entities:
                tenant = created_entities[tenant_key]
                set_current_tenant_id(tenant.id)

                supplier_uuid = scenario.get_uuid("supplier", entity_config.identifier)
                supplier, created = Supplier.all_objects.get_or_create(
                    id=supplier_uuid,
                    defaults={
                        "tenant": tenant,
                        "tenant_id": tenant.id,
                        "name": entity_config.data.get("name", entity_config.identifier),
                        "is_active": entity_config.data.get("is_active", True),
                    },
                )
                created_entities[f"supplier:{entity_config.identifier}"] = supplier
                if created:
                    stats["suppliers"] += 1
                    self.stdout.write(f"  Created supplier: {supplier.name}")
                else:
                    self.stdout.write(f"  Exists supplier: {supplier.name}")

        # Create price lists (depend on tenants)
        for entity_config in scenario.price_lists:
            tenant_key = self._get_dependency(entity_config.dependencies, "tenant")
            if tenant_key and tenant_key in created_entities:
                tenant = created_entities[tenant_key]
                set_current_tenant_id(tenant.id)

                pl_uuid = scenario.get_uuid("price_list", entity_config.identifier)
                price_list, created = PriceList.all_objects.get_or_create(
                    id=pl_uuid,
                    defaults={
                        "tenant": tenant,
                        "tenant_id": tenant.id,
                        "name": entity_config.data.get("name", entity_config.identifier),
                        "is_default": entity_config.data.get("is_default", False),
                    },
                )
                created_entities[f"price_list:{entity_config.identifier}"] = price_list
                if created:
                    stats["price_lists"] += 1
                    self.stdout.write(f"  Created price list: {price_list.name}")
                else:
                    self.stdout.write(f"  Exists price list: {price_list.name}")

        # Create products (depend on tenants and categories)
        for entity_config in scenario.products:
            tenant_key = self._get_dependency(entity_config.dependencies, "tenant")
            category_key = self._get_dependency(entity_config.dependencies, "category")
            if tenant_key and tenant_key in created_entities:
                tenant = created_entities[tenant_key]
                set_current_tenant_id(tenant.id)
                category = created_entities.get(category_key)

                product_uuid = scenario.get_uuid("product", entity_config.identifier)
                product, created = Product.all_objects.get_or_create(
                    id=product_uuid,
                    defaults={
                        "tenant": tenant,
                        "tenant_id": tenant.id,
                        "name": entity_config.data.get("name", entity_config.identifier),
                        "sku": entity_config.data.get("sku", entity_config.identifier),
                        "category": category,
                        "unit_price": Decimal(entity_config.data.get("base_price", "0")),
                        "cost_price": Decimal(entity_config.data.get("cost_price", "0")),
                        "is_active": entity_config.data.get("is_active", True),
                    },
                )
                created_entities[f"product:{entity_config.identifier}"] = product
                if created:
                    stats["products"] += 1
                    self.stdout.write(f"  Created product: {product.name}")
                else:
                    self.stdout.write(f"  Exists product: {product.name}")

        # Create users (depend on tenants, roles, and branches)
        for entity_config in scenario.users:
            tenant_key = self._get_dependency(entity_config.dependencies, "tenant")
            role_key = self._get_dependency(entity_config.dependencies, "role")
            branch_key = self._get_dependency(entity_config.dependencies, "branch")

            if tenant_key and tenant_key in created_entities:
                tenant = created_entities[tenant_key]
                set_current_tenant_id(tenant.id)
                role = created_entities.get(role_key)
                branch = created_entities.get(branch_key)

                user_uuid = scenario.get_uuid("user", entity_config.identifier)
                email = entity_config.data.get("email", f"{entity_config.identifier}@test.local")

                existing = AppUser.all_objects.filter(id=user_uuid).first()
                if existing:
                    created_entities[f"user:{entity_config.identifier}"] = existing
                    self.stdout.write(f"  Exists user: {existing.email}")
                else:
                    user = AppUser.objects.create_user(
                        id=user_uuid,
                        email=email,
                        tenant=tenant,
                        password=_SEED_PASSWORD,
                        full_name=f"{entity_config.data.get('first_name', '')} {entity_config.data.get('last_name', '')}".strip(),
                        role=role,
                        default_branch=branch,
                    )
                    created_entities[f"user:{entity_config.identifier}"] = user
                    stats["users"] += 1
                    self.stdout.write(f"  Created user: {user.email}")

        # Create stock levels (depend on branches and products)
        for entity_config in scenario.stock_levels:
            branch_key = self._get_dependency(entity_config.dependencies, "branch")
            product_key = self._get_dependency(entity_config.dependencies, "product")

            branch = created_entities.get(branch_key)
            product = created_entities.get(product_key)

            if branch and product:
                existing = StockSnapshot.objects.filter(
                    branch=branch, product=product
                ).first()

                if existing:
                    self.stdout.write(f"  Exists stock: {product.name} @ {branch.name}")
                else:
                    StockSnapshot.objects.create(
                        branch=branch,
                        product=product,
                        quantity=Decimal(str(entity_config.data.get("quantity", 0))),
                        reserved_quantity=Decimal("0"),
                    )
                    stats["stock_levels"] += 1
                    self.stdout.write(f"  Created stock: {product.name} @ {branch.name}")

        return stats

    def _get_dependency(self, dependencies, entity_type):
        """Extract dependency of given type from dependencies list."""
        for dep in dependencies:
            if dep.startswith(f"{entity_type}:"):
                return dep
        return None

    def handle_legacy_seeding(self, options):
        """Handle legacy hardcoded seeding (original behavior)."""
        self.stdout.write("Seeding database with mock data...")

        with transaction.atomic():
            if options["clear"]:
                self.clear_data()

            tenant = self.create_tenant()

            # Set tenant context for all tenant-bound operations
            set_current_tenant_id(tenant.id)

            branches = self.create_branches(tenant)
            roles = self.create_roles(tenant)
            users = self.create_users(tenant, roles, branches)
            categories = self.create_categories(tenant)
            suppliers = self.create_suppliers(tenant)
            price_lists = self.create_price_lists(tenant)
            products = self.create_products(tenant, categories, suppliers)
            self.create_stock_snapshots(products, branches)

        self.stdout.write(self.style.SUCCESS("Mock data seeded successfully!"))
        self.stdout.write("\n=== Summary ===")
        self.stdout.write(f"Tenant: {tenant.name} (ID: {tenant.id})")
        self.stdout.write(f"Branches: {len(branches)}")
        self.stdout.write(f"Roles: {len(roles)}")
        self.stdout.write(f"Users: {len(users)}")
        self.stdout.write(f"Categories: {len(categories)}")
        self.stdout.write(f"Suppliers: {len(suppliers)}")
        self.stdout.write(f"Price Lists: {len(price_lists)}")
        self.stdout.write(f"Products: {len(products)}")
        self.stdout.write("\n=== Login Credentials ===")
        self.stdout.write(f"Admin: admin@gravitea-demo.com / {_SEED_PASSWORD}")
        self.stdout.write(f"Manager: gerente@gravitea-demo.com / {_SEED_PASSWORD}")
        self.stdout.write(f"Cashier: cajero@gravitea-demo.com / {_SEED_PASSWORD}")

    def clear_data(self):
        """Clear existing mock data."""
        self.stdout.write("Clearing existing data...")
        # Delete in reverse dependency order
        StockSnapshot.objects.all().delete()
        Product.all_objects.all().delete()
        ProductCategory.all_objects.all().delete()
        Supplier.all_objects.all().delete()
        PriceList.all_objects.all().delete()
        AppUser.all_objects.all().delete()
        Role.all_objects.all().delete()
        Branch.all_objects.all().delete()
        Tenant.objects.all().delete()
        self.stdout.write("  Existing data cleared.")

    def create_tenant(self):
        """Create demo tenant."""
        self.stdout.write("Creating tenant...")
        tenant, created = Tenant.objects.get_or_create(
            name="Gravitea Demo",
            defaults={
                "tax_id": "30-12345678-9",
                "plan_type": "PRO",
                "valid_until": timezone.now() + timezone.timedelta(days=365),
                "is_active": True,
                # Note: fiscal_config_public requires fiscal_secrets_ref
                # so we leave it null for demo purposes
            },
        )
        if created:
            self.stdout.write(f"  Created tenant: {tenant.name}")
        else:
            self.stdout.write(f"  Tenant already exists: {tenant.name}")
        return tenant

    def create_branches(self, tenant):
        """Create demo branches."""
        self.stdout.write("Creating branches...")
        branches_data = [
            {
                "name": "Casa Central",
                "address": "Av. Corrientes 1234, CABA",
                "phone": "+54 11 4567-8901",
                "coordinates": {"lat": -34.6037, "lng": -58.3816},
                "afip_pos_number": 1,
            },
            {
                "name": "Sucursal Norte",
                "address": "Av. Santa Fe 2345, CABA",
                "phone": "+54 11 4567-8902",
                "coordinates": {"lat": -34.5875, "lng": -58.4054},
                "afip_pos_number": 2,
            },
            {
                "name": "Sucursal Sur",
                "address": "Av. Rivadavia 5678, CABA",
                "phone": "+54 11 4567-8903",
                "coordinates": {"lat": -34.6261, "lng": -58.4281},
                "afip_pos_number": 3,
            },
        ]

        branches = []
        for data in branches_data:
            branch, created = Branch.all_objects.get_or_create(
                tenant=tenant,
                name=data["name"],
                defaults={
                    "tenant_id": tenant.id,
                    "address": data["address"],
                    "phone": data["phone"],
                    "coordinates": data["coordinates"],
                    "afip_pos_number": data["afip_pos_number"],
                    "is_active": True,
                },
            )
            branches.append(branch)
            status = "Created" if created else "Exists"
            self.stdout.write(f"  {status}: {branch.name}")

        return branches

    def create_roles(self, tenant):
        """Create demo roles."""
        self.stdout.write("Creating roles...")
        roles_data = [
            {
                "name": "Administrador",
                "permissions": [
                    "inventory.read",
                    "inventory.write",
                    "inventory.admin",
                    "sales.read",
                    "sales.write",
                    "sales.create",
                    "sales.admin",
                    "purchases.read",
                    "purchases.write",
                    "purchases.create",
                    "purchases.admin",
                    "customers.read",
                    "customers.write",
                    "reports.read",
                    "reports.write",
                    "reports.export",
                    "settings.read",
                    "settings.write",
                    "settings.admin",
                ],
            },
            {
                "name": "Gerente",
                "permissions": [
                    "inventory.read",
                    "inventory.write",
                    "sales.read",
                    "sales.write",
                    "sales.create",
                    "purchases.read",
                    "purchases.write",
                    "customers.read",
                    "customers.write",
                    "reports.read",
                    "reports.write",
                    "reports.export",
                    "settings.read",
                ],
            },
            {
                "name": "Vendedor",
                "permissions": [
                    "inventory.read",
                    "sales.read",
                    "sales.write",
                    "sales.create",
                    "customers.read",
                    "reports.read",
                ],
            },
            {
                "name": "Cajero",
                "permissions": [
                    "inventory.read",
                    "sales.read",
                    "sales.create",
                ],
            },
        ]

        roles = []
        for data in roles_data:
            role, created = Role.all_objects.get_or_create(
                tenant=tenant,
                name=data["name"],
                defaults={
                    "tenant_id": tenant.id,
                    "permissions": data["permissions"],
                },
            )
            roles.append(role)
            status = "Created" if created else "Exists"
            self.stdout.write(f"  {status}: {role.name}")

        return roles

    def create_users(self, tenant, roles, branches):
        """Create demo users."""
        self.stdout.write("Creating users...")
        users_data = [
            {
                "email": "admin@gravitea-demo.com",
                "full_name": "Admin Usuario",
                "password": _SEED_PASSWORD,
                "role_name": "Administrador",
                "branch_index": 0,
            },
            {
                "email": "gerente@gravitea-demo.com",
                "full_name": "Gerente Usuario",
                "password": _SEED_PASSWORD,
                "role_name": "Gerente",
                "branch_index": 0,
            },
            {
                "email": "vendedor1@gravitea-demo.com",
                "full_name": "Vendedor Uno",
                "password": _SEED_PASSWORD,
                "role_name": "Vendedor",
                "branch_index": 0,
            },
            {
                "email": "vendedor2@gravitea-demo.com",
                "full_name": "Vendedor Dos",
                "password": _SEED_PASSWORD,
                "role_name": "Vendedor",
                "branch_index": 1,
            },
            {
                "email": "cajero@gravitea-demo.com",
                "full_name": "Cajero Usuario",
                "password": _SEED_PASSWORD,
                "role_name": "Cajero",
                "branch_index": 0,
            },
        ]

        roles_dict = {r.name: r for r in roles}
        users = []
        for data in users_data:
            existing = AppUser.all_objects.filter(email=data["email"]).first()
            if existing:
                users.append(existing)
                self.stdout.write(f"  Exists: {data['email']}")
                continue

            user = AppUser.objects.create_user(
                email=data["email"],
                tenant=tenant,
                password=data["password"],
                full_name=data["full_name"],
                role=roles_dict.get(data["role_name"]),
                default_branch=branches[data["branch_index"]],
            )
            users.append(user)
            self.stdout.write(f"  Created: {user.email}")

        return users

    def create_categories(self, tenant):
        """Create hardware store product categories."""
        self.stdout.write("Creating categories...")
        categories_data = [
            {"name": "Herramientas Eléctricas", "parent": None},
            {"name": "Taladros y Rotomartillos", "parent": "Herramientas Eléctricas"},
            {"name": "Amoladoras y Sierras", "parent": "Herramientas Eléctricas"},
            {"name": "Lijadoras y Cepillos", "parent": "Herramientas Eléctricas"},
            {"name": "Compresores y Equipos", "parent": "Herramientas Eléctricas"},
            {"name": "Herramientas Manuales", "parent": None},
            {"name": "Llaves y Destornilladores", "parent": "Herramientas Manuales"},
            {"name": "Pinzas y Alicates", "parent": "Herramientas Manuales"},
            {"name": "Martillos y Mazas", "parent": "Herramientas Manuales"},
            {"name": "Medición y Corte", "parent": "Herramientas Manuales"},
            {"name": "Maquinaria Jardín", "parent": None},
            {"name": "Corte de Césped", "parent": "Maquinaria Jardín"},
            {"name": "Poda y Mantenimiento", "parent": "Maquinaria Jardín"},
            {"name": "Soldadura y Corte", "parent": None},
            {"name": "Soldadoras", "parent": "Soldadura y Corte"},
            {"name": "Accesorios Soldadura", "parent": "Soldadura y Corte"},
            {"name": "Insumos y Abrasivos", "parent": None},
            {"name": "Discos y Lijas", "parent": "Insumos y Abrasivos"},
            {"name": "Mechas y Puntas", "parent": "Insumos y Abrasivos"},
            {"name": "Seguridad Industrial", "parent": None},
            {"name": "Protección Personal", "parent": "Seguridad Industrial"},
            {"name": "Protección Corporal", "parent": "Seguridad Industrial"},
            {"name": "Fijaciones y Ferretería", "parent": None},
            {"name": "Tornillería", "parent": "Fijaciones y Ferretería"},
            {"name": "Fijaciones Varias", "parent": "Fijaciones y Ferretería"},
            {"name": "Químicos y Adhesivos", "parent": None},
            {"name": "Pegamentos y Selladores", "parent": "Químicos y Adhesivos"},
            {"name": "Cintas y Lubricantes", "parent": "Químicos y Adhesivos"},
        ]

        categories = {}
        for data in categories_data:
            parent = categories.get(data["parent"]) if data["parent"] else None
            cat, created = ProductCategory.all_objects.get_or_create(
                tenant=tenant,
                name=data["name"],
                defaults={
                    "tenant_id": tenant.id,
                    "parent": parent,
                },
            )
            categories[data["name"]] = cat
            status = "Created" if created else "Exists"
            self.stdout.write(f"  {status}: {cat.name}")

        return categories

    def create_suppliers(self, tenant):
        """Create hardware store suppliers."""
        self.stdout.write("Creating suppliers...")
        suppliers_data = [
            {"name": "DeWalt Argentina", "lead_time_days": 5},
            {"name": "Makita Distribuidor", "lead_time_days": 5},
            {"name": "Stanley Black & Decker", "lead_time_days": 4},
            {"name": "Bremen Tools", "lead_time_days": 3},
            {"name": "Bosch Power Tools", "lead_time_days": 7},
            {"name": "Lusqtoff S.A.", "lead_time_days": 4},
            {"name": "Truper Argentina", "lead_time_days": 6},
            {"name": "3M Argentina", "lead_time_days": 5},
            {"name": "Ferretería Mayorista Central", "lead_time_days": 2},
            {"name": "Importadora Industrial Sur", "lead_time_days": 10},
        ]

        suppliers = {}
        for data in suppliers_data:
            supplier, created = Supplier.all_objects.get_or_create(
                tenant=tenant,
                name=data["name"],
                defaults={
                    "tenant_id": tenant.id,
                    "lead_time_days": data["lead_time_days"],
                    "is_active": True,
                },
            )
            suppliers[data["name"]] = supplier
            status = "Created" if created else "Exists"
            self.stdout.write(f"  {status}: {supplier.name}")

        return suppliers

    def create_price_lists(self, tenant):
        """Create demo price lists."""
        self.stdout.write("Creating price lists...")
        price_lists_data = [
            {"name": "Lista General", "margin_pct": Decimal("30.00"), "is_default": True},
            {"name": "Mayorista", "margin_pct": Decimal("15.00"), "is_default": False},
            {"name": "VIP", "margin_pct": Decimal("25.00"), "is_default": False},
        ]

        price_lists = []
        for data in price_lists_data:
            pl, created = PriceList.all_objects.get_or_create(
                tenant=tenant,
                name=data["name"],
                defaults={
                    "tenant_id": tenant.id,
                    "margin_pct": data["margin_pct"],
                    "is_default": data["is_default"],
                },
            )
            price_lists.append(pl)
            status = "Created" if created else "Exists"
            self.stdout.write(f"  {status}: {pl.name}")

        return price_lists

    def create_products(self, tenant, categories, suppliers):
        """Create 100 hardware store products from SeedData.md specification."""
        self.stdout.write("Creating products (100 hardware store items)...")

        # All 100 products from SeedData.md with realistic Argentine prices (ARS)
        products_data = [
            # === Herramientas Eléctricas e Inalámbricas (1-20) ===
            {"sku": "HE-001", "name": "Taladro percutor 13mm DeWalt DWD024", "category": "Taladros y Rotomartillos", "supplier": "DeWalt Argentina", "cost": 89000, "price": 125000, "min": 5, "max": 25},
            {"sku": "HE-002", "name": "Atornillador impacto 18V Makita DTD152", "category": "Taladros y Rotomartillos", "supplier": "Makita Distribuidor", "cost": 145000, "price": 195000, "min": 4, "max": 20},
            {"sku": "HE-003", "name": "Amoladora angular 115mm Bosch GWS 700", "category": "Amoladoras y Sierras", "supplier": "Bosch Power Tools", "cost": 45000, "price": 65000, "min": 8, "max": 40},
            {"sku": "HE-004", "name": "Amoladora angular 230mm DeWalt DWE4579", "category": "Amoladoras y Sierras", "supplier": "DeWalt Argentina", "cost": 125000, "price": 175000, "min": 3, "max": 15},
            {"sku": "HE-005", "name": "Sierra circular 7-1/4 Makita 5007N", "category": "Amoladoras y Sierras", "supplier": "Makita Distribuidor", "cost": 98000, "price": 139000, "min": 4, "max": 20},
            {"sku": "HE-006", "name": "Sierra caladora Bosch GST 75 E", "category": "Amoladoras y Sierras", "supplier": "Bosch Power Tools", "cost": 78000, "price": 110000, "min": 5, "max": 25},
            {"sku": "HE-007", "name": "Lijadora orbital Makita BO4556", "category": "Lijadoras y Cepillos", "supplier": "Makita Distribuidor", "cost": 52000, "price": 75000, "min": 6, "max": 30},
            {"sku": "HE-008", "name": "Lijadora de banda Black+Decker DS321", "category": "Lijadoras y Cepillos", "supplier": "Stanley Black & Decker", "cost": 68000, "price": 95000, "min": 4, "max": 20},
            {"sku": "HE-009", "name": "Rotomartillo SDS Plus Bosch GBH 2-24", "category": "Taladros y Rotomartillos", "supplier": "Bosch Power Tools", "cost": 185000, "price": 259000, "min": 3, "max": 15},
            {"sku": "HE-010", "name": "Demoledor hexagonal Makita HM0870C", "category": "Taladros y Rotomartillos", "supplier": "Makita Distribuidor", "cost": 425000, "price": 595000, "min": 2, "max": 8},
            {"sku": "HE-011", "name": "Pistola de calor DeWalt D26411", "category": "Compresores y Equipos", "supplier": "DeWalt Argentina", "cost": 42000, "price": 59000, "min": 6, "max": 30},
            {"sku": "HE-012", "name": "Cepillo eléctrico Makita KP0800", "category": "Lijadoras y Cepillos", "supplier": "Makita Distribuidor", "cost": 115000, "price": 159000, "min": 3, "max": 15},
            {"sku": "HE-013", "name": "Fresadora Router Bosch GKF 550", "category": "Amoladoras y Sierras", "supplier": "Bosch Power Tools", "cost": 89000, "price": 125000, "min": 4, "max": 20},
            {"sku": "HE-014", "name": "Ingletadora compuesta DeWalt DWS780", "category": "Amoladoras y Sierras", "supplier": "DeWalt Argentina", "cost": 650000, "price": 895000, "min": 2, "max": 6},
            {"sku": "HE-015", "name": "Taladro de banco Truper 1/2 HP", "category": "Taladros y Rotomartillos", "supplier": "Truper Argentina", "cost": 185000, "price": 259000, "min": 2, "max": 8},
            {"sku": "HE-016", "name": "Esmeril de banco 6 pulgadas", "category": "Compresores y Equipos", "supplier": "Truper Argentina", "cost": 75000, "price": 105000, "min": 4, "max": 16},
            {"sku": "HE-017", "name": "Aspiradora industrial 30L Karcher", "category": "Compresores y Equipos", "supplier": "Importadora Industrial Sur", "cost": 165000, "price": 229000, "min": 3, "max": 12},
            {"sku": "HE-018", "name": "Compresor de aire 50L Lusqtoff", "category": "Compresores y Equipos", "supplier": "Lusqtoff S.A.", "cost": 245000, "price": 345000, "min": 2, "max": 10},
            {"sku": "HE-019", "name": "Hidrolavadora alta presión Karcher K3", "category": "Compresores y Equipos", "supplier": "Importadora Industrial Sur", "cost": 185000, "price": 259000, "min": 3, "max": 12},
            {"sku": "HE-020", "name": "Mezcladora pintura/cemento 1600W", "category": "Compresores y Equipos", "supplier": "Lusqtoff S.A.", "cost": 65000, "price": 92000, "min": 4, "max": 16},
            # === Herramientas Manuales (21-40) ===
            {"sku": "HM-021", "name": "Juego llaves combinadas 6-32mm Bremen", "category": "Llaves y Destornilladores", "supplier": "Bremen Tools", "cost": 45000, "price": 65000, "min": 8, "max": 40},
            {"sku": "HM-022", "name": "Juego destornilladores 12 piezas Stanley", "category": "Llaves y Destornilladores", "supplier": "Stanley Black & Decker", "cost": 18500, "price": 26000, "min": 12, "max": 60},
            {"sku": "HM-023", "name": "Destornilladores aislados 1000V x6", "category": "Llaves y Destornilladores", "supplier": "Stanley Black & Decker", "cost": 32000, "price": 45000, "min": 8, "max": 40},
            {"sku": "HM-024", "name": "Pinza universal 8 pulgadas Bremen", "category": "Pinzas y Alicates", "supplier": "Bremen Tools", "cost": 8500, "price": 12000, "min": 15, "max": 75},
            {"sku": "HM-025", "name": "Alicate corte diagonal 7 pulgadas", "category": "Pinzas y Alicates", "supplier": "Bremen Tools", "cost": 7200, "price": 10000, "min": 15, "max": 75},
            {"sku": "HM-026", "name": "Pinza pico de loro 10 pulgadas", "category": "Pinzas y Alicates", "supplier": "Bremen Tools", "cost": 12500, "price": 17500, "min": 12, "max": 60},
            {"sku": "HM-027", "name": "Llave ajustable francesa 10 Stanley", "category": "Llaves y Destornilladores", "supplier": "Stanley Black & Decker", "cost": 15000, "price": 21000, "min": 10, "max": 50},
            {"sku": "HM-028", "name": "Llave Stillson 14 pulgadas", "category": "Llaves y Destornilladores", "supplier": "Truper Argentina", "cost": 18000, "price": 25000, "min": 8, "max": 40},
            {"sku": "HM-029", "name": "Juego llaves Allen mm y pulgadas", "category": "Llaves y Destornilladores", "supplier": "Stanley Black & Decker", "cost": 8500, "price": 12000, "min": 15, "max": 75},
            {"sku": "HM-030", "name": "Juego llaves Torx T10-T50", "category": "Llaves y Destornilladores", "supplier": "Bremen Tools", "cost": 9500, "price": 13500, "min": 12, "max": 60},
            {"sku": "HM-031", "name": "Martillo galponero 500g Bremen", "category": "Martillos y Mazas", "supplier": "Bremen Tools", "cost": 8500, "price": 12000, "min": 15, "max": 75},
            {"sku": "HM-032", "name": "Martillo bolita mecánico 300g", "category": "Martillos y Mazas", "supplier": "Truper Argentina", "cost": 7500, "price": 10500, "min": 12, "max": 60},
            {"sku": "HM-033", "name": "Maza de goma 500g", "category": "Martillos y Mazas", "supplier": "Truper Argentina", "cost": 5500, "price": 7800, "min": 15, "max": 75},
            {"sku": "HM-034", "name": "Arco de sierra profesional 12", "category": "Medición y Corte", "supplier": "Stanley Black & Decker", "cost": 6500, "price": 9200, "min": 15, "max": 75},
            {"sku": "HM-035", "name": "Serrucho costilla 14 pulgadas", "category": "Medición y Corte", "supplier": "Truper Argentina", "cost": 8500, "price": 12000, "min": 12, "max": 60},
            {"sku": "HM-036", "name": "Cinta métrica 8m Stanley FatMax", "category": "Medición y Corte", "supplier": "Stanley Black & Decker", "cost": 12500, "price": 17500, "min": 20, "max": 100},
            {"sku": "HM-037", "name": "Nivel aluminio 60cm Stanley", "category": "Medición y Corte", "supplier": "Stanley Black & Decker", "cost": 18500, "price": 26000, "min": 10, "max": 50},
            {"sku": "HM-038", "name": "Escuadra carpintero 30cm", "category": "Medición y Corte", "supplier": "Truper Argentina", "cost": 4500, "price": 6500, "min": 15, "max": 75},
            {"sku": "HM-039", "name": "Cutter profesional 18mm Stanley", "category": "Medición y Corte", "supplier": "Stanley Black & Decker", "cost": 3500, "price": 5000, "min": 25, "max": 125},
            {"sku": "HM-040", "name": "Juego tubos y crique 40 piezas", "category": "Llaves y Destornilladores", "supplier": "Bremen Tools", "cost": 65000, "price": 92000, "min": 6, "max": 30},
            # === Maquinaria de Jardín y Agro (41-50) ===
            {"sku": "MJ-041", "name": "Tractor cortacésped 17.5HP", "category": "Corte de Césped", "supplier": "Importadora Industrial Sur", "cost": 2850000, "price": 3950000, "min": 1, "max": 3},
            {"sku": "MJ-042", "name": "Cortadora césped explosión 5.5HP", "category": "Corte de Césped", "supplier": "Lusqtoff S.A.", "cost": 285000, "price": 395000, "min": 2, "max": 8},
            {"sku": "MJ-043", "name": "Motosierra nafta 18 pulgadas Stihl", "category": "Poda y Mantenimiento", "supplier": "Importadora Industrial Sur", "cost": 425000, "price": 595000, "min": 2, "max": 8},
            {"sku": "MJ-044", "name": "Desmalezadora Motoguadaña 52cc", "category": "Poda y Mantenimiento", "supplier": "Lusqtoff S.A.", "cost": 165000, "price": 229000, "min": 3, "max": 12},
            {"sku": "MJ-045", "name": "Bordeadora eléctrica 700W", "category": "Poda y Mantenimiento", "supplier": "Lusqtoff S.A.", "cost": 45000, "price": 65000, "min": 5, "max": 25},
            {"sku": "MJ-046", "name": "Sopladora hojas 600W", "category": "Poda y Mantenimiento", "supplier": "Bosch Power Tools", "cost": 52000, "price": 73000, "min": 5, "max": 25},
            {"sku": "MJ-047", "name": "Cortasetos eléctrico 500W", "category": "Poda y Mantenimiento", "supplier": "Bosch Power Tools", "cost": 68000, "price": 95000, "min": 4, "max": 20},
            {"sku": "MJ-048", "name": "Hacha de mano 600g Truper", "category": "Poda y Mantenimiento", "supplier": "Truper Argentina", "cost": 12500, "price": 17500, "min": 10, "max": 50},
            {"sku": "MJ-049", "name": "Tijera podar bypass profesional", "category": "Poda y Mantenimiento", "supplier": "Truper Argentina", "cost": 8500, "price": 12000, "min": 15, "max": 75},
            {"sku": "MJ-050", "name": "Manguera riego reforzada 1/2 x 25m", "category": "Poda y Mantenimiento", "supplier": "Ferretería Mayorista Central", "cost": 18500, "price": 26000, "min": 10, "max": 50},
            # === Soldadura y Corte (51-60) ===
            {"sku": "SC-051", "name": "Soldadora Inverter 200A Lusqtoff", "category": "Soldadoras", "supplier": "Lusqtoff S.A.", "cost": 185000, "price": 259000, "min": 3, "max": 15},
            {"sku": "SC-052", "name": "Soldadora MIG-MAG 180A", "category": "Soldadoras", "supplier": "Lusqtoff S.A.", "cost": 425000, "price": 595000, "min": 2, "max": 8},
            {"sku": "SC-053", "name": "Máscara soldar fotosensible", "category": "Accesorios Soldadura", "supplier": "Lusqtoff S.A.", "cost": 32000, "price": 45000, "min": 8, "max": 40},
            {"sku": "SC-054", "name": "Torcha TIG/MIG 3m", "category": "Accesorios Soldadura", "supplier": "Ferretería Mayorista Central", "cost": 45000, "price": 63000, "min": 5, "max": 25},
            {"sku": "SC-055", "name": "Pinza porta electrodo 500A", "category": "Accesorios Soldadura", "supplier": "Ferretería Mayorista Central", "cost": 8500, "price": 12000, "min": 12, "max": 60},
            {"sku": "SC-056", "name": "Pinza de masa 500A", "category": "Accesorios Soldadura", "supplier": "Ferretería Mayorista Central", "cost": 6500, "price": 9200, "min": 12, "max": 60},
            {"sku": "SC-057", "name": "Electrodos punta azul 6013 x 5kg", "category": "Accesorios Soldadura", "supplier": "Ferretería Mayorista Central", "cost": 18500, "price": 26000, "min": 10, "max": 50},
            {"sku": "SC-058", "name": "Alambre soldar MIG 0.8mm x 5kg", "category": "Accesorios Soldadura", "supplier": "Ferretería Mayorista Central", "cost": 25000, "price": 35000, "min": 8, "max": 40},
            {"sku": "SC-059", "name": "Delantal cuero soldador", "category": "Accesorios Soldadura", "supplier": "Ferretería Mayorista Central", "cost": 12500, "price": 17500, "min": 10, "max": 50},
            {"sku": "SC-060", "name": "Escuadras magnéticas x4 soldadura", "category": "Accesorios Soldadura", "supplier": "Bremen Tools", "cost": 15000, "price": 21000, "min": 8, "max": 40},
            # === Insumos y Abrasivos (61-70) ===
            {"sku": "IA-061", "name": "Discos corte metal 115mm x 25 unid", "category": "Discos y Lijas", "supplier": "Ferretería Mayorista Central", "cost": 12500, "price": 17500, "min": 20, "max": 100},
            {"sku": "IA-062", "name": "Discos desbaste 115mm x 10 unid", "category": "Discos y Lijas", "supplier": "Ferretería Mayorista Central", "cost": 15000, "price": 21000, "min": 15, "max": 75},
            {"sku": "IA-063", "name": "Discos flap lija 115mm grano 80 x10", "category": "Discos y Lijas", "supplier": "3M Argentina", "cost": 18500, "price": 26000, "min": 15, "max": 75},
            {"sku": "IA-064", "name": "Disco diamantado 115mm concreto", "category": "Discos y Lijas", "supplier": "Bosch Power Tools", "cost": 15000, "price": 21000, "min": 12, "max": 60},
            {"sku": "IA-065", "name": "Juego mechas HSS 1-10mm x 19 piezas", "category": "Mechas y Puntas", "supplier": "Bosch Power Tools", "cost": 25000, "price": 35000, "min": 10, "max": 50},
            {"sku": "IA-066", "name": "Juego mechas widia pared x 8 piezas", "category": "Mechas y Puntas", "supplier": "Bosch Power Tools", "cost": 18500, "price": 26000, "min": 12, "max": 60},
            {"sku": "IA-067", "name": "Juego mechas paleta madera x 6", "category": "Mechas y Puntas", "supplier": "Bosch Power Tools", "cost": 15000, "price": 21000, "min": 10, "max": 50},
            {"sku": "IA-068", "name": "Mechas copa bimetal x 9 piezas", "category": "Mechas y Puntas", "supplier": "Bosch Power Tools", "cost": 32000, "price": 45000, "min": 6, "max": 30},
            {"sku": "IA-069", "name": "Set puntas atornillador 32 piezas", "category": "Mechas y Puntas", "supplier": "Bosch Power Tools", "cost": 8500, "price": 12000, "min": 15, "max": 75},
            {"sku": "IA-070", "name": "Lijas al agua surtidas x 50 hojas", "category": "Discos y Lijas", "supplier": "3M Argentina", "cost": 8500, "price": 12000, "min": 20, "max": 100},
            # === Seguridad Industrial EPP (71-80) ===
            {"sku": "SI-071", "name": "Zapatos seguridad punta acero", "category": "Protección Corporal", "supplier": "Importadora Industrial Sur", "cost": 45000, "price": 63000, "min": 10, "max": 50},
            {"sku": "SI-072", "name": "Guantes nitrilo caja x 100", "category": "Protección Personal", "supplier": "3M Argentina", "cost": 12500, "price": 17500, "min": 15, "max": 75},
            {"sku": "SI-073", "name": "Guantes cuero descarne par", "category": "Protección Personal", "supplier": "Ferretería Mayorista Central", "cost": 4500, "price": 6500, "min": 25, "max": 125},
            {"sku": "SI-074", "name": "Anteojos seguridad transparentes", "category": "Protección Personal", "supplier": "3M Argentina", "cost": 3500, "price": 5000, "min": 30, "max": 150},
            {"sku": "SI-075", "name": "Protectores auditivos tipo copa", "category": "Protección Personal", "supplier": "3M Argentina", "cost": 12500, "price": 17500, "min": 12, "max": 60},
            {"sku": "SI-076", "name": "Casco seguridad industrial", "category": "Protección Personal", "supplier": "3M Argentina", "cost": 8500, "price": 12000, "min": 15, "max": 75},
            {"sku": "SI-077", "name": "Chaleco reflectivo naranja", "category": "Protección Corporal", "supplier": "Ferretería Mayorista Central", "cost": 4500, "price": 6500, "min": 25, "max": 125},
            {"sku": "SI-078", "name": "Arnés seguridad 5 puntos", "category": "Protección Corporal", "supplier": "Importadora Industrial Sur", "cost": 65000, "price": 92000, "min": 4, "max": 20},
            {"sku": "SI-079", "name": "Respirador 3M media cara + filtros", "category": "Protección Personal", "supplier": "3M Argentina", "cost": 25000, "price": 35000, "min": 8, "max": 40},
            {"sku": "SI-080", "name": "Faja lumbar industrial", "category": "Protección Corporal", "supplier": "Ferretería Mayorista Central", "cost": 8500, "price": 12000, "min": 15, "max": 75},
            # === Fijaciones y Ferretería General (81-90) ===
            {"sku": "FF-081", "name": "Tornillos autoperforantes T1 x 1000", "category": "Tornillería", "supplier": "Ferretería Mayorista Central", "cost": 8500, "price": 12000, "min": 20, "max": 100},
            {"sku": "FF-082", "name": "Tornillos Fix madera surtidos x 500", "category": "Tornillería", "supplier": "Ferretería Mayorista Central", "cost": 6500, "price": 9200, "min": 20, "max": 100},
            {"sku": "FF-083", "name": "Tarugos nylon surtidos x 200", "category": "Tornillería", "supplier": "Ferretería Mayorista Central", "cost": 4500, "price": 6500, "min": 25, "max": 125},
            {"sku": "FF-084", "name": "Varilla roscada 3/8 x 1m", "category": "Tornillería", "supplier": "Ferretería Mayorista Central", "cost": 2500, "price": 3500, "min": 30, "max": 150},
            {"sku": "FF-085", "name": "Kit tuercas/arandelas zincadas x 200", "category": "Tornillería", "supplier": "Ferretería Mayorista Central", "cost": 5500, "price": 7800, "min": 20, "max": 100},
            {"sku": "FF-086", "name": "Bulones hexagonales surtidos x 100", "category": "Tornillería", "supplier": "Ferretería Mayorista Central", "cost": 8500, "price": 12000, "min": 15, "max": 75},
            {"sku": "FF-087", "name": "Remaches pop surtidos x 500", "category": "Fijaciones Varias", "supplier": "Ferretería Mayorista Central", "cost": 4500, "price": 6500, "min": 20, "max": 100},
            {"sku": "FF-088", "name": "Precintos plásticos surtidos x 500", "category": "Fijaciones Varias", "supplier": "Ferretería Mayorista Central", "cost": 3500, "price": 5000, "min": 25, "max": 125},
            {"sku": "FF-089", "name": "Cadena galvanizada 6mm x 10m", "category": "Fijaciones Varias", "supplier": "Ferretería Mayorista Central", "cost": 15000, "price": 21000, "min": 10, "max": 50},
            {"sku": "FF-090", "name": "Soga polipropileno 10mm x 50m", "category": "Fijaciones Varias", "supplier": "Ferretería Mayorista Central", "cost": 8500, "price": 12000, "min": 12, "max": 60},
            # === Químicos y Varios (91-100) ===
            {"sku": "QV-091", "name": "Adhesivo contacto Poxiran 450ml", "category": "Pegamentos y Selladores", "supplier": "Ferretería Mayorista Central", "cost": 5500, "price": 7800, "min": 20, "max": 100},
            {"sku": "QV-092", "name": "Silicona neutra transparente 280ml", "category": "Pegamentos y Selladores", "supplier": "3M Argentina", "cost": 4500, "price": 6500, "min": 25, "max": 125},
            {"sku": "QV-093", "name": "Espuma poliuretano expandido 750ml", "category": "Pegamentos y Selladores", "supplier": "Ferretería Mayorista Central", "cost": 6500, "price": 9200, "min": 20, "max": 100},
            {"sku": "QV-094", "name": "Cinta aisladora PVC x 10 rollos", "category": "Cintas y Lubricantes", "supplier": "3M Argentina", "cost": 5500, "price": 7800, "min": 25, "max": 125},
            {"sku": "QV-095", "name": "Cinta embalar 48mm x 6 rollos", "category": "Cintas y Lubricantes", "supplier": "Ferretería Mayorista Central", "cost": 4500, "price": 6500, "min": 25, "max": 125},
            {"sku": "QV-096", "name": "Cinta teflón 3/4 x 10 rollos", "category": "Cintas y Lubricantes", "supplier": "Ferretería Mayorista Central", "cost": 2500, "price": 3500, "min": 30, "max": 150},
            {"sku": "QV-097", "name": "Aceite lubricante WD-40 432ml", "category": "Cintas y Lubricantes", "supplier": "Importadora Industrial Sur", "cost": 8500, "price": 12000, "min": 20, "max": 100},
            {"sku": "QV-098", "name": "Pintura aerosol colores x 6 unid", "category": "Cintas y Lubricantes", "supplier": "Ferretería Mayorista Central", "cost": 15000, "price": 21000, "min": 15, "max": 75},
            {"sku": "QV-099", "name": "Escalera aluminio tijera 6 escalones", "category": "Fijaciones Varias", "supplier": "Importadora Industrial Sur", "cost": 85000, "price": 119000, "min": 4, "max": 16},
            {"sku": "QV-100", "name": "Caja herramientas plástica 20 pulg", "category": "Fijaciones Varias", "supplier": "Stanley Black & Decker", "cost": 32000, "price": 45000, "min": 8, "max": 40},
        ]

        products = []
        for data in products_data:
            product, created = Product.all_objects.get_or_create(
                tenant=tenant,
                sku=data["sku"],
                defaults={
                    "tenant_id": tenant.id,
                    "name": data["name"],
                    "unit_price": Decimal(str(data["price"])),
                    "cost_price": Decimal(str(data["cost"])),
                    "category": categories.get(data["category"]),
                    "supplier": suppliers.get(data["supplier"]),
                    "tax_rate": Decimal("21.00"),
                    "min_stock": Decimal(str(data["min"])),
                    "max_stock": Decimal(str(data["max"])),
                    "is_active": True,
                },
            )
            products.append(product)
            status = "Created" if created else "Exists"
            self.stdout.write(f"  {status}: {product.sku} - {product.name}")

        return products

    def create_stock_snapshots(self, products, branches):
        """Create initial stock snapshots."""
        self.stdout.write("Creating stock snapshots...")
        count = 0
        for product in products:
            for branch in branches:
                # Check if already exists
                existing = StockSnapshot.objects.filter(
                    product=product, branch=branch
                ).first()
                if existing:
                    continue

                # Random-ish initial stock based on min_stock
                initial_qty = (product.min_stock or Decimal("10")) * Decimal("3")

                StockSnapshot.objects.create(
                    product=product,
                    branch=branch,
                    quantity=initial_qty,
                    reserved_quantity=Decimal("0"),
                )
                count += 1

        self.stdout.write(f"  Created {count} stock snapshots")
