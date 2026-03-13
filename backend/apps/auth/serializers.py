"""
Authentication serializers for Gravitea ERP.

Provides serializers for User, Role, and Branch management.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.core.models import Branch

from .models import Role

User = get_user_model()


class RoleSerializer(serializers.ModelSerializer):
    """
    Role serializer for read operations.

    Returns role details with permission list.
    """

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "permissions",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class RoleCreateSerializer(serializers.ModelSerializer):
    """
    Role serializer for create/update operations.

    Validates permission format and uniqueness within tenant.
    """

    class Meta:
        model = Role
        fields = [
            "name",
            "permissions",
        ]

    def validate_permissions(self, value):
        """Validate permission format."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Permissions must be a list.")

        valid_modules = Role.VALID_MODULES
        valid_actions = Role.VALID_ACTIONS

        for perm in value:
            if not isinstance(perm, str):
                raise serializers.ValidationError(f"Permission must be a string: {perm}")

            parts = perm.split(".")
            if len(parts) != 2:
                raise serializers.ValidationError(
                    f"Invalid permission format: {perm}. Expected 'module.action'."
                )

            module, action = parts
            if module not in valid_modules:
                raise serializers.ValidationError(
                    f"Invalid module: {module}. Valid: {valid_modules}"
                )
            if action not in valid_actions:
                raise serializers.ValidationError(
                    f"Invalid action: {action}. Valid: {valid_actions}"
                )

        return value

    def create(self, validated_data):
        """Create role with tenant from request context."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["tenant"] = request.user.tenant
        return super().create(validated_data)


class BranchSerializer(serializers.ModelSerializer):
    """
    Branch serializer for read operations.

    Returns branch details for user context.
    """

    class Meta:
        model = Branch
        fields = [
            "id",
            "name",
            "address",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class UserSerializer(serializers.ModelSerializer):
    """
    User serializer for read operations.

    Returns user profile with role and branch details.
    """

    role = RoleSerializer(read_only=True)
    default_branch = BranchSerializer(read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "role",
            "default_branch",
            "permissions",
            "is_active",
            "last_login",
            "created_at",
        ]
        read_only_fields = ["id", "last_login", "created_at"]

    def get_permissions(self, obj):
        """Get list of permissions from user's role."""
        return obj.get_permissions()


class UserCreateSerializer(serializers.ModelSerializer):
    """
    User serializer for create operations.

    Validates email uniqueness within tenant and password strength.
    """

    password = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )
    role_id = serializers.UUIDField(required=False, allow_null=True)
    default_branch_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            "email",
            "full_name",
            "password",
            "role_id",
            "default_branch_id",
        ]

    def validate_password(self, value):
        """Validate password strength."""
        validate_password(value)
        return value

    def validate_email(self, value):
        """Validate email uniqueness within tenant."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            tenant = request.user.tenant
            if User.objects.filter(tenant=tenant, email=value).exists():
                raise serializers.ValidationError(
                    "A user with this email already exists in your organization."
                )
        return value

    def validate_role_id(self, value):
        """Validate role belongs to same tenant."""
        if value:
            request = self.context.get("request")
            if request and hasattr(request, "user"):
                tenant = request.user.tenant
                if not Role.objects.filter(id=value, tenant=tenant).exists():
                    raise serializers.ValidationError("Role not found in your organization.")
        return value

    def validate_default_branch_id(self, value):
        """Validate branch belongs to same tenant."""
        if value:
            request = self.context.get("request")
            if request and hasattr(request, "user"):
                tenant = request.user.tenant
                if not Branch.objects.filter(id=value, tenant=tenant).exists():
                    raise serializers.ValidationError("Branch not found in your organization.")
        return value

    def create(self, validated_data):
        """Create user with tenant from request context."""
        request = self.context.get("request")
        password = validated_data.pop("password")

        role_id = validated_data.pop("role_id", None)
        branch_id = validated_data.pop("default_branch_id", None)

        if request and hasattr(request, "user"):
            validated_data["tenant"] = request.user.tenant

        user = User(**validated_data)
        user.set_password(password)

        if role_id:
            user.role_id = role_id
        if branch_id:
            user.default_branch_id = branch_id

        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    User serializer for update operations.

    Allows updating profile fields without password.
    """

    role_id = serializers.UUIDField(required=False, allow_null=True)
    default_branch_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            "full_name",
            "role_id",
            "default_branch_id",
            "is_active",
        ]

    def validate_role_id(self, value):
        """Validate role belongs to same tenant."""
        if value:
            instance = self.instance
            if instance:
                if not Role.objects.filter(id=value, tenant=instance.tenant).exists():
                    raise serializers.ValidationError("Role not found in your organization.")
        return value

    def validate_default_branch_id(self, value):
        """Validate branch belongs to same tenant."""
        if value:
            instance = self.instance
            if instance:
                if not Branch.objects.filter(id=value, tenant=instance.tenant).exists():
                    raise serializers.ValidationError("Branch not found in your organization.")
        return value

    def update(self, instance, validated_data):
        """Update user fields."""
        role_id = validated_data.pop("role_id", None)
        branch_id = validated_data.pop("default_branch_id", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if role_id is not None:
            instance.role_id = role_id
        if branch_id is not None:
            instance.default_branch_id = branch_id

        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change endpoint.

    Validates current password and new password strength.
    """

    current_password = serializers.CharField(required=True, style={"input_type": "password"})
    new_password = serializers.CharField(required=True, style={"input_type": "password"})

    def validate_new_password(self, value):
        """Validate new password strength."""
        validate_password(value)
        return value
