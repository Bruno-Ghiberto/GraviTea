"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function JwtClaims() {
  const { claims, accessToken } = useAuth();
  const [expanded, setExpanded] = useState(false);

  if (!claims) {
    return null;
  }

  const expiresAt = new Date(claims.exp * 1000).toLocaleString();
  const issuedAt = new Date(claims.iat * 1000).toLocaleString();

  return (
    <div className="w-full">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setExpanded((v) => !v)}
        className="text-xs text-muted-foreground"
      >
        {expanded ? "Hide" : "Show"} JWT Claims
      </Button>
      {expanded ? (
        <Card className="mt-2">
          <CardHeader className="py-3">
            <CardTitle className="text-sm">JWT Claims</CardTitle>
          </CardHeader>
          <CardContent className="py-2">
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
              <dt className="font-medium text-muted-foreground">tenant_id</dt>
              <dd className="font-mono">{claims.tenant_id}</dd>

              <dt className="font-medium text-muted-foreground">user_id</dt>
              <dd className="font-mono">{claims.sub}</dd>

              <dt className="font-medium text-muted-foreground">email</dt>
              <dd className="font-mono">{claims.email ?? "—"}</dd>

              <dt className="font-medium text-muted-foreground">expires</dt>
              <dd>{expiresAt}</dd>

              <dt className="font-medium text-muted-foreground">issued</dt>
              <dd>{issuedAt}</dd>

              <dt className="font-medium text-muted-foreground">jti</dt>
              <dd className="font-mono truncate">{claims.jti}</dd>
            </dl>
            {accessToken ? (
              <details className="mt-3">
                <summary className="cursor-pointer text-xs text-muted-foreground">
                  Raw token
                </summary>
                <pre className="mt-1 max-h-32 overflow-auto rounded bg-muted p-2 text-[10px] break-all whitespace-pre-wrap">
                  {accessToken}
                </pre>
              </details>
            ) : null}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
