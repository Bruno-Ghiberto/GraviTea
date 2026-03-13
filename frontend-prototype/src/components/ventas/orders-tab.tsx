"use client";

import { useState } from "react";
import { usePagination } from "@/hooks/use-pagination";
import { apiClient, ApiError } from "@/lib/api-client";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { CrudForm, type FieldConfig } from "@/components/crud-form";
import { StatusBadge } from "@/components/status-badge";
import { RawJsonToggle } from "@/components/raw-json-toggle";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useQueryClient } from "@tanstack/react-query";

interface SaleOrder extends Record<string, unknown> {
  id: string;
  customer_name: string;
  branch_name: string;
  status: string;
  status_display: string;
  subtotal: string;
  total_iva: string;
  total_amount: string;
  sale_date: string;
  comprobante_id: string | null;
}

interface OrderItem extends Record<string, unknown> {
  id: string;
  product_name: string;
  product_sku: string;
  quantity: string;
  unit_price: string;
  tax_rate: string;
  subtotal: string;
  iva_amount: string;
}

const STATUS_VARIANT: Record<string, "warning" | "success" | "default"> = {
  DRAFT: "warning",
  CONFIRMED: "success",
  INVOICED: "success",
};

const orderFormFields: FieldConfig[] = [
  { name: "customer", label: "Customer ID (UUID)", type: "text", required: true },
  { name: "branch", label: "Branch ID (UUID)", type: "text", required: true },
];

const itemFormFields: FieldConfig[] = [
  { name: "product", label: "Product ID (UUID)", type: "text", required: true },
  { name: "quantity", label: "Quantity", type: "number", required: true },
  { name: "unit_price", label: "Unit Price", type: "number", required: true },
  { name: "tax_rate", label: "Tax Rate %", type: "number", placeholder: "21.00" },
];

const itemColumns: ColumnDef<OrderItem>[] = [
  { key: "product_sku", header: "SKU" },
  { key: "product_name", header: "Product" },
  { key: "quantity", header: "Qty" },
  { key: "unit_price", header: "Price", render: (v) => `$${v}` },
  { key: "tax_rate", header: "IVA %", render: (v) => `${v}%` },
  { key: "subtotal", header: "Subtotal", render: (v) => `$${v}` },
  {
    key: "iva_amount",
    header: "Total",
    render: (_v, row) => {
      const subtotal = parseFloat((row as OrderItem).subtotal) || 0;
      const iva = parseFloat((row as OrderItem).iva_amount) || 0;
      return `$${(subtotal + iva).toFixed(2)}`;
    },
  },
];

