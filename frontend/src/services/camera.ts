import { api } from "@/services/api";
import type { CameraEstimate, LiveCameraSummary } from "@/types";

/** GET /firebase/live — current camera detection summary (or 404 if none linked). */
export async function getLiveCamera(): Promise<LiveCameraSummary> {
  const { data } = await api.get<LiveCameraSummary>("/firebase/live");
  return data;
}

/** GET /firebase/estimate — outputs for N containers at the current camera purity. */
export async function getEstimate(containers: number): Promise<CameraEstimate> {
  const { data } = await api.get<CameraEstimate>("/firebase/estimate", {
    params: { containers },
  });
  return data;
}
