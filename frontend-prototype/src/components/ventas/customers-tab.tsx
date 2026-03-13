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

interface Customer extends Record<string, unknown> {
  id: string;
  cuit: string;
  razon_social: string;
  condicion_iva_display: string;
  email: string;
  telefono: string;
  is_active: boolean;
}

const formFields: FieldConfig[] = [
  { name: "cuit", label: "CUIT", type: "text", required: true, placeholder: "20123456789" },
  { name: "razon_social", label: "Razon Social", type: "text", required: true },
  {
    name: "doc_tipo",
    label: "Doc Type",
    type: "select",
    required: true,
    options: [
      { label: "CUIT (80)", value: "80" },
      { label: "DNI (96)", value: "96" },
      { label: "Consumidor Final (99)", value: "99" },
    ],
  },
  {
    name: "condicion_iva",
    label: "IVA Condition",
    type: "select",
    required: true,
    options: [
      { label: "IVA Responsable Inscripto (1)", value: "1" },
      { label: "IVA Sujeto Exento (4)", value: "4" },
      { label: "Consumidor Final (5)", value: "5" },
      { label: "Responsable Monotributo (6)", value: "6" },
    ],
  },
  { name: "domicilio", label: "Address", type: "text" },
  { name: "email", label: "Email", type: "email" },
  { name: "telefono", label: "Phone", type: "text" },
];

const columns: ColumnDef<Customer>[] = [
  { key: "cuit", header: "CUIT" },
  { key: "razon_social", header: "Name" },
  { key: "condicion_iva_display", header: "IVA Condition" },
  { key: "email", header: "Email", render: (v) => (v as string) || "-" },
  {
    key: "is_active",
    header: "Status",
    render: (v) => <StatusBadge status={v as boolean ? "active" : "inactive"} />,
  },
];

export function CustomersTab() {
  const queryClient = useQueryClient();
  const { data, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage, error } =
    usePagination<Customer>("/api/v1/ventas/customers/");

  const [showForm, setShowForm] = useState(false);
  const [formErrors, setFormErrors] = useState<Record<string, string[]>>({});
  const [isCreating, setIsCreating] = useState(false);

  async function handleCreate(values: Record<string, string>) {
    setFormErrors({});
    setIsCreating(true);
    try {
      await apiClient("/api/v1/ventas/customers/", {
        method: "POST",
        body: {
          cuit: values.cuit,
          razon_social: values.razon_social,
          doc_tipo: Number(values.doc_tipo),
          condicion_iva: Number(values.condicion_iva),
          domicilio: values.domicilio || "",
          email: values.email || "",
          telefono: values.telefono || "",
        },
      });
      setShowForm(false);
      void queryClient.invalidateQueries({ queryKey: ["/api/v1/ventas/customers/"] });
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
          {showForm ? "Cancel" : "New Customer"}
        </Button>
      </div>
      {showForm ? (
        <CrudForm
          fields={formFields}
          mode="create"
          title="Create Customer"
          onSubmit={handleCreate}
          errors={formErrors}
          isLoading={isCreating}
        />
      ) : null}
      {error ? (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : "Failed to load customers"}
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
      {data.length > 0 ? <RawJsonToggle data={data} label="Customers JSON" /> : null}
    </div>
  );
}
