import type { RequestStatus } from "@/types";

/**
 * Presentation + lifecycle mapping for collection requests — the single source
 * of truth on the frontend, mirroring the backend `state_machine.py`. Keeping
 * labels, badge colors, and the "what can I do next" logic here means the UI
 * never offers an action the backend would reject with a 409.
 */

type BadgeVariant =
  | "default"
  | "secondary"
  | "success"
  | "warning"
  | "destructive"
  | "outline";

interface StatusMeta {
  label: string;
  variant: BadgeVariant;
}

export const REQUEST_STATUS_META: Record<RequestStatus, StatusMeta> = {
  pending: { label: "Pending", variant: "warning" },
  ai_failed: { label: "AI failed", variant: "destructive" },
  accepted: { label: "Accepted", variant: "default" },
  rejected: { label: "Rejected", variant: "destructive" },
  on_the_way: { label: "On the way", variant: "default" },
  collected: { label: "Collected", variant: "secondary" },
  completed: { label: "Completed", variant: "success" },
};

/** Operator actions available from a given status. Empty = terminal state. */
export type RequestAction = "decide" | "on_the_way" | "collected" | "completed";

const NEXT_ACTIONS: Record<RequestStatus, RequestAction[]> = {
  pending: ["decide"],
  ai_failed: ["decide"],
  accepted: ["on_the_way"],
  on_the_way: ["collected"],
  collected: ["completed"],
  rejected: [],
  completed: [],
};

export function nextActionsFor(status: RequestStatus): RequestAction[] {
  return NEXT_ACTIONS[status];
}

export function isTerminal(status: RequestStatus): boolean {
  return NEXT_ACTIONS[status].length === 0;
}
