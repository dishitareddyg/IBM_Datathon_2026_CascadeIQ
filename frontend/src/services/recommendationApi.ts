import { apiClient, parseAxiosError, unwrap } from "./apiClient";
import type {
  RecommendationRequest,
  RecommendationResult,
  SuccessResponse,
} from "@/types/api";

export const recommendationApi = {
  /** POST /api/v1/recommendations */
  getRecommendations: async (
    body: RecommendationRequest,
  ): Promise<RecommendationResult> => {
    try {
      const res = await apiClient.post<SuccessResponse<RecommendationResult>>(
        "/api/v1/recommendations",
        body,
      );
      return unwrap(res.data);
    } catch (err) {
      throw parseAxiosError(err);
    }
  },
};
