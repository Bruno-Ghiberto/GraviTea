"use client";

import { useState, type FormEvent } from "react";
import { useAuth } from "@/lib/auth-context";
import { apiClient, ApiError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

function JsonBlock({ data }: { data: unknown }) {
  return (
    <pre className="mt-2 max-h-64 overflow-auto rounded bg-muted p-3 text-xs">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

function ProfileSection() {
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function fetchProfile() {
    setError(null);
    setLoading(true);
    try {
      const data = await apiClient("/api/v1/auth/users/me/");
      setResult(data);
    } catch (err) {
      setError(
        err instanceof ApiError ? JSON.stringify(err.body) : String(err),
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Profile</CardTitle>
        <CardDescription>GET /api/v1/auth/users/me/</CardDescription>
      </CardHeader>
      <CardContent>
        <Button size="sm" onClick={fetchProfile} disabled={loading}>
          {loading ? "Loading..." : "Fetch Profile"}
        </Button>
        {error ? (
          <p className="mt-2 text-sm text-destructive">{error}</p>
        ) : null}
        {result ? <JsonBlock data={result} /> : null}
      </CardContent>
    </Card>
  );
}

function RefreshSection() {
  const { refresh, accessToken } = useAuth();
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleRefresh() {
    setError(null);
    setLoading(true);
    try {
      await refresh();
      setResult("Token refreshed successfully");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Refresh failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Manual Refresh</CardTitle>
        <CardDescription>POST /api/v1/auth/token/refresh/</CardDescription>
      </CardHeader>
      <CardContent>
        <Button size="sm" onClick={handleRefresh} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh Token"}
        </Button>
        {result ? (
          <p className="mt-2 text-sm text-green-600">{result}</p>
        ) : null}
        {error ? (
          <p className="mt-2 text-sm text-destructive">{error}</p>
        ) : null}
        {accessToken ? (
          <p className="mt-2 truncate text-xs text-muted-foreground">
            Current token: {accessToken.slice(0, 20)}...
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

function VerifySection() {
  const { accessToken } = useAuth();
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleVerify() {
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      await apiClient("/api/v1/auth/token/verify/", {
        method: "POST",
        body: { token: accessToken },
      });
      setResult({ valid: true });
    } catch (err) {
      if (err instanceof ApiError) {
        setResult({ valid: false, status: err.status, detail: err.body });
      } else {
        setError(String(err));
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Token Verify</CardTitle>
        <CardDescription>POST /api/v1/auth/token/verify/</CardDescription>
      </CardHeader>
      <CardContent>
        <Button size="sm" onClick={handleVerify} disabled={loading}>
          {loading ? "Verifying..." : "Verify Token"}
        </Button>
        {error ? (
          <p className="mt-2 text-sm text-destructive">{error}</p>
        ) : null}
        {result ? <JsonBlock data={result} /> : null}
      </CardContent>
    </Card>
  );
}

function ChangePasswordSection() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const data = await apiClient("/api/v1/auth/users/me/change-password/", {
        method: "POST",
        body: {
          current_password: currentPassword,
          new_password: newPassword,
        },
      });
      setResult(data);
      setCurrentPassword("");
      setNewPassword("");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(JSON.stringify(err.body));
      } else {
        setError(String(err));
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Change Password</CardTitle>
        <CardDescription>
          POST /api/v1/auth/users/me/change-password/
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="grid gap-3">
          <Input
            type="password"
            placeholder="Current password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
          <Input
            type="password"
            placeholder="New password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            autoComplete="new-password"
          />
          <Button type="submit" size="sm" disabled={loading}>
            {loading ? "Changing..." : "Change Password"}
          </Button>
        </form>
        {error ? (
          <p className="mt-2 text-sm text-destructive">{error}</p>
        ) : null}
        {result ? <JsonBlock data={result} /> : null}
      </CardContent>
    </Card>
  );
}

function LogoutSection() {
  const { logout } = useAuth();
  const [loading, setLoading] = useState(false);

  async function handleLogout() {
    setLoading(true);
    await logout();
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Logout</CardTitle>
        <CardDescription>POST /api/v1/auth/logout/</CardDescription>
      </CardHeader>
      <CardContent>
        <Button
          size="sm"
          variant="destructive"
          onClick={handleLogout}
          disabled={loading}
        >
          {loading ? "Logging out..." : "Logout"}
        </Button>
      </CardContent>
    </Card>
  );
}

export function OperationsTab() {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <ProfileSection />
      <RefreshSection />
      <VerifySection />
      <ChangePasswordSection />
      <LogoutSection />
    </div>
  );
}
