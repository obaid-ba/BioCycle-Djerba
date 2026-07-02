import type {
  AlertSeverity,
  AlertStatus,
  BinStatus,
  HotelStatus,
} from "@/types";

type Variant = "default" | "secondary" | "success" | "warning" | "destructive";

export const hotelStatusVariant: Record<HotelStatus, Variant> = {
  active: "success",
  onboarding: "warning",
  inactive: "secondary",
};

export const binStatusVariant: Record<BinStatus, Variant> = {
  online: "success",
  maintenance: "warning",
  offline: "secondary",
};

export const alertSeverityVariant: Record<AlertSeverity, Variant> = {
  info: "secondary",
  warning: "warning",
  critical: "destructive",
};

export const alertStatusVariant: Record<AlertStatus, Variant> = {
  open: "destructive",
  acknowledged: "warning",
  resolved: "success",
};

/** Replace an enum's underscores with spaces for display (e.g. bin_full). */
export function humanize(value: string): string {
  return value.replace(/_/g, " ");
}
