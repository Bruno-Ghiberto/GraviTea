"""
Module-level permission classes for Gravitea ERP.

Provides HasModulePermission base class that checks user's role
permissions against module.action pairs based on the HTTP method.
"""

from __future__ import annotations

from rest_framework.permissions import BasePermission, IsAuthenticated


class HasModulePermission(BasePermission):
    """
    Check that the authenticated user's role has the required module permission.

    Usage on ViewSets::

        class MyViewSet(viewsets.ModelViewSet):
            permission_classes = [IsAuthenticated, HasModulePermission]
            module_name = "purchases"  # matches Role.VALID_MODULES

    Method → action mapping:
        GET (list/retrieve)  → {module}.read
        POST (create)        → {module}.write
        PUT/PATCH (update)   → {module}.write
        DELETE               → {module}.admin

    Override `get_required_permission()` for custom action mappings.
    """

    # Default method-to-action mapping
    METHOD_ACTION_MAP = {
        "GET": "read",
        "HEAD": "read",
        "OPTIONS": "read",
        "POST": "write",
        "PUT": "write",
        "PATCH": "write",
        "DELETE": "admin",
    }

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        module = getattr(view, "module_name", None)
        if module is None:
            return True  # No module_name set — skip module permission check

        required_permission = self.get_required_permission(request, view, module)
        if required_permission is None:
            return True  # No permission required for this action

        role = getattr(request.user, "role", None)
        if role is None:
            return False  # No role assigned — deny

        return role.has_permission(required_permission)

    def get_required_permission(self, request, view, module: str) -> str | None:
        """
        Determine the required permission string for this request.

        Override in subclasses or set `action_permissions` on the view::

            class MyViewSet(viewsets.ModelViewSet):
                module_name = "reports"
                action_permissions = {
                    "create": "reports.export",  # custom action mapping
                }
        """
        # Check view-level action_permissions override first
        action_permissions = getattr(view, "action_permissions", {})
        view_action = getattr(view, "action", None)

        if view_action and view_action in action_permissions:
            return action_permissions[view_action]

        # Fall back to method-based mapping
        action = self.METHOD_ACTION_MAP.get(request.method)
        if action is None:
            return None

        return f"{module}.{action}"