export function OrdersTab() {
  const queryClient = useQueryClient();
  const { data, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage, error } =
    usePagination<SaleOrder>("/api/v1/ventas/orders/");

  const [showForm, setShowForm] = useState(false);
  const [formErrors, setFormErrors] = useState<Record<string, string[]>>({});
  const [isCreating, setIsCreating] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<SaleOrder | null>(null);
  const [orderItems, setOrderItems] = useState<OrderItem[]>([]);
  const [itemsLoading, setItemsLoading] = useState(false);
  const [showItemForm, setShowItemForm] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const columns: ColumnDef<SaleOrder>[] = [
    { key: "customer_name", header: "Customer" },
    { key: "branch_name", header: "Branch" },
    {
      key: "status",
      header: "Status",
      render: (v) => {
        const s = v as string;
        return <StatusBadge status={s} variant={STATUS_VARIANT[s]} />;
      },
    },
    { key: "total_amount", header: "Total", render: (v) => `$${v}` },
    { key: "sale_date", header: "Date" },
    {
      key: "comprobante_id",
      header: "Invoice",
      render: (v) => (v as string | null) ? (v as string).slice(0, 8) + "..." : "-",
    },
    {
      key: "id",
      header: "Actions",
      render: (_v, row) => (
        <Button variant="outline" size="sm" onClick={() => void loadOrderDetail(row)}>
          View
        </Button>
      ),
    },
  ];

  async function loadOrderDetail(order: SaleOrder) {
    setSelectedOrder(order);
    setItemsLoading(true);
    setShowItemForm(false);
    try {
      const res = await apiClient<{ results: OrderItem[] }>(
        `/api/v1/ventas/orders/${order.id}/items/`,
      );
      setOrderItems(res.results);
    } catch {
      setOrderItems([]);
    } finally {
      setItemsLoading(false);
    }
  }

  async function handleCreateOrder(values: Record<string, string>) {
    setFormErrors({});
    setIsCreating(true);
    try {
      await apiClient("/api/v1/ventas/orders/", {
        method: "POST",
        body: { customer: values.customer, branch: values.branch },
      });
      setShowForm(false);
      void queryClient.invalidateQueries({ queryKey: ["/api/v1/ventas/orders/"] });
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

  async function handleAddItem(values: Record<string, string>) {
    if (!selectedOrder) return;
    try {
      await apiClient(`/api/v1/ventas/orders/${selectedOrder.id}/items/`, {
        method: "POST",
        body: {
          product: values.product,
          quantity: values.quantity,
          unit_price: values.unit_price,
          tax_rate: values.tax_rate || "21.00",
        },
      });
      setShowItemForm(false);
      void loadOrderDetail(selectedOrder);
      void queryClient.invalidateQueries({ queryKey: ["/api/v1/ventas/orders/"] });
    } catch {
      // form errors handled by CrudForm in a full impl
    }
  }

  async function handleAction(action: string) {
    if (!selectedOrder) return;
    setActionLoading(action);
    try {
      const method = action === "invoice" ? "GET" : "POST";
      await apiClient(`/api/v1/ventas/orders/${selectedOrder.id}/${action}/`, {
        method,
      });
      void queryClient.invalidateQueries({ queryKey: ["/api/v1/ventas/orders/"] });
      // Reload order detail to see updated status
      const updated = await apiClient<SaleOrder>(
        `/api/v1/ventas/orders/${selectedOrder.id}/`,
      );
      setSelectedOrder(updated);
    } finally {
      setActionLoading(null);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => { setShowForm((v) => !v); setFormErrors({}); }}>
          {showForm ? "Cancel" : "New Order"}
        </Button>
      </div>
      {showForm ? (
        <CrudForm
          fields={orderFormFields}
          mode="create"
          title="Create Sale Order"
          onSubmit={handleCreateOrder}
          errors={formErrors}
          isLoading={isCreating}
        />
      ) : null}
      {error ? (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : "Failed to load orders"}
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

      {selectedOrder ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between text-base">
              <span>
                Order {selectedOrder.id.slice(0, 8)}... — {selectedOrder.customer_name}
              </span>
              <div className="flex items-center gap-2">
                <StatusBadge
                  status={selectedOrder.status}
                  variant={STATUS_VARIANT[selectedOrder.status]}
                />
                {selectedOrder.status === "DRAFT" ? (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={actionLoading !== null}
                    onClick={() => void handleAction("confirm")}
                  >
                    {actionLoading === "confirm" ? "..." : "Confirm"}
                  </Button>
                ) : null}
                {selectedOrder.status === "CONFIRMED" ? (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={actionLoading !== null}
                    onClick={() => void handleAction("invoice")}
                  >
                    {actionLoading === "invoice" ? "..." : "Invoice"}
                  </Button>
                ) : null}
                {selectedOrder.comprobante_id ? (
                  <span className="text-xs text-muted-foreground">
                    Comprobante: {selectedOrder.comprobante_id.slice(0, 8)}...
                  </span>
                ) : null}
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Subtotal:</span> ${selectedOrder.subtotal}
              </div>
              <div>
                <span className="text-muted-foreground">IVA:</span> ${selectedOrder.total_iva}
              </div>
              <div>
                <span className="font-medium">Total:</span> ${selectedOrder.total_amount}
              </div>
            </div>

            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium">Order Items</h3>
              {selectedOrder.status === "DRAFT" ? (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setShowItemForm((v) => !v)}
                >
                  {showItemForm ? "Cancel" : "Add Item"}
                </Button>
              ) : null}
            </div>

            {showItemForm ? (
              <CrudForm
                fields={itemFormFields}
                mode="create"
                title="Add Item"
                onSubmit={handleAddItem}
              />
            ) : null}

            <DataTable
              columns={itemColumns}
              data={orderItems}
              isLoading={itemsLoading}
            />

            <RawJsonToggle
              data={{ order: selectedOrder, items: orderItems }}
              label="Order Detail JSON"
            />
          </CardContent>
        </Card>
      ) : null}

      {data.length > 0 && !selectedOrder ? (
        <RawJsonToggle data={data} label="Orders JSON" />
      ) : null}
    </div>
  );
}
