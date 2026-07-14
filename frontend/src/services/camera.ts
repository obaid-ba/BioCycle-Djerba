import { api } from "@/services/api";
import type { LiveCameraSummary } from "@/types";

/** GET /firebase/live — current camera detection summary (or 404 if none linked). */
export async function getLiveCamera(): Promise<LiveCameraSummary> {
  const { data } = await api.get<LiveCameraSummary>("/firebase/live");
  return data;
}
