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

interface ARCACredential extends Record<string, unknown> {
  id: string;
  cuit_holder: string;
  cuit_represented: string | null;
  is_production: boolean;
  is_active: boolean;
  certificate_expires_at: string | null;
  created_at: string;
}

const formFields: FieldConfig[] = [
  { name: "cuit_holder", label: "CUIT Holder", type: "text", required: true, placeholder: "20123456789" },
  { name: "cuit_represented", label: "CUIT Represented (optional)", type: "text", placeholder: "Delegation model" },
  { name: "certificate_pem", label: "Certificate PEM", type: "textarea", required: true },
  { name: "private_key_pem", label: "Private Key PEM", type: "textarea", required: true },
  {
    name: "is_production",
    label: "Environment",
    type: "select",
    required: true,
    options: [
      { label: "Homologacion (testing)", value: "false" },
      { label: "Production", value: "true" },
    ],
  },
];

const columns: ColumnDef<ARCACredential>[] = [
  { key: "cuit_holder", header: "CUIT Holder" },
  { key: "cuit_represented", header: "CUIT Represented", render: (v) => (v as string | null) || "-" },
  {
    key: "is_production",
    header: "Environment",
    render: (v) => (v as boolean ? "Production" : "Homologacion"),
  },
  {
    key: "is_active",
    header: "Status",
    render: (v) => <StatusBadge status={v as boolean ? "active" : "inactive"} />,
  },
  {
    key: "certificate_expires_at",
    header: "Cert Expires",
    render: (v) => (v as string | null) ? (v as string).slice(0, 10) : "-",
  },
  { key: "created_at", header: "Created", render: (v) => (v as string).slice(0, 10) },
];

export function CredentialsTab() {
  const queryClient = useQueryClient();
  const { data, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage, error } =
    usePagination<ARCACredential>("/api/v1/facturacion/credentials/");

  const [showForm, setShowForm] = useState(false);
  const [formErrors, setFormErrors] = useState<Record<string, string[]>>({});
  const [isCreating, setIsCreating] = useState(false);

  async function handleCreate(values: Record<string, string>) {
    setFormErrors({});
    setIsCreating(true);
    try {
      await apiClient("/api/v1/facturacion/credentials/", {
        method: "POST",
        body: {
          cuit_holder: values.cuit_holder,
          cuit_represented: values.cuit_represented || null,
          certificate_pem: values.certificate_pem,
          private_key_pem: values.private_key_pem,
          is_production: values.is_production === "true",
        },
      });
      setShowForm(false);
      void queryClient.invalidateQueries({ queryKey: ["/api/v1/facturacion/credentials/"] });
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
          {showForm ? "Cancel" : "New Credential"}
        </Button>
      </div>
      {showForm ? (
        <CrudForm
          fields={formFields}
          mode="create"
          title="Register ARCA Credential"
          onSubmit={handleCreate}
          errors={formErrors}
          isLoading={isCreating}
        />
      ) : null}
      {error ? (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : "Failed to load credentials"}
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
      {data.length > 0 ? <RawJsonToggle data={data} label="Credentials JSON" /> : null}
    </div>
  );
}
