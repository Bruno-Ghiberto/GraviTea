"use client";

import { useState } from "react";
import { apiClient } from "@/lib/api-client";
import { StatusBadge } from "@/components/status-badge";
import { RawJsonToggle } from "@/components/raw-json-toggle";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface SyncStatus {
  device_id: string;
  status: string;
  last_sync_at: string | null;
  pending_operations: number;
  conflicts: number;
  sync_vector: unknown;
}

const STATUS_VARIANT: Record<string, "success" | "warning" | "error" | "default"> = {
  completed: "success",
  pending: "warning",
  processing: "default",
  error: "error",
};

export function StatusTab() {
  const [deviceId, setDeviceId] = useState("");
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCheck() {
    if (!deviceId.trim()) return;
    setIsLoading(true);
    setError(null);
    setStatus(null);
    try {
      const res = await apiClient<SyncStatus>(`/api/v1/sync/status/${encodeURIComponent(deviceId)}/`);
      setStatus(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch status");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <label htmlFor="device-id-input" className="mb-1 block text-sm font-medium">
            Device ID
          </label>
          <input
            id="device-id-input"
            type="text"
            value={deviceId}
            onChange={(e) => setDeviceId(e.target.value)}
            placeholder="POS-BRANCH-001-TERMINAL-01"
            className="w-full rounded-md border px-3 py-2 text-sm"
            onKeyDown={(e) => {
              if (e.key === "Enter") void handleCheck();
            }}
          />
        </div>
        <Button size="sm" disabled={isLoading || !deviceId.trim()} onClick={() => void handleCheck()}>
          {isLoading ? "Checking..." : "Check Status"}
        </Button>
      </div>

      {error ? (
        <p className="text-sm text-destructive">{error}</p>
      ) : null}

      {status ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between text-base">
              <span>{status.device_id}</span>
              <StatusBadge
                status={status.status}
                variant={STATUS_VARIANT[status.status]}
              />
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
              <div>
                <span className="text-muted-foreground">Last Sync:</span>{" "}
                {status.last_sync_at
                  ? status.last_sync_at.slice(0, 19).replace("T", " ")
                  : "Never"}
              </div>
              <div>
                <span className="text-muted-foreground">Pending Ops:</span>{" "}
                {status.pending_operations}
              </div>
              <div>
                <span className="text-muted-foreground">Conflicts:</span>{" "}
                {status.conflicts}
              </div>
              <div>
                <span className="text-muted-foreground">Status:</span> {status.status}
              </div>
            </div>
            <RawJsonToggle data={status} label="Full Status JSON" />
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
