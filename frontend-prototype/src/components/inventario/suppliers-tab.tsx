"use client";

import { useState } from "react";
import { usePagination } from "@/hooks/use-pagination";
import { apiClient, ApiError } from "@/lib/api-client";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { CrudForm, type FieldConfig } from "@/components/crud-form";
import { StatusBadge } from "@/components/status-badge";
import { RawJsonToggle } from "@/components/raw-json-toggle";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useQueryClient } from "@tanstack/react-query";

interface Supplier extends Record<string, unknown> {
  id: string;
  name: string;
  tax_id: string | null;
  email: string | null;
  contact_info: string | null;
  address: string | null;
  is_active: boolean;
}

const formFields: FieldConfig[] = [
  { name: "name", label: "Name", type: "text", required: true },
  { name: "tax_id", label: "Tax ID (CUIT)", type: "text" },
  { name: "email", label: "Email", type: "email" },
  { name: "contact_info", label: "Contact Info", type: "text" },
  { name: "address", label: "Address", type: "textarea" },
];

const columns: ColumnDef<Supplier>[] = [
  { key: "name", header: "Name" },
  { key: "tax_id", header: "Tax ID", render: (v) => (v as string | null) ?? "-" },
  { key: "email", header: "Email", render: (v) => (v as string | null) ?? "-" },
  {
    key: "is_active",
    header: "Status",
    render: (v) => <StatusBadge status={v as boolean ? "active" : "inactive"} />,
  },
];

export function SuppliersTab() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const params = search ? { q: search } : undefined;
  const { data, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage, error } =
    usePagination<Supplier>(
      search ? "/api/v1/suppliers/search/" : "/api/v1/suppliers/",
      params,
    );

  const [showForm, setShowForm] = useState(false);
  const [formErrors, setFormErrors] = useState<Record<string, string[]>>({});
  const [isCreating, setIsCreating] = useState(false);

  async function handleCreate(values: Record<string, string>) {
    setFormErrors({});
    setIsCreating(true);
    try {
      await apiClient("/api/v1/suppliers/", {
        method: "POST",
        body: {
          name: values.name,
          tax_id: values.tax_id || null,
          email: values.email || null,
          contact_info: values.contact_info || null,
          address: values.address || null,
        },
      });
      setShowForm(false);
      void queryClient.invalidateQueries({ queryKey: ["/api/v1/suppliers/"] });
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
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <Input
          placeholder="Search suppliers..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
        />
        <Button size="sm" onClick={() => { setShowForm((v) => !v); setFormErrors({}); }}>
          {showForm ? "Cancel" : "New Supplier"}
        </Button>
      </div>
      {showForm ? (
        <CrudForm
          fields={formFields}
          mode="create"
          title="Create Supplier"
          onSubmit={handleCreate}
          errors={formErrors}
          isLoading={isCreating}
        />
      ) : null}
      {error ? (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : "Failed to load suppliers"}
        </p>
      ) : null}
      <DataTable
        columns={columns}
        data={data}
        isLoading={isLoading}
        hasNextPage={hasNextPage}
        onLoadMore={() => void fetchNextPage()}
        isFetchingNextPage={isFetchingNextPage}
      />
      {data.length > 0 ? <RawJsonToggle data={data} label="Suppliers JSON" /> : null}
    </div>
  );
}
