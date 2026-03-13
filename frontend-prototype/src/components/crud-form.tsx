"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export interface FieldConfig {
  name: string;
  label: string;
  type: "text" | "number" | "email" | "password" | "select" | "textarea";
  required?: boolean;
  options?: { label: string; value: string }[];
  placeholder?: string;
}

interface CrudFormProps {
  fields: FieldConfig[];
  initialValues?: Record<string, string>;
  onSubmit: (values: Record<string, string>) => void | Promise<void>;
  errors?: Record<string, string[]>;
  mode: "create" | "edit";
  title?: string;
  isLoading?: boolean;
}

export function CrudForm({
  fields,
  initialValues,
  onSubmit,
  errors,
  mode,
  title,
  isLoading,
}: CrudFormProps) {
  const [values, setValues] = useState<Record<string, string>>(() => {
    const defaults: Record<string, string> = {};
    for (const f of fields) {
      defaults[f.name] = initialValues?.[f.name] ?? "";
    }
    return defaults;
  });

  function handleChange(name: string, value: string) {
    setValues((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    await onSubmit(values);
  }

  return (
    <Card>
      {title ? (
        <CardHeader>
          <CardTitle className="text-base">{title}</CardTitle>
        </CardHeader>
      ) : null}
      <CardContent>
        <form onSubmit={handleSubmit} className="grid gap-4">
          {fields.map((field) => {
            const fieldErrors = errors?.[field.name];
            return (
              <div key={field.name} className="grid gap-1.5">
                <label
                  htmlFor={field.name}
                  className="text-sm font-medium"
                >
                  {field.label}
                  {field.required ? (
                    <span className="text-destructive"> *</span>
                  ) : null}
                </label>
                {field.type === "select" ? (
                  <select
                    id={field.name}
                    value={values[field.name]}
                    onChange={(e) => handleChange(field.name, e.target.value)}
                    required={field.required}
                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs"
                  >
                    <option value="">Select...</option>
                    {field.options?.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                ) : field.type === "textarea" ? (
                  <textarea
                    id={field.name}
                    value={values[field.name]}
                    onChange={(e) => handleChange(field.name, e.target.value)}
                    required={field.required}
                    placeholder={field.placeholder}
                    rows={3}
                    className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs"
                  />
                ) : (
                  <Input
                    id={field.name}
                    type={field.type}
                    value={values[field.name]}
                    onChange={(e) => handleChange(field.name, e.target.value)}
                    required={field.required}
                    placeholder={field.placeholder}
                  />
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
          <Button type="submit" disabled={isLoading}>
            {isLoading
              ? "Saving..."
              : mode === "create"
                ? "Create"
                : "Update"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
