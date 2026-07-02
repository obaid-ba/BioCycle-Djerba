import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createCollection,
  deleteCollection,
  listCollections,
  predictCollection,
  updateCollection,
  type CollectionListParams,
} from "@/services/collections";
import type { WasteCollectionCreate, WasteCollectionUpdate } from "@/types";

const KEY = "collections";

export function useCollections(params: CollectionListParams) {
  return useQuery({
    queryKey: [KEY, params],
    queryFn: () => listCollections(params),
  });
}

function useInvalidateCollections() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: [KEY] });
}

export function useCreateCollection() {
  const invalidate = useInvalidateCollections();
  return useMutation({
    mutationFn: (payload: WasteCollectionCreate) => createCollection(payload),
    onSuccess: invalidate,
  });
}

export function useUpdateCollection() {
  const invalidate = useInvalidateCollections();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: WasteCollectionUpdate }) =>
      updateCollection(id, payload),
    onSuccess: invalidate,
  });
}

export function useDeleteCollection() {
  const invalidate = useInvalidateCollections();
  return useMutation({
    mutationFn: (id: string) => deleteCollection(id),
    onSuccess: invalidate,
  });
}

export function usePredictCollection() {
  return useMutation({
    mutationFn: (id: string) => predictCollection(id),
  });
}
