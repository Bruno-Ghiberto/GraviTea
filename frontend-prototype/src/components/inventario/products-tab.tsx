"use client";

import { useState } from "react";
import { usePagination } from "@/hooks/use-pagination";
import { apiClient, ApiError } from "@/lib/api-client";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { CrudForm, type FieldConfig } from "@/components/crud-form";
import { StatusBadge } from "@/components/status-badge";
import { RawJsonToggle } from "@/components/raw-json-toggle";
import { Button } from "@/components/ui/button";
import { useQueryClient } from "@tanstack/react-query";
import { DynamicFields } from "@/components/inventario/dynamic-fields";

interface Product extends Record<string, unknown> {
  id: string;
  sku: string;
  name: string;
  barcode: string | null;
  description: string | null;
  category_name: string | null;
  supplier_name: string | null;
  cost_price: string | null;
  is_active: boolean;
}

const formFields: FieldConfig[] = [
  { name: "sku", label: "SKU", type: "text", required: true, placeholder: "PROD-001" },
  { name: "name", label: "Name", type: "text", required: true },
  { name: "barcode", label: "Barcode", type: "text" },
  { name: "description", label: "Description", type: "textarea" },
  { name: "cost_price", label: "Cost Price", type: "number", placeholder: "0.00" },
];

export function ProductsTab() {
  const queryClient = useQueryClient();
  const { data, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage, error } =
    usePagination<Product>("/api/v1/products/");

  const [showForm, setShowForm] = useState(false);
  const [formErrors, setFormErrors] = useState<Record<string, string[]>>({});
  const [isCreating, setIsCreating] = useState(false);
  const [customData, setCustomData] = useState<Record<string, unknown>>({});

  const columns: ColumnDef<Product>[] = [
    { key: "sku", header: "SKU" },
    { key: "name", header: "Name" },
    {
      key: "category_name",
      header: "Category",
      render: (v) => (v as string | null) ?? "-",
    },
    {
      key: "supplier_name",
      header: "Supplier",
      render: (v) => (v as string | null) ?? "-",
    },
    {
      key: "cost_price",
      header: "Cost",
      render: (v) => (v != null ? `$${v}` : "-"),
    },
    {
      key: "is_active",
      header: "Status",
      render: (v) => <StatusBadge status={v as boolean ? "active" : "inactive"} />,
    },
  ];

  async function handleCreate(values: Record<string, string>) {
    setFormErrors({});
    setIsCreating(true);
    try {
      await apiClient("/api/v1/products/", {
        method: "POST",
        body: {
          sku: values.sku,
          name: values.name,
          barcode: values.barcode || null,
          description: values.description || null,
          cost_price: values.cost_price || null,
          custom_data: Object.keys(customData).length > 0 ? customData : undefined,
        },
      });
      setShowForm(false);
      setCustomData({});
      void queryClient.invalidateQueries({ queryKey: ["/api/v1/products/"] });
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
      <div className="flex justify-end">
        <Button size="sm" onClick={() => { setShowForm((v) => !v); setFormErrors({}); setCustomData({}); }}>
          {showForm ? "Cancel" : "New Product"}
        </Button>
      </div>
      {showForm ? (
        <div className="space-y-4">
          <CrudForm
            fields={formFields}
            mode="create"
            title="Create Product"
            onSubmit={handleCreate}
            errors={formErrors}
            isLoading={isCreating}
          />
          <DynamicFields
            onChange={setCustomData}
            errors={
              formErrors.custom_data && typeof formErrors.custom_data === "object" && !Array.isArray(formErrors.custom_data)
                ? (formErrors.custom_data as unknown as Record<string, string[]>)
                : undefined
            }
          />
        </div>
      ) : null}
      {error ? (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : "Failed to load products"}
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
      {data.length > 0 ? <RawJsonToggle data={data} label="Products JSON" /> : null}
    </div>
  );
}
