import { apiClient, parseAxiosError, unwrap } from "./apiClient";
import type {
  EvaluationRequest,
  EvaluationResponse,
  SuccessResponse,
} from "@/types/api";

export const evaluationApi = {
  /** POST /api/v1/evaluations/compare */
  compare: async (body: EvaluationRequest): Promise<EvaluationResponse> => {
    try {
      const res = await apiClient.post<SuccessResponse<EvaluationResponse>>(
        "/api/v1/evaluations/compare",
        body,
      );
      return unwrap(res.data);
    } catch (err) {
      throw parseAxiosError(err);
    }
  },
};
