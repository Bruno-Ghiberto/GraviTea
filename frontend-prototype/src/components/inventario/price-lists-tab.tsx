"use client";

import { useState } from "react";
import { useCrud } from "@/hooks/use-crud";
import { apiClient, ApiError } from "@/lib/api-client";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { CrudForm, type FieldConfig } from "@/components/crud-form";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { StatusBadge } from "@/components/status-badge";
import { RawJsonToggle } from "@/components/raw-json-toggle";
import { Button } from "@/components/ui/button";

interface PriceList extends Record<string, unknown> {
  id: string;
  name: string;
  margin_pct: string | null;
  is_default: boolean;
  created_at: string;
}

const formFields: FieldConfig[] = [
  { name: "name", label: "Name", type: "text", required: true, placeholder: "e.g. Retail, Wholesale" },
  { name: "margin_pct", label: "Margin %", type: "number", placeholder: "15.00" },
];

export function PriceListsTab() {
  const { items, isLoading, create, update, remove, isCreating, isUpdating, isRemoving, refetch } =
    useCrud<PriceList>("/api/v1/price-lists/");

  const [showForm, setShowForm] = useState(false);
  const [editingItem, setEditingItem] = useState<PriceList | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [formErrors, setFormErrors] = useState<Record<string, string[]>>({});
  const [settingDefault, setSettingDefault] = useState<string | null>(null);

  const columns: ColumnDef<PriceList>[] = [
    { key: "name", header: "Name" },
    { key: "margin_pct", header: "Margin %", render: (v) => (v != null ? `${v}%` : "-") },
    {
      key: "is_default",
      header: "Default",
      render: (v) => (v as boolean ? <StatusBadge status="active" /> : <span className="text-muted-foreground">-</span>),
    },
    { key: "created_at", header: "Created" },
    {
      key: "id",
      header: "Actions",
      render: (_v, row) => (
        <div className="flex gap-2">
          {!row.is_default ? (
            <Button
              variant="outline"
              size="sm"
              disabled={settingDefault === row.id}
              onClick={() => void handleSetDefault(row.id)}
            >
              {settingDefault === row.id ? "..." : "Set Default"}
            </Button>
          ) : null}
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setEditingItem(row);
              setShowForm(true);
              setFormErrors({});
            }}
          >
            Edit
          </Button>
          <Button variant="destructive" size="sm" onClick={() => setDeletingId(row.id)}>
            Delete
          </Button>
        </div>
      ),
    },
  ];

  async function handleSetDefault(id: string) {
    setSettingDefault(id);
    try {
      await apiClient(`/api/v1/price-lists/${id}/set_default/`, { method: "POST" });
      void refetch();
    } finally {
      setSettingDefault(null);
    }
  }

  async function handleSubmit(values: Record<string, string>) {
    setFormErrors({});
    const payload = {
      name: values.name,
      margin_pct: values.margin_pct || null,
    };

    try {
      if (editingItem) {
        await update({ id: editingItem.id, data: payload as unknown as Partial<PriceList> });
      } else {
        await create(payload as unknown as Partial<PriceList>);
      }
      setShowForm(false);
      setEditingItem(null);
    } catch (err) {
      if (err instanceof ApiError && err.body && typeof err.body === "object") {
        const body = err.body as Record<string, unknown>;
        if (body.errors && Array.isArray(body.errors)) {
          const fe: Record<string, string[]> = {};
          for (const e of body.errors as { field: string; message: string }[]) {
            const existing = fe[e.field] ?? [];
            existing.push(e.message);
            fe[e.field] = existing;
          }
          setFormErrors(fe);
        }
      }
    }
  }

  async function handleDelete() {
    if (!deletingId) return;
    try {
      await remove(deletingId);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button
          size="sm"
          onClick={() => {
            setEditingItem(null);
            setShowForm((v) => !v);
            setFormErrors({});
          }}
        >
          {showForm ? "Cancel" : "New Price List"}
        </Button>
      </div>
      {showForm ? (
        <CrudForm
          fields={formFields}
          mode={editingItem ? "edit" : "create"}
          title={editingItem ? `Edit: ${editingItem.name}` : "Create Price List"}
          initialValues={
            editingItem
              ? { name: editingItem.name, margin_pct: editingItem.margin_pct ?? "" }
              : undefined
          }
          onSubmit={handleSubmit}
          errors={formErrors}
          isLoading={isCreating || isUpdating}
        />
      ) : null}
      <DataTable columns={columns} data={items} isLoading={isLoading} />
      {items.length > 0 ? <RawJsonToggle data={items} label="Price Lists JSON" /> : null}
      <ConfirmDialog
        open={deletingId !== null}
        title="Delete Price List"
        description="Are you sure? This will permanently delete this price list."
        onConfirm={() => void handleDelete()}
        onCancel={() => setDeletingId(null)}
        isLoading={isRemoving}
      />
    </div>
  );
}
