"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { StatusBadge } from "@/components/status-badge";
import { RawJsonToggle } from "@/components/raw-json-toggle";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface HealthCheck {
  status: string;
  latency_ms?: number;
  pending?: number;
}

interface HealthResponse {
  status: string;
  checks: Record<string, HealthCheck>;
  version: string;
  timestamp: string;
}

export default function HealthPage() {
  const { data, isLoading, error, refetch, dataUpdatedAt } =
    useQuery<HealthResponse>({
      queryKey: ["health"],
      queryFn: () => apiClient<HealthResponse>("/api/v1/health/"),
      refetchInterval: 30_000,
    });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">System Health</h1>
        <Button
          variant="outline"
          size="sm"
          onClick={() => void refetch()}
          disabled={isLoading}
        >
          {isLoading ? "Checking..." : "Refresh"}
        </Button>
      </div>

      {error ? (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-sm text-destructive">
              Failed to fetch health status:{" "}
              {error instanceof Error ? error.message : "Unknown error"}
            </p>
          </CardContent>
        </Card>
      ) : null}

      {data ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-3">
                Overall Status
                <StatusBadge status={data.status} />
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>
                <span className="text-muted-foreground">Version:</span>{" "}
                {data.version}
              </p>
              <p>
                <span className="text-muted-foreground">Timestamp:</span>{" "}
                {data.timestamp}
              </p>
              {dataUpdatedAt ? (
                <p>
                  <span className="text-muted-foreground">Last checked:</span>{" "}
                  {new Date(dataUpdatedAt).toLocaleTimeString()}
                </p>
              ) : null}
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-3">
            {Object.entries(data.checks).map(([name, check]) => (
              <Card key={name}>
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center justify-between text-base">
                    <span className="capitalize">{name}</span>
                    <StatusBadge status={check.status} />
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  {check.latency_ms != null ? (
                    <p>Latency: {check.latency_ms}ms</p>
                  ) : null}
                  {check.pending != null ? (
                    <p>Pending migrations: {check.pending}</p>
                  ) : null}
                </CardContent>
              </Card>
            ))}
          </div>

          <RawJsonToggle data={data} label="Health Response" />
        </>
      ) : null}
    </div>
  );
}
