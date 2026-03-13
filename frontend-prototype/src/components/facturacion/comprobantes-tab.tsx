"use client";

import { useState } from "react";
import { usePagination } from "@/hooks/use-pagination";
import { apiClient } from "@/lib/api-client";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { StatusBadge } from "@/components/status-badge";
import { RawJsonToggle } from "@/components/raw-json-toggle";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Comprobante extends Record<string, unknown> {
  id: string;
  punto_venta_numero: number;
  cbte_tipo: number;
  cbte_nro: number;
  concepto: number;
  doc_tipo: number;
  doc_nro: string;
  cbte_fch: string;
  imp_total: string;
  imp_neto: string;
  imp_iva: string;
  imp_trib: string;
  status: string;
  cae: string | null;
  cae_fch_vto: string | null;
  emitter_cuit: string;
  customer_name: string | null;
  qr_url: string | null;
  arca_errors: unknown;
  created_at: string;
}

const CBTE_TIPO_LABELS: Record<number, string> = {
  1: "Factura A",
  2: "ND A",
  3: "NC A",
  6: "Factura B",
  7: "ND B",
  8: "NC B",
  11: "Factura C",
  12: "ND C",
  13: "NC C",
  51: "Factura M",
  52: "ND M",
  53: "NC M",
};

const STATUS_VARIANT: Record<string, "warning" | "success" | "error" | "default"> = {
  DRAFT: "warning",
  VALIDANDO: "default",
  AUTORIZADO: "success",
  OBSERVADO: "warning",
  RECHAZADO: "error",
};

export function ComprobantesTab() {
  const { data, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage, error } =
    usePagination<Comprobante>("/api/v1/facturacion/comprobantes/");

  const [selected, setSelected] = useState<Comprobante | null>(null);
  const [authorizing, setAuthorizing] = useState(false);

  const columns: ColumnDef<Comprobante>[] = [
    {
      key: "cbte_tipo",
      header: "Type",
      render: (v) => CBTE_TIPO_LABELS[v as number] ?? String(v),
    },
    { key: "punto_venta_numero", header: "PtoVta" },
    { key: "cbte_nro", header: "Nro" },
    {
      key: "customer_name",
      header: "Customer",
      render: (v, row) =>
        (v as string | null) ?? `Doc ${(row as Comprobante).doc_tipo}-${(row as Comprobante).doc_nro}`,
    },
    { key: "imp_total", header: "Total", render: (v) => `$${v}` },
    {
      key: "status",
      header: "Status",
      render: (v) => {
        const s = v as string;
        return <StatusBadge status={s} variant={STATUS_VARIANT[s]} />;
      },
    },
    {
      key: "cae",
      header: "CAE",
      render: (v) => (v as string | null) ? (v as string).slice(0, 10) + "..." : "-",
    },
    { key: "cbte_fch", header: "Date" },
    {
      key: "id",
      header: "Actions",
      render: (_v, row) => (
        <Button variant="outline" size="sm" onClick={() => setSelected(row)}>
          Detail
        </Button>
      ),
    },
  ];

  async function handleAuthorize() {
    if (!selected) return;
    setAuthorizing(true);
    try {
      const updated = await apiClient<Comprobante>(
        `/api/v1/facturacion/comprobantes/${selected.id}/authorize/`,
        { method: "POST" },
      );
      setSelected(updated);
    } finally {
      setAuthorizing(false);
    }
  }

  return (
    <div className="space-y-4">
      {error ? (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : "Failed to load comprobantes"}
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

      {selected ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between text-base">
              <span>
                {CBTE_TIPO_LABELS[selected.cbte_tipo] ?? `Type ${selected.cbte_tipo}`}{" "}
                {String(selected.punto_venta_numero).padStart(5, "0")}-
                {String(selected.cbte_nro).padStart(8, "0")}
              </span>
              <div className="flex items-center gap-2">
                <StatusBadge
                  status={selected.status}
                  variant={STATUS_VARIANT[selected.status]}
                />
                {selected.status === "DRAFT" ? (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={authorizing}
                    onClick={() => void handleAuthorize()}
                  >
                    {authorizing ? "..." : "Authorize (CAE)"}
                  </Button>
                ) : null}
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
              <div>
                <span className="text-muted-foreground">Customer:</span>{" "}
                {selected.customer_name}
              </div>
              <div>
                <span className="text-muted-foreground">Doc:</span> {selected.doc_tipo}-
                {selected.doc_nro}
              </div>
              <div>
                <span className="text-muted-foreground">Emitter:</span> {selected.emitter_cuit}
              </div>
              <div>
                <span className="text-muted-foreground">Date:</span> {selected.cbte_fch}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
              <div>
                <span className="text-muted-foreground">Neto:</span> ${selected.imp_neto}
              </div>
              <div>
                <span className="text-muted-foreground">IVA:</span> ${selected.imp_iva}
              </div>
              <div>
                <span className="text-muted-foreground">Tributos:</span> ${selected.imp_trib}
              </div>
              <div>
                <span className="font-medium">Total:</span> ${selected.imp_total}
              </div>
            </div>

            {selected.cae ? (
              <div className="rounded-md border p-3 text-sm">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-muted-foreground">CAE:</span> {selected.cae}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Vto:</span>{" "}
                    {selected.cae_fch_vto ?? "-"}
                  </div>
                </div>
                {selected.qr_url ? (
                  <div className="mt-2">
                    <span className="text-muted-foreground">QR: </span>
                    <a
                      href={selected.qr_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary underline"
                    >
                      View Fiscal QR
                    </a>
                  </div>
                ) : null}
              </div>
            ) : null}

            {selected.arca_errors ? (
              <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm">
                <span className="font-medium text-destructive">ARCA Errors:</span>
                <pre className="mt-1 whitespace-pre-wrap text-xs">
                  {JSON.stringify(selected.arca_errors, null, 2)}
                </pre>
              </div>
            ) : null}

            <RawJsonToggle data={selected} label="Comprobante JSON" />

            <Button variant="outline" size="sm" onClick={() => setSelected(null)}>
              Close Detail
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {data.length > 0 && !selected ? (
        <RawJsonToggle data={data} label="Comprobantes JSON" />
      ) : null}
    </div>
  );
}
