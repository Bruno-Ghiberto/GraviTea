"use client";

import { useState } from "react";
import { apiClient, ApiError } from "@/lib/api-client";
import { CrudForm, type FieldConfig } from "@/components/crud-form";
import { RawJsonToggle } from "@/components/raw-json-toggle";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface PullResponse {
  changes: unknown[];
  server_timestamp: string;
  has_more: boolean;
}

interface PushResponse {
  status: string;
  created: number;
  skipped: number;
  errors: unknown[];
  server_timestamp: string;
}

const pullFields: FieldConfig[] = [
  { name: "device_id", label: "Device ID", type: "text", required: true, placeholder: "POS-BRANCH-001-TERMINAL-01" },
  { name: "last_sync_at", label: "Last Sync At (ISO datetime, optional)", type: "text", placeholder: "2026-01-01T00:00:00Z" },
  { name: "entity_types", label: "Entity Types (comma-separated, optional)", type: "text", placeholder: "Sale,StockMovement" },
];

const pushFields: FieldConfig[] = [
  { name: "device_id", label: "Device ID", type: "text", required: true, placeholder: "POS-BRANCH-001-TERMINAL-01" },
  { name: "operations_json", label: "Operations (JSON array)", type: "textarea", required: true, placeholder: '[{"id":"...","operation_type":"CREATE","entity_type":"Sale","entity_id":"...","payload":{},"client_timestamp":"..."}]' },
];

export function OperationsTab() {
  const [pullResult, setPullResult] = useState<PullResponse | null>(null);
  const [pushResult, setPushResult] = useState<PushResponse | null>(null);
  const [pullErrors, setPullErrors] = useState<Record<string, string[]>>({});
  const [pushErrors, setPushErrors] = useState<Record<string, string[]>>({});
  const [isPulling, setIsPulling] = useState(false);
  const [isPushing, setIsPushing] = useState(false);

  async function handlePull(values: Record<string, string>) {
    setPullErrors({});
    setPullResult(null);
    setIsPulling(true);
    try {
      const body: Record<string, unknown> = { device_id: values.device_id };
      if (values.last_sync_at) body.last_sync_at = values.last_sync_at;
      if (values.entity_types) body.entity_types = values.entity_types.split(",").map((s) => s.trim());
      const res = await apiClient<PullResponse>("/api/v1/sync/pull/", {
        method: "POST",
        body,
      });
      setPullResult(res);
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
          setPullErrors(fe);
        }
      }
    } finally {
      setIsPulling(false);
    }
  }

  async function handlePush(values: Record<string, string>) {
    setPushErrors({});
    setPushResult(null);
    setIsPushing(true);
    try {
      let operations: unknown[];
      const rawJson = values.operations_json ?? "";
      try {
        operations = JSON.parse(rawJson) as unknown[];
      } catch {
        setPushErrors({ operations_json: ["Invalid JSON array"] });
        setIsPushing(false);
        return;
      }
      const res = await apiClient<PushResponse>("/api/v1/sync/push/", {
        method: "POST",
        body: { device_id: values.device_id, operations },
      });
      setPushResult(res);
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
          setPushErrors(fe);
        }
      }
    } finally {
      setIsPushing(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Pull Changes</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <CrudForm
            fields={pullFields}
            mode="create"
            title=""
            onSubmit={handlePull}
            errors={pullErrors}
            isLoading={isPulling}
          />
          {pullResult ? <RawJsonToggle data={pullResult} label="Pull Response" /> : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Push Operations</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <CrudForm
            fields={pushFields}
            mode="create"
            title=""
            onSubmit={handlePush}
            errors={pushErrors}
            isLoading={isPushing}
          />
          {pushResult ? (
            <div className="space-y-2">
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>Created: {pushResult.created}</div>
                <div>Skipped: {pushResult.skipped}</div>
                <div>Errors: {pushResult.errors.length}</div>
              </div>
              <RawJsonToggle data={pushResult} label="Push Response" />
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
