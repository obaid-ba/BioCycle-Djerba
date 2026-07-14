import { useQuery } from "@tanstack/react-query";

import { getEstimate, getLiveCamera } from "@/services/camera";

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

/**
 * Estimate for a container count against the live camera composition. Refetches
 * on a short interval so the estimate tracks the camera in real time. Disabled
 * for a non-positive count.
 */
export function useEstimate(containers: number) {
  return useQuery({
    queryKey: ["firebase", "estimate", containers],
    queryFn: () => getEstimate(containers),
    enabled: containers > 0,
    refetchInterval: 5000,
    retry: false,
  });
}
