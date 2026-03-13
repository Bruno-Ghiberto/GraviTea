"use client";

import { usePagination } from "@/hooks/use-pagination";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { RawJsonToggle } from "@/components/raw-json-toggle";

interface PriceHistoryEntry extends Record<string, unknown> {
  id: string;
  product_sku: string;
  price_list_name: string;
  price: string;
  valid_from: string;
  valid_to: string | null;
}

interface CostHistoryEntry extends Record<string, unknown> {
  id: string;
  product_sku: string;
  cost: string;
  valid_from: string;
  valid_to: string | null;
}

const priceColumns: ColumnDef<PriceHistoryEntry>[] = [
  { key: "product_sku", header: "SKU" },
  { key: "price_list_name", header: "Price List" },
  { key: "price", header: "Price", render: (v) => `$${v}` },
  { key: "valid_from", header: "Effective From" },
  { key: "valid_to", header: "Valid To", render: (v) => (v as string | null) ?? "-" },
];

const costColumns: ColumnDef<CostHistoryEntry>[] = [
  { key: "product_sku", header: "SKU" },
  { key: "cost", header: "Cost", render: (v) => `$${v}` },
  { key: "valid_from", header: "Effective From" },
  { key: "valid_to", header: "Valid To", render: (v) => (v as string | null) ?? "-" },
];

export function PriceHistoryTab() {
  const { data, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage, error } =
    usePagination<PriceHistoryEntry>("/api/v1/price-history/");

  return (
    <div className="space-y-4">
      {error ? (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : "Failed to load price history"}
        </p>
      ) : null}
      <DataTable
        columns={priceColumns}
        data={data}
        isLoading={isLoading}
        hasNextPage={hasNextPage}
        onLoadMore={() => void fetchNextPage()}
        isFetchingNextPage={isFetchingNextPage}
      />
      {data.length > 0 ? <RawJsonToggle data={data} label="Price History JSON" /> : null}
    </div>
  );
}

export function CostHistoryTab() {
  const { data, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage, error } =
    usePagination<CostHistoryEntry>("/api/v1/cost-history/");

  return (
    <div className="space-y-4">
      {error ? (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : "Failed to load cost history"}
        </p>
      ) : null}
      <DataTable
        columns={costColumns}
        data={data}
        isLoading={isLoading}
        hasNextPage={hasNextPage}
        onLoadMore={() => void fetchNextPage()}
        isFetchingNextPage={isFetchingNextPage}
      />
      {data.length > 0 ? <RawJsonToggle data={data} label="Cost History JSON" /> : null}
    </div>
  );
}
