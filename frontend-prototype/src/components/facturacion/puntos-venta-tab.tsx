"use client";

import { useState } from "react";
import { useCrud } from "@/hooks/use-crud";
import { ApiError } from "@/lib/api-client";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { CrudForm, type FieldConfig } from "@/components/crud-form";
import { StatusBadge } from "@/components/status-badge";
import { RawJsonToggle } from "@/components/raw-json-toggle";
import { Button } from "@/components/ui/button";

interface PuntoDeVenta extends Record<string, unknown> {
  id: string;
  numero: number;
  tipo: string;
  description: string;
  is_active: boolean;
  fecha_alta: string | null;
  created_at: string;
}

const formFields: FieldConfig[] = [
  { name: "numero", label: "Number", type: "number", required: true, placeholder: "1-99999" },
  {
    name: "tipo",
    label: "Type",
    type: "select",
    required: true,
    options: [
      { label: "Electronic", value: "electronic" },
      { label: "Manual", value: "manual" },
    ],
  },
  { name: "description", label: "Description", type: "text", placeholder: "e.g. Main POS" },
  { name: "fecha_alta", label: "ARCA Registration Date", type: "text", placeholder: "YYYY-MM-DD" },
];

const columns: ColumnDef<PuntoDeVenta>[] = [
  { key: "numero", header: "#" },
  { key: "tipo", header: "Type" },
  { key: "description", header: "Description", render: (v) => (v as string) || "-" },
  {
    key: "is_active",
    header: "Status",
    render: (v) => <StatusBadge status={v as boolean ? "active" : "inactive"} />,
  },
  { key: "fecha_alta", header: "Reg. Date", render: (v) => (v as string | null) || "-" },
  { key: "created_at", header: "Created", render: (v) => (v as string).slice(0, 10) },
];

export function PuntosVentaTab() {
  const { items, isLoading, create, isCreating } =
    useCrud<PuntoDeVenta>("/api/v1/facturacion/puntos-de-venta/");

  const [showForm, setShowForm] = useState(false);
  const [formErrors, setFormErrors] = useState<Record<string, string[]>>({});

  async function handleCreate(values: Record<string, string>) {
    setFormErrors({});
    try {
      await create({
        numero: Number(values.numero),
        tipo: values.tipo,
        description: values.description || "",
        fecha_alta: values.fecha_alta || null,
      } as unknown as Partial<PuntoDeVenta>);
      setShowForm(false);
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

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => { setShowForm((v) => !v); setFormErrors({}); }}>
          {showForm ? "Cancel" : "New Punto de Venta"}
        </Button>
      </div>
      {showForm ? (
        <CrudForm
          fields={formFields}
          mode="create"
          title="Register Punto de Venta"
          onSubmit={handleCreate}
          errors={formErrors}
          isLoading={isCreating}
        />
      ) : null}
      <DataTable columns={columns} data={items} isLoading={isLoading} />
      {items.length > 0 ? <RawJsonToggle data={items} label="Puntos de Venta JSON" /> : null}
    </div>
  );
}
