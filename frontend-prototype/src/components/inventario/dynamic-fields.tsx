"use client";

import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Input } from "@/components/ui/input";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface FieldDefinition {
  id: string;
  field_key: string;
  label: string;
  entity_type: string;
  field_type: "text" | "integer" | "decimal" | "boolean" | "date" | "select";
  section: string;
  position: number;
  required: boolean;
  default_value: unknown;
  choices: string[] | null;
}

interface FieldDefinitionsResponse {
  results: FieldDefinition[];
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface DynamicFieldsProps {
  initialValues?: Record<string, unknown>;
  errors?: Record<string, string[]>;
  onChange: (customData: Record<string, unknown>) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function capitalize(s: string): string {
  if (!s) return s;
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function getInitialValue(field: FieldDefinition, initialValues?: Record<string, unknown>): unknown {
  if (initialValues && Object.prototype.hasOwnProperty.call(initialValues, field.field_key)) {
    return initialValues[field.field_key];
  }
  if (field.default_value !== null && field.default_value !== undefined) {
    return field.default_value;
  }
  if (field.field_type === "boolean") return false;
  return "";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function DynamicFields({ initialValues, errors, onChange }: DynamicFieldsProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["/api/v1/field-definitions/", { entity_type: "product" }],
    queryFn: () =>
      apiClient<FieldDefinitionsResponse>(
        "/api/v1/field-definitions/?entity_type=product",
      ),
  });

  const definitions: FieldDefinition[] = data?.results ?? [];

  // Initialize local state from initialValues + defaults
  const [values, setValues] = useState<Record<string, unknown>>(() => {
    const init: Record<string, unknown> = {};
    return init;
  });

  // Sync initial values when definitions arrive or initialValues changes
  useEffect(() => {
    if (definitions.length === 0) return;
    const init: Record<string, unknown> = {};
    for (const field of definitions) {
      init[field.field_key] = getInitialValue(field, initialValues);
    }
    setValues(init);
    // Notify parent of initial state
    onChange(init);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [definitions.length, JSON.stringify(initialValues)]);

  // Return null when there are no field definitions (FR-022)
  if (!isLoading && definitions.length === 0) return null;

  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground">Loading custom fields...</p>
    );
  }

  // Group fields by section, preserving position order within each section
  const sectionMap = new Map<string, FieldDefinition[]>();
  for (const field of [...definitions].sort((a, b) => a.position - b.position)) {
    const section = field.section ?? "general";
    if (!sectionMap.has(section)) {
      sectionMap.set(section, []);
    }
    sectionMap.get(section)!.push(field);
  }

  function handleChange(key: string, value: unknown) {
    setValues((prev) => {
      const next = { ...prev, [key]: value };
      onChange(next);
      return next;
    });
  }

  return (
    <div className="grid gap-4">
      {Array.from(sectionMap.entries()).map(([section, fields]) => (
        <div key={section} className="grid gap-3">
          <h4 className="text-sm font-semibold text-muted-foreground border-b pb-1">
            {capitalize(section)}
          </h4>
          {fields.map((field) => {
            const fieldErrors = errors?.[field.field_key];
            const currentValue = values[field.field_key];

            return (
              <div key={field.field_key} className="grid gap-1.5">
                <label
                  htmlFor={`custom_${field.field_key}`}
                  className="text-sm font-medium"
                >
                  {field.label}
                  {field.required ? (
                    <span className="text-destructive"> *</span>
                  ) : null}
                </label>

                {field.field_type === "text" && (
                  <Input
                    id={`custom_${field.field_key}`}
                    type="text"
                    value={typeof currentValue === "string" ? currentValue : ""}
                    required={field.required}
                    onChange={(e) => handleChange(field.field_key, e.target.value)}
                  />
                )}

                {field.field_type === "integer" && (
                  <Input
                    id={`custom_${field.field_key}`}
                    type="number"
                    step={1}
                    value={currentValue !== "" && currentValue !== undefined && currentValue !== null ? String(currentValue) : ""}
                    required={field.required}
                    onChange={(e) =>
                      handleChange(
                        field.field_key,
                        e.target.value === "" ? "" : parseInt(e.target.value, 10),
                      )
                    }
                  />
                )}

                {field.field_type === "decimal" && (
                  <Input
                    id={`custom_${field.field_key}`}
                    type="number"
                    step={0.01}
                    value={currentValue !== "" && currentValue !== undefined && currentValue !== null ? String(currentValue) : ""}
                    required={field.required}
                    onChange={(e) =>
                      handleChange(
                        field.field_key,
                        e.target.value === "" ? "" : parseFloat(e.target.value),
                      )
                    }
                  />
                )}

                {field.field_type === "boolean" && (
                  <label
                    htmlFor={`custom_${field.field_key}`}
                    className="flex items-center gap-2 cursor-pointer"
                  >
                    <input
                      id={`custom_${field.field_key}`}
                      type="checkbox"
                      checked={Boolean(currentValue)}
                      required={field.required}
                      onChange={(e) => handleChange(field.field_key, e.target.checked)}
                      className="h-4 w-4 rounded border-input accent-primary"
                    />
                    <span className="text-sm">{field.label}</span>
                  </label>
                )}

                {field.field_type === "date" && (
                  <Input
                    id={`custom_${field.field_key}`}
                    type="date"
                    value={typeof currentValue === "string" ? currentValue : ""}
                    required={field.required}
                    onChange={(e) => handleChange(field.field_key, e.target.value)}
                  />
                )}

                {field.field_type === "select" && (
                  <select
                    id={`custom_${field.field_key}`}
                    value={typeof currentValue === "string" ? currentValue : ""}
                    required={field.required}
                    onChange={(e) => handleChange(field.field_key, e.target.value)}
                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs"
                  >
                    <option value="">Select...</option>
                    {(field.choices ?? []).map((choice) => (
                      <option key={choice} value={choice}>
                        {choice}
                      </option>
                    ))}
                  </select>
                )}

                {fieldErrors
                  ? fieldErrors.map((msg, i) => (
                      <p key={i} className="text-xs text-destructive">
                        {msg}
                      </p>
                    ))
                  : null}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
