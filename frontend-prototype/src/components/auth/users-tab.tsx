"use client";

import { usePagination } from "@/hooks/use-pagination";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { StatusBadge } from "@/components/status-badge";
import { RawJsonToggle } from "@/components/raw-json-toggle";

interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  role: { id: string; name: string; permissions: string[] } | null;
  default_branch: { id: string; name: string } | null;
  created_at: string;
  [key: string]: unknown;
}

const columns: ColumnDef<User>[] = [
  { key: "email", header: "Email" },
  {
    key: "full_name",
    header: "Name",
    render: (v) => (v as string | null) ?? "-",
  },
  {
    key: "is_active",
    header: "Status",
    render: (v) => (
      <StatusBadge status={v as boolean ? "active" : "inactive"} />
    ),
  },
  {
    key: "role",
    header: "Role",
    render: (v) => (v as { name: string } | null)?.name ?? "-",
  },
  {
    key: "default_branch",
    header: "Branch",
    render: (v) => (v as { name: string } | null)?.name ?? "-",
  },
];

export function UsersTab() {
  const {
    data,
    isLoading,
    hasNextPage,
    fetchNextPage,
    isFetchingNextPage,
    error,
  } = usePagination<User>("/api/v1/auth/users/");

  return (
    <div className="space-y-4">
      {error ? (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : "Failed to load users"}
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
      {data.length > 0 ? <RawJsonToggle data={data} label="Users JSON" /> : null}
    </div>
  );
}
