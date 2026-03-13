"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient, ApiError } from "@/lib/api-client";
import { CrudForm, type FieldConfig } from "@/components/crud-form";
import { RawJsonToggle } from "@/components/raw-json-toggle";
import { Button } from "@/components/ui/button";

interface CategoryTreeNode {
  id: string;
  name: string;
  children: CategoryTreeNode[];
}

function TreeNode({ node, depth }: { node: CategoryTreeNode; depth: number }) {
  return (
    <div style={{ paddingLeft: `${depth * 1.5}rem` }}>
      <div className="flex items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-muted">
        {node.children.length > 0 ? (
          <span className="text-muted-foreground">+</span>
        ) : (
          <span className="text-muted-foreground">-</span>
        )}
        <span>{node.name}</span>
        <span className="text-xs text-muted-foreground">({node.id.slice(0, 8)})</span>
      </div>
      {node.children.map((child) => (
        <TreeNode key={child.id} node={child} depth={depth + 1} />
      ))}
    </div>
  );
}

const formFields: FieldConfig[] = [
  { name: "name", label: "Category Name", type: "text", required: true },
  { name: "parent", label: "Parent ID (optional UUID)", type: "text", placeholder: "Leave empty for root" },
];

export function CategoriesTab() {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery<CategoryTreeNode[]>({
    queryKey: ["categories-tree"],
    queryFn: () => apiClient<CategoryTreeNode[]>("/api/v1/categories/tree/"),
  });

  const [showForm, setShowForm] = useState(false);
  const [formErrors, setFormErrors] = useState<Record<string, string[]>>({});
  const [isCreating, setIsCreating] = useState(false);

  async function handleCreate(values: Record<string, string>) {
    setFormErrors({});
    setIsCreating(true);
    try {
      await apiClient("/api/v1/categories/", {
        method: "POST",
        body: {
          name: values.name,
          parent: values.parent || null,
        },
      });
      setShowForm(false);
      void queryClient.invalidateQueries({ queryKey: ["categories-tree"] });
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

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => { setShowForm((v) => !v); setFormErrors({}); }}>
          {showForm ? "Cancel" : "New Category"}
        </Button>
      </div>
      {showForm ? (
        <CrudForm
          fields={formFields}
          mode="create"
          title="Create Category"
          onSubmit={handleCreate}
          errors={formErrors}
          isLoading={isCreating}
        />
      ) : null}
      {error ? (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : "Failed to load categories"}
        </p>
      ) : null}
      {isLoading ? (
        <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
          Loading...
        </div>
      ) : null}
      {data && data.length === 0 ? (
        <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
          No categories found.
        </div>
      ) : null}
      {data && data.length > 0 ? (
        <div className="rounded-md border p-2">
          {data.map((node) => (
            <TreeNode key={node.id} node={node} depth={0} />
          ))}
        </div>
      ) : null}
      {data && data.length > 0 ? <RawJsonToggle data={data} label="Tree JSON" /> : null}
    </div>
  );
}
