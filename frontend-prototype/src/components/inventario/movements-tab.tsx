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

interface Movement extends Record<string, unknown> {
  id: string;
  product_sku: string;
  product_name: string;
  branch_name: string;
  type: string;
  quantity_delta: string;
  notes: string | null;
  created_at: string;
}

const formFields: FieldConfig[] = [
  { name: "product", label: "Product ID (UUID)", type: "text", required: true },
  { name: "branch", label: "Branch ID (UUID)", type: "text", required: true },
  {
    name: "type",
    label: "Movement Type",
    type: "select",
    required: true,
    options: [
      { label: "Sale", value: "SALE" },
      { label: "Purchase", value: "PURCHASE" },
      { label: "Adjustment", value: "ADJ" },
      { label: "Transfer In", value: "TRANS_IN" },
      { label: "Transfer Out", value: "TRANS_OUT" },
    ],
  },
  { name: "quantity_delta", label: "Quantity", type: "number", required: true },
  { name: "notes", label: "Notes", type: "textarea" },
];

const TYPE_VARIANT: Record<string, "success" | "warning" | "error" | "default"> = {
  PURCHASE: "success",
  TRANS_IN: "success",
  SALE: "warning",
  TRANS_OUT: "warning",
  ADJ: "default",
};

const columns: ColumnDef<Movement>[] = [
  { key: "product_sku", header: "SKU" },
  { key: "product_name", header: "Product" },
  { key: "branch_name", header: "Branch" },
  {
    key: "type",
    header: "Type",
    render: (v) => {
      const t = v as string;
      return <StatusBadge status={t} variant={TYPE_VARIANT[t]} />;
    },
  },
  { key: "quantity_delta", header: "Qty" },
  { key: "created_at", header: "Date" },
];

export function MovementsTab() {
  const queryClient = useQueryClient();
  const { data, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage, error } =
    usePagination<Movement>("/api/v1/movements/");

  const [showForm, setShowForm] = useState(false);
  const [formErrors, setFormErrors] = useState<Record<string, string[]>>({});
  const [isCreating, setIsCreating] = useState(false);

  async function handleCreate(values: Record<string, string>) {
    setFormErrors({});
    setIsCreating(true);
    try {
      await apiClient("/api/v1/movements/", {
        method: "POST",
        body: {
          product: values.product,
          branch: values.branch,
          type: values.type,
          quantity_delta: values.quantity_delta,
          notes: values.notes || null,
        },
      });
      setShowForm(false);
      void queryClient.invalidateQueries({ queryKey: ["/api/v1/movements/"] });
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
        <Button size="sm" onClick={() => { setShowForm((v) => !v); setFormErrors({}); }}>
          {showForm ? "Cancel" : "New Movement"}
        </Button>
      </div>
      {showForm ? (
        <CrudForm
          fields={formFields}
          mode="create"
          title="Record Stock Movement"
          onSubmit={handleCreate}
          errors={formErrors}
          isLoading={isCreating}
        />
      ) : null}
      {error ? (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : "Failed to load movements"}
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
      {data.length > 0 ? <RawJsonToggle data={data} label="Movements JSON" /> : null}
    </div>
  );
}
