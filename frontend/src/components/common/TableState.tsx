import { AlertTriangle, Inbox } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { TableCell, TableRow } from "@/components/ui/table";

interface TableStateProps {
  colSpan: number;
  isLoading: boolean;
  isError: boolean;
  isEmpty: boolean;
  emptyLabel?: string;
  onRetry?: () => void;
  /** Number of skeleton rows to show while loading. */
  skeletonRows?: number;
}

/**
 * Renders the loading / error / empty body for a table. Returns null when there
 * is real data to show, so the caller can render its rows unconditionally after.
 */
export function TableState({
  colSpan,
  isLoading,
  isError,
  isEmpty,
  emptyLabel = "No records found.",
  onRetry,
  skeletonRows = 5,
}: TableStateProps) {
  if (isLoading) {
    return (
      <>
        {Array.from({ length: skeletonRows }).map((_, i) => (
          <TableRow key={i}>
            <TableCell colSpan={colSpan}>
              <Skeleton className="h-5 w-full" />
            </TableCell>
          </TableRow>
        ))}
      </>
    );
  }

  if (isError) {
    return (
      <TableRow>
        <TableCell colSpan={colSpan}>
          <div className="flex flex-col items-center gap-3 py-10 text-center">
            <AlertTriangle className="size-6 text-warning" />
            <p className="text-sm text-muted-foreground">Could not load data.</p>
            {onRetry && (
              <Button variant="outline" size="sm" onClick={onRetry}>
                Retry
              </Button>
            )}
          </div>
        </TableCell>
      </TableRow>
    );
  }

  if (isEmpty) {
    return (
      <TableRow>
        <TableCell colSpan={colSpan}>
          <div className="flex flex-col items-center gap-2 py-10 text-center">
            <Inbox className="size-6 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">{emptyLabel}</p>
          </div>
        </TableCell>
      </TableRow>
    );
  }

  return null;
}
