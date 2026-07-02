import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge Tailwind class names with conflict resolution. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** Format a number as kilograms with sensible precision. */
export function formatKg(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 1 })} kg`;
}

/** Format an ISO date string as a short, locale-aware date-time. */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}
