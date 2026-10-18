import { apiClient, parseAxiosError, unwrap } from "./apiClient";
import type {
  ScenarioConfig,
  ScenarioInput,
  SimulationResult,
  CascadeStep,
  SuccessResponse,
} from "@/types/api";

export const simulationApi = {
  /** GET /api/v1/scenarios */
  listScenarios: async (): Promise<ScenarioConfig[]> => {
    try {
      const res = await apiClient.get<SuccessResponse<ScenarioConfig[]>>(
        "/api/v1/scenarios",
      );
      return unwrap(res.data);
    } catch (err) {
      throw parseAxiosError(err);
    }
  },

  /** GET /api/v1/scenarios/{id} */
  getScenario: async (scenarioId: string): Promise<ScenarioConfig> => {
    try {
      const res = await apiClient.get<SuccessResponse<ScenarioConfig>>(
        `/api/v1/scenarios/${scenarioId}`,
      );
      return unwrap(res.data);
    } catch (err) {
      throw parseAxiosError(err);
    }
  },

  /** POST /api/v1/simulations */
  runSimulation: async (input: ScenarioInput): Promise<SimulationResult> => {
    try {
      const res = await apiClient.post<SuccessResponse<SimulationResult>>(
        "/api/v1/simulations",
        input,
      );
      return unwrap(res.data);
    } catch (err) {
      throw parseAxiosError(err);
    }
  },

  /** GET /api/v1/simulations */
  listSimulations: async (): Promise<string[]> => {
    try {
      const res = await apiClient.get<SuccessResponse<string[]>>(
        "/api/v1/simulations",
      );
      return unwrap(res.data);
    } catch (err) {
      throw parseAxiosError(err);
    }
  },

  /** GET /api/v1/simulations/{id} */
  getSimulation: async (simulationId: string): Promise<SimulationResult> => {
    try {
      const res = await apiClient.get<SuccessResponse<SimulationResult>>(
        `/api/v1/simulations/${simulationId}`,
      );
      return unwrap(res.data);
    } catch (err) {
      throw parseAxiosError(err);
    }
  },

  /** GET /api/v1/simulations/{id}/cascade */
  getCascade: async (
    simulationId: string,
    step?: number,
  ): Promise<CascadeStep[]> => {
    try {
      const res = await apiClient.get<SuccessResponse<CascadeStep[]>>(
        `/api/v1/simulations/${simulationId}/cascade`,
        { params: step !== undefined ? { step } : undefined },
      );
      return unwrap(res.data);
    } catch (err) {
      throw parseAxiosError(err);
    }
  },
};
