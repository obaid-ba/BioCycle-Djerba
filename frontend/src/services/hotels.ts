import { api } from "@/services/api";
import type { Hotel, HotelCreate, HotelStatus, HotelUpdate, Page } from "@/types";

export interface HotelListParams {
  page?: number;
  page_size?: number;
  search?: string;
  status?: HotelStatus;
  sort?: string;
}

export async function listHotels(params: HotelListParams): Promise<Page<Hotel>> {
  const { data } = await api.get<Page<Hotel>>("/hotels", { params });
  return data;
}

export async function createHotel(payload: HotelCreate): Promise<Hotel> {
  const { data } = await api.post<Hotel>("/hotels", payload);
  return data;
}

export async function updateHotel(id: string, payload: HotelUpdate): Promise<Hotel> {
  const { data } = await api.patch<Hotel>(`/hotels/${id}`, payload);
  return data;
}

export async function deleteHotel(id: string): Promise<void> {
  await api.delete(`/hotels/${id}`);
}
