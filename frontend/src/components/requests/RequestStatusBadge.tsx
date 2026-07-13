import { Badge } from "@/components/ui/badge";
import { REQUEST_STATUS_META } from "@/lib/requestStatus";
import type { RequestStatus } from "@/types";

/** Colored status badge; label + variant come from the single status map. */
export function RequestStatusBadge({ status }: { status: RequestStatus }) {
  const meta = REQUEST_STATUS_META[status];
  return <Badge variant={meta.variant}>{meta.label}</Badge>;
}
