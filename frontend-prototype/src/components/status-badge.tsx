import { Badge } from "@/components/ui/badge";

type BadgeVariant = "success" | "warning" | "error" | "default";

const STATUS_MAP: Record<string, BadgeVariant> = {
  active: "success",
  pass: "success",
  authorized: "success",
  approved: "success",
  completed: "success",
  pending: "warning",
  draft: "warning",
  processing: "warning",
  error: "error",
  failed: "error",
  rejected: "error",
  cancelled: "error",
  inactive: "error",
};

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  success: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  warning:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  error: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  default: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
};

interface StatusBadgeProps {
  status: string;
  variant?: BadgeVariant;
}

export function StatusBadge({ status, variant }: StatusBadgeProps) {
  const resolved =
    variant ?? STATUS_MAP[status.toLowerCase()] ?? "default";

  return (
    <Badge variant="outline" className={VARIANT_CLASSES[resolved]}>
      {status}
    </Badge>
  );
}
