import { apiClient, parseAxiosError, unwrap } from "./apiClient";
import type {
  RainfallObservation,
  WeatherStatus,
  WeatherWarning,
  SuccessResponse,
} from "@/types/api";

export const weatherApi = {
  /** GET /api/v1/weather/current */
  getCurrent: async (seed = 42): Promise<RainfallObservation[]> => {
    try {
      const res = await apiClient.get<RainfallObservation[]>(
        "/api/v1/weather/current",
        { params: { seed } },
      );
      return res.data;
    } catch (err) {
      throw parseAxiosError(err);
    }
  },

  /** GET /api/v1/weather/warnings */
  getWarnings: async (seed = 42): Promise<WeatherWarning[]> => {
    try {
      const res = await apiClient.get<WeatherWarning[]>(
        "/api/v1/weather/warnings",
        { params: { seed } },
      );
      return res.data;
    } catch (err) {
      throw parseAxiosError(err);
    }
  },

  /** GET /api/v1/weather/status */
  getStatus: async (seed = 42): Promise<WeatherStatus> => {
    try {
      const res = await apiClient.get<WeatherStatus>(
        "/api/v1/weather/status",
        { params: { seed } },
      );
      return res.data;
    } catch (err) {
      throw parseAxiosError(err);
    }
  },
};
