import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createRequest,
  decideRequest,
  deletePhoto,
  listRequests,
  transitionRequest,
  uploadPhotos,
  type RequestListParams,
} from "@/services/requests";
import type {
  CollectionRequestCreate,
  RequestDecision,
  RequestTransition,
} from "@/types";

const KEY = "requests";

export function useRequests(params: RequestListParams) {
  return useQuery({
    queryKey: [KEY, params],
    queryFn: () => listRequests(params),
  });
}

function useInvalidateRequests() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: [KEY] });
}

export function useCreateRequest() {
  const invalidate = useInvalidateRequests();
  return useMutation({
    mutationFn: ({
      payload,
      hotelId,
    }: {
      payload: CollectionRequestCreate;
      hotelId?: string;
    }) => createRequest(payload, hotelId),
    onSuccess: invalidate,
  });
}

export function useDecideRequest() {
  const invalidate = useInvalidateRequests();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: RequestDecision }) =>
      decideRequest(id, payload),
    onSuccess: invalidate,
  });
}

export function useTransitionRequest() {
  const invalidate = useInvalidateRequests();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: RequestTransition }) =>
      transitionRequest(id, payload),
    onSuccess: invalidate,
  });
}

export function useUploadPhotos() {
  const invalidate = useInvalidateRequests();
  return useMutation({
    mutationFn: ({ id, files }: { id: string; files: File[] }) =>
      uploadPhotos(id, files),
    onSuccess: invalidate,
  });
}

export function useDeletePhoto() {
  const invalidate = useInvalidateRequests();
  return useMutation({
    mutationFn: ({ requestId, photoId }: { requestId: string; photoId: string }) =>
      deletePhoto(requestId, photoId),
    onSuccess: invalidate,
  });
}
