"use client";

import { usePagination } from "@/hooks/use-pagination";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { StatusBadge } from "@/components/status-badge";
import { RawJsonToggle } from "@/components/raw-json-toggle";

interface Branch {
  id: string;
  name: string;
  address: string | null;
  is_active: boolean;
  created_at: string;
  [key: string]: unknown;
}

const columns: ColumnDef<Branch>[] = [
  { key: "name", header: "Name" },
  {
    key: "address",
    header: "Address",
    render: (v) => (v as string | null) ?? "-",
  },
  {
    key: "is_active",
    header: "Status",
    render: (v) => (
      <StatusBadge status={v as boolean ? "active" : "inactive"} />
    ),
  },
  { key: "created_at", header: "Created" },
];

export function BranchesTab() {
  const {
    data,
    isLoading,
    hasNextPage,
    fetchNextPage,
    isFetchingNextPage,
    error,
  } = usePagination<Branch>("/api/v1/auth/branches/");

  return (
    <div className="space-y-4">
      {error ? (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : "Failed to load branches"}
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
      {data.length > 0 ? (
        <RawJsonToggle data={data} label="Branches JSON" />
      ) : null}
    </div>
  );
}
