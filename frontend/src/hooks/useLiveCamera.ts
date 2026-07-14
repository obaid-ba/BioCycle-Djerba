import { useQuery } from "@tanstack/react-query";

import { getLiveCamera } from "@/services/camera";

/**
 * Polls the live camera summary. Returns no data (and no error surfaced to the
 * UI) when the user has no linked camera — the panel simply hides itself.
 * `retry: false` so a 404 (no camera) doesn't spam retries.
 */
export function useLiveCamera() {
  return useQuery({
    queryKey: ["firebase", "live"],
    queryFn: getLiveCamera,
    refetchInterval: 5000,
    retry: false,
  });
}
