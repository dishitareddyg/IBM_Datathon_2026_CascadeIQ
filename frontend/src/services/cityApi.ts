import { apiClient, parseAxiosError, unwrap } from "./apiClient";
import type {
  CityGraphResponse,
  CityMetadataResponse,
  HealthResponse,
  SuccessResponse,
} from "@/types/api";

export const cityApi = {
  /** GET /api/v1/city/metadata */
  getMetadata: async (): Promise<CityMetadataResponse> => {
    try {
      const res = await apiClient.get<CityMetadataResponse>(
        "/api/v1/city/metadata",
      );
      return res.data;
    } catch (err) {
      throw parseAxiosError(err);
    }
  },

  /** GET /api/v1/city/graph */
  getGraph: async (): Promise<CityGraphResponse> => {
    try {
      const res =
        await apiClient.get<CityGraphResponse>("/api/v1/city/graph");
      return res.data;
    } catch (err) {
      throw parseAxiosError(err);
    }
  },

  /** GET /health */
  getHealth: async (): Promise<HealthResponse> => {
    try {
      const res = await apiClient.get<HealthResponse>("/health");
      return res.data;
    } catch (err) {
      throw parseAxiosError(err);
    }
  },
};
