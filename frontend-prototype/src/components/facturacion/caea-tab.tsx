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

interface CAEA extends Record<string, unknown> {
  id: string;
  punto_venta: string;
  punto_venta_numero: number;
  caea_code: string;
  periodo: string;
  orden: number;
  fch_vig_desde: string;
  fch_vig_hasta: string;
  fch_tope_inf: string;
  status: string;
  created_at: string;
}

const STATUS_VARIANT: Record<string, "warning" | "success" | "default"> = {
  ACTIVE: "success",
  REPORTED: "default",
  REPORTED_NO_MOVEMENT: "default",
  EXPIRED: "warning",
};

const solicitarFields: FieldConfig[] = [
  { name: "punto_venta", label: "Punto de Venta ID (UUID)", type: "text", required: true },
  { name: "periodo", label: "Period (YYYYMM)", type: "text", required: true, placeholder: "202602" },
  {
    name: "orden",
    label: "Quincena",
    type: "select",
    required: true,
    options: [
      { label: "1st (1-15)", value: "1" },
      { label: "2nd (16-end)", value: "2" },
    ],
  },
];

export function CAEATab() {
  const queryClient = useQueryClient();
  const { data, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage, error } =
    usePagination<CAEA>("/api/v1/facturacion/caeas/");

  const [showForm, setShowForm] = useState(false);
  const [formErrors, setFormErrors] = useState<Record<string, string[]>>({});
  const [isRequesting, setIsRequesting] = useState(false);
  const [reportingId, setReportingId] = useState<string | null>(null);

  const columns: ColumnDef<CAEA>[] = [
    { key: "punto_venta_numero", header: "PtoVta" },
    { key: "caea_code", header: "CAEA Code" },
    { key: "periodo", header: "Period" },
    { key: "orden", header: "Q", render: (v) => (v as number === 1 ? "1st" : "2nd") },
    { key: "fch_vig_desde", header: "From" },
    { key: "fch_vig_hasta", header: "Until" },
    { key: "fch_tope_inf", header: "Deadline" },
    {
      key: "status",
      header: "Status",
      render: (v) => {
        const s = v as string;
        return <StatusBadge status={s} variant={STATUS_VARIANT[s]} />;
      },
    },
    {
      key: "id",
      header: "Actions",
      render: (_v, row) =>
        row.status === "ACTIVE" ? (
          <Button
            variant="outline"
            size="sm"
            disabled={reportingId === row.id}
            onClick={() => void handleSinMovimiento(row.id)}
          >
            {reportingId === row.id ? "..." : "Sin Movimiento"}
          </Button>
        ) : null,
    },
  ];

  async function handleSolicitar(values: Record<string, string>) {
    setFormErrors({});
    setIsRequesting(true);
    try {
      await apiClient("/api/v1/facturacion/caeas/solicitar/", {
        method: "POST",
        body: {
          punto_venta: values.punto_venta,
          periodo: values.periodo,
          orden: Number(values.orden),
        },
      });
      setShowForm(false);
      void queryClient.invalidateQueries({ queryKey: ["/api/v1/facturacion/caeas/"] });
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
      setIsRequesting(false);
    }
  }

  async function handleSinMovimiento(id: string) {
    setReportingId(id);
    try {
      await apiClient(`/api/v1/facturacion/caeas/${id}/sin-movimiento/`, {
        method: "POST",
      });
      void queryClient.invalidateQueries({ queryKey: ["/api/v1/facturacion/caeas/"] });
    } finally {
      setReportingId(null);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => { setShowForm((v) => !v); setFormErrors({}); }}>
          {showForm ? "Cancel" : "Request CAEA"}
        </Button>
      </div>
      {showForm ? (
        <CrudForm
          fields={solicitarFields}
          mode="create"
          title="Request CAEA from ARCA"
          onSubmit={handleSolicitar}
          errors={formErrors}
          isLoading={isRequesting}
        />
      ) : null}
      {error ? (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : "Failed to load CAEAs"}
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
      {data.length > 0 ? <RawJsonToggle data={data} label="CAEAs JSON" /> : null}
    </div>
  );
}
