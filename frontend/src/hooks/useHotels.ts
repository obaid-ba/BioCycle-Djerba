import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createHotel,
  deleteHotel,
  listHotels,
  updateHotel,
  type HotelListParams,
} from "@/services/hotels";
import type { HotelCreate, HotelUpdate } from "@/types";

const KEY = "hotels";

export function useHotels(params: HotelListParams) {
  return useQuery({
    queryKey: [KEY, params],
    queryFn: () => listHotels(params),
  });
}

/** All hotels (first large page) — for populating select dropdowns. */
export function useHotelOptions() {
  return useQuery({
    queryKey: [KEY, "options"],
    queryFn: () => listHotels({ page_size: 100, sort: "name" }),
    select: (data) => data.items,
  });
}

/** Invalidate every hotels list query after a mutation. */
function useInvalidateHotels() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: [KEY] });
}

export function useCreateHotel() {
  const invalidate = useInvalidateHotels();
  return useMutation({
    mutationFn: (payload: HotelCreate) => createHotel(payload),
    onSuccess: invalidate,
  });
}

export function useUpdateHotel() {
  const invalidate = useInvalidateHotels();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: HotelUpdate }) =>
      updateHotel(id, payload),
    onSuccess: invalidate,
  });
}

export function useDeleteHotel() {
  const invalidate = useInvalidateHotels();
  return useMutation({
    mutationFn: (id: string) => deleteHotel(id),
    onSuccess: invalidate,
  });
}
