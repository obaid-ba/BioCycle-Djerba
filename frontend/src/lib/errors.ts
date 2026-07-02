import { AxiosError } from "axios";

import type { ApiError } from "@/types";

/** Turn an unknown error (usually an AxiosError) into a user-facing message. */
export function messageFromError(error: unknown, fallback = "Something went wrong."): string {
  if (error instanceof AxiosError) {
    if (!error.response) return "Cannot reach the server. Please try again.";
    if (error.response.status === 401) return "Your session has expired. Please sign in again.";
    if (error.response.status === 403) return "You don't have permission to do that.";
    const data = error.response.data as ApiError | undefined;
    if (data?.error?.message) return data.error.message;
  }
  return fallback;
}
