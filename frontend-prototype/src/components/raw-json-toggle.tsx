"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

interface RawJsonToggleProps {
  data: unknown;
  label?: string;
}

export function RawJsonToggle({ data, label = "Raw JSON" }: RawJsonToggleProps) {
  const [open, setOpen] = useState(false);

  return (
    <div>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setOpen((v) => !v)}
        className="text-xs text-muted-foreground"
      >
        {open ? "Hide" : "Show"} {label}
      </Button>
      {open ? (
        <pre className="mt-2 max-h-80 overflow-auto rounded bg-muted p-3 text-xs">
          <code>{JSON.stringify(data, null, 2)}</code>
        </pre>
      ) : null}
    </div>
  );
}
