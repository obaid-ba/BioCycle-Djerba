import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createBin,
  deleteBin,
  listBins,
  updateBin,
  type BinListParams,
} from "@/services/bins";
import type { SmartBinCreate, SmartBinUpdate } from "@/types";

const KEY = "bins";

export function useBins(params: BinListParams) {
  return useQuery({
    queryKey: [KEY, params],
    queryFn: () => listBins(params),
  });
}

function useInvalidateBins() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: [KEY] });
}

export function useCreateBin() {
  const invalidate = useInvalidateBins();
  return useMutation({
    mutationFn: (payload: SmartBinCreate) => createBin(payload),
    onSuccess: invalidate,
  });
}

export function useUpdateBin() {
  const invalidate = useInvalidateBins();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: SmartBinUpdate }) =>
      updateBin(id, payload),
    onSuccess: invalidate,
  });
}

export function useDeleteBin() {
  const invalidate = useInvalidateBins();
  return useMutation({
    mutationFn: (id: string) => deleteBin(id),
    onSuccess: invalidate,
  });
}
