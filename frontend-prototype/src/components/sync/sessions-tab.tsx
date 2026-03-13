"use client";

import { useState } from "react";
import { usePagination } from "@/hooks/use-pagination";
import { apiClient, ApiError } from "@/lib/api-client";
import { DataTable, type ColumnDef } from "@/components/data-table";
import { CrudForm, type FieldConfig } from "@/components/crud-form";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { RawJsonToggle } from "@/components/raw-json-toggle";
import { Button } from "@/components/ui/button";
import { useQueryClient } from "@tanstack/react-query";

interface SyncSession extends Record<string, unknown> {
  id: string;
  device_id: string;
  branch: string;
  status: string;
  last_sync_at: string | null;
  pending_operations: number;
  conflicts: number;
  created_at: string;
}

const formFields: FieldConfig[] = [
  { name: "device_id", label: "Device ID", type: "text", required: true, placeholder: "POS-BRANCH-001-TERMINAL-01" },
  { name: "branch", label: "Branch ID (UUID)", type: "text", required: true },
];

export function SessionsTab() {
  const queryClient = useQueryClient();
  const { data, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage, error } =
    usePagination<SyncSession>("/api/v1/sync/sessions/");

  const [showForm, setShowForm] = useState(false);
  const [formErrors, setFormErrors] = useState<Record<string, string[]>>({});
  const [isCreating, setIsCreating] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const columns: ColumnDef<SyncSession>[] = [
    { key: "device_id", header: "Device" },
    { key: "status", header: "Status" },
    {
      key: "last_sync_at",
      header: "Last Sync",
      render: (v) => (v as string | null) ? (v as string).slice(0, 19).replace("T", " ") : "Never",
    },
    { key: "pending_operations", header: "Pending" },
    { key: "conflicts", header: "Conflicts" },
    {
      key: "id",
      header: "Actions",
      render: (_v, row) => (
        <Button variant="destructive" size="sm" onClick={() => setDeletingId(row.id)}>
          Unregister
        </Button>
      ),
    },
  ];

  async function handleCreate(values: Record<string, string>) {
    setFormErrors({});
    setIsCreating(true);
    try {
      await apiClient("/api/v1/sync/sessions/", {
        method: "POST",
        body: { device_id: values.device_id, branch: values.branch },
      });
      setShowForm(false);
      void queryClient.invalidateQueries({ queryKey: ["/api/v1/sync/sessions/"] });
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

  async function handleDelete() {
    if (!deletingId) return;
    setIsDeleting(true);
    try {
      await apiClient(`/api/v1/sync/sessions/${deletingId}/`, { method: "DELETE" });
      void queryClient.invalidateQueries({ queryKey: ["/api/v1/sync/sessions/"] });
    } finally {
      setIsDeleting(false);
      setDeletingId(null);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => { setShowForm((v) => !v); setFormErrors({}); }}>
          {showForm ? "Cancel" : "Register Device"}
        </Button>
      </div>
      {showForm ? (
        <CrudForm
          fields={formFields}
          mode="create"
          title="Register POS Terminal"
          onSubmit={handleCreate}
          errors={formErrors}
          isLoading={isCreating}
        />
      ) : null}
      {error ? (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : "Failed to load sessions"}
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
      {data.length > 0 ? <RawJsonToggle data={data} label="Sessions JSON" /> : null}
      <ConfirmDialog
        open={deletingId !== null}
        title="Unregister Device"
        description="This will delete the sync session and all pending operations for this device. This cannot be undone."
        onConfirm={() => void handleDelete()}
        onCancel={() => setDeletingId(null)}
        isLoading={isDeleting}
      />
    </div>
  );
}
