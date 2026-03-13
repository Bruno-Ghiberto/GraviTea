"use client";

import { useState } from "react";
import { useCrud } from "@/hooks/use-crud";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { CrudForm, type FieldConfig } from "@/components/crud-form";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { RawJsonToggle } from "@/components/raw-json-toggle";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";

interface Role extends Record<string, unknown> {
  id: string;
  name: string;
  permissions: string[];
  created_at: string;
}

const formFields: FieldConfig[] = [
  {
    name: "name",
    label: "Role Name",
    type: "text",
    required: true,
    placeholder: "e.g. Vendedor, Gerente",
  },
  {
    name: "permissions",
    label: "Permissions (comma-separated)",
    type: "textarea",
    placeholder: "users.view, sales.create, reports.view",
  },
];

export function RolesTab() {
  const { items, isLoading, create, update, remove, isCreating, isUpdating, isRemoving, refetch } =
    useCrud<Role>("/api/v1/auth/roles/");

  const [showForm, setShowForm] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [formErrors, setFormErrors] = useState<Record<string, string[]>>({});

  const columns: ColumnDef<Role>[] = [
    { key: "name", header: "Name" },
    {
      key: "permissions",
      header: "Permissions",
      render: (v) => {
        const perms = v as string[];
        if (!perms || perms.length === 0) return "-";
        return perms.length <= 3
          ? perms.join(", ")
          : `${perms.slice(0, 3).join(", ")} +${perms.length - 3}`;
      },
    },
    { key: "created_at", header: "Created" },
    {
      key: "id",
      header: "Actions",
      render: (_v, row) => (
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setEditingRole(row);
              setShowForm(true);
              setFormErrors({});
            }}
          >
            Edit
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setDeletingId(row.id)}
          >
            Delete
          </Button>
        </div>
      ),
    },
  ];

  async function handleSubmit(values: Record<string, string>) {
    setFormErrors({});
    const payload = {
      name: values.name,
      permissions: values.permissions
        ? values.permissions.split(",").map((s) => s.trim()).filter(Boolean)
        : [],
    };

    try {
      if (editingRole) {
        await update({ id: editingRole.id, data: payload as unknown as Partial<Role> });
      } else {
        await create(payload as unknown as Partial<Role>);
      }
      setShowForm(false);
      setEditingRole(null);
    } catch (err) {
      if (err instanceof ApiError && err.body && typeof err.body === "object") {
        const body = err.body as Record<string, unknown>;
        if (body.errors && Array.isArray(body.errors)) {
          const fieldErrors: Record<string, string[]> = {};
          for (const e of body.errors as { field: string; message: string }[]) {
            const existing = fieldErrors[e.field] ?? [];
            existing.push(e.message);
            fieldErrors[e.field] = existing;
          }
          setFormErrors(fieldErrors);
        }
      }
    }
  }

  async function handleDelete() {
    if (!deletingId) return;
    try {
      await remove(deletingId);
      setDeletingId(null);
    } catch {
      setDeletingId(null);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button
          size="sm"
          onClick={() => {
            setEditingRole(null);
            setShowForm((v) => !v);
            setFormErrors({});
          }}
        >
          {showForm ? "Cancel" : "New Role"}
        </Button>
      </div>

      {showForm ? (
        <CrudForm
          fields={formFields}
          mode={editingRole ? "edit" : "create"}
          title={editingRole ? `Edit: ${editingRole.name}` : "Create Role"}
          initialValues={
            editingRole
              ? {
                  name: editingRole.name,
                  permissions: editingRole.permissions.join(", "),
                }
              : undefined
          }
          onSubmit={handleSubmit}
          errors={formErrors}
          isLoading={isCreating || isUpdating}
        />
      ) : null}

      <DataTable
        columns={columns}
        data={items}
        isLoading={isLoading}
      />

      {items.length > 0 ? (
        <RawJsonToggle data={items} label="Roles JSON" />
      ) : null}

      <ConfirmDialog
        open={deletingId !== null}
        title="Delete Role"
        description="Are you sure? This role will be permanently deleted. Users assigned to this role must be reassigned first."
        onConfirm={() => void handleDelete()}
        onCancel={() => setDeletingId(null)}
        isLoading={isRemoving}
      />
    </div>
  );
}
