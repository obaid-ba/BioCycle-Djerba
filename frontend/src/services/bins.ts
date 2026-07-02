import { api } from "@/services/api";
import type {
  BinStatus,
  BinType,
  Page,
  SmartBin,
  SmartBinCreate,
  SmartBinUpdate,
} from "@/types";

export interface BinListParams {
  page?: number;
  page_size?: number;
  search?: string;
  hotel_id?: string;
  status?: BinStatus;
  bin_type?: BinType;
  sort?: string;
}

export async function listBins(params: BinListParams): Promise<Page<SmartBin>> {
  const { data } = await api.get<Page<SmartBin>>("/bins", { params });
  return data;
}

export async function createBin(payload: SmartBinCreate): Promise<SmartBin> {
  const { data } = await api.post<SmartBin>("/bins", payload);
  return data;
}

export async function updateBin(id: string, payload: SmartBinUpdate): Promise<SmartBin> {
  const { data } = await api.patch<SmartBin>(`/bins/${id}`, payload);
  return data;
}

export async function deleteBin(id: string): Promise<void> {
  await api.delete(`/bins/${id}`);
}
