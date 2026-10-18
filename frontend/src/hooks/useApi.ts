/**
 * Custom hooks for data fetching via TanStack Query.
 * All hooks use staleTime to prevent unnecessary refetches.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cityApi } from "@/services/cityApi";
import { weatherApi } from "@/services/weatherApi";
import { simulationApi } from "@/services/simulationApi";
import { recommendationApi } from "@/services/recommendationApi";
import { evaluationApi } from "@/services/evaluationApi";
import type {
  RecommendationRequest,
  ScenarioInput,
  EvaluationRequest,
} from "@/types/api";

// ── Query Keys ─────────────────────────────────────────────────────────────────

export const QUERY_KEYS = {
  health: ["health"] as const,
  cityMetadata: ["city", "metadata"] as const,
  cityGraph: ["city", "graph"] as const,
  weatherStatus: (seed: number) => ["weather", "status", seed] as const,
  weatherCurrent: (seed: number) => ["weather", "current", seed] as const,
  weatherWarnings: (seed: number) => ["weather", "warnings", seed] as const,
  scenarios: ["scenarios"] as const,
  scenario: (id: string) => ["scenarios", id] as const,
  simulation: (id: string) => ["simulations", id] as const,
  simulationList: ["simulations", "list"] as const,
  cascade: (id: string) => ["simulations", id, "cascade"] as const,
  recommendations: (simId: string) => ["recommendations", simId] as const,
  evaluation: ["evaluations", "compare"] as const,
};

// ── City Hooks ─────────────────────────────────────────────────────────────────

export function useHealth() {
  return useQuery({
    queryKey: QUERY_KEYS.health,
    queryFn: cityApi.getHealth,
    staleTime: 30_000,
    retry: 2,
  });
}

export function useCityMetadata() {
  return useQuery({
    queryKey: QUERY_KEYS.cityMetadata,
    queryFn: cityApi.getMetadata,
    staleTime: 5 * 60_000,
    retry: 2,
  });
}

export function useCityGraph() {
  return useQuery({
    queryKey: QUERY_KEYS.cityGraph,
    queryFn: cityApi.getGraph,
    staleTime: 10 * 60_000, // graph changes rarely
    retry: 2,
  });
}

// ── Weather Hooks ──────────────────────────────────────────────────────────────

export function useWeatherStatus(seed = 42) {
  return useQuery({
    queryKey: QUERY_KEYS.weatherStatus(seed),
    queryFn: () => weatherApi.getStatus(seed),
    staleTime: 60_000,
    retry: 1,
  });
}

export function useWeatherCurrent(seed = 42) {
  return useQuery({
    queryKey: QUERY_KEYS.weatherCurrent(seed),
    queryFn: () => weatherApi.getCurrent(seed),
    staleTime: 60_000,
    retry: 1,
  });
}

export function useWeatherWarnings(seed = 42) {
  return useQuery({
    queryKey: QUERY_KEYS.weatherWarnings(seed),
    queryFn: () => weatherApi.getWarnings(seed),
    staleTime: 60_000,
    retry: 1,
  });
}

// ── Scenario Hooks ─────────────────────────────────────────────────────────────

export function useScenarios() {
  return useQuery({
    queryKey: QUERY_KEYS.scenarios,
    queryFn: simulationApi.listScenarios,
    staleTime: 5 * 60_000,
  });
}

// ── Simulation Hooks ───────────────────────────────────────────────────────────

export function useSimulationList() {
  return useQuery({
    queryKey: QUERY_KEYS.simulationList,
    queryFn: simulationApi.listSimulations,
    staleTime: 10_000,
  });
}

export function useSimulation(simulationId: string | null) {
  return useQuery({
    queryKey: QUERY_KEYS.simulation(simulationId ?? ""),
    queryFn: () => simulationApi.getSimulation(simulationId!),
    enabled: !!simulationId,
    staleTime: 30_000,
  });
}

export function useCascade(simulationId: string | null) {
  return useQuery({
    queryKey: QUERY_KEYS.cascade(simulationId ?? ""),
    queryFn: () => simulationApi.getCascade(simulationId!),
    enabled: !!simulationId,
    staleTime: 30_000,
  });
}

export function useRunSimulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: ScenarioInput) => simulationApi.runSimulation(input),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: QUERY_KEYS.simulationList });
    },
  });
}

// ── Recommendation Hook ────────────────────────────────────────────────────────

export function useRecommendations(simulationId: string | null) {
  return useQuery({
    queryKey: QUERY_KEYS.recommendations(simulationId ?? ""),
    queryFn: () =>
      recommendationApi.getRecommendations({
        simulation_id: simulationId!,
        objective_lambda: 0.3,
        objective_mu: 0.1,
        max_recommendations: 5,
      }),
    enabled: !!simulationId,
    staleTime: 30_000,
  });
}

export function useRequestRecommendations() {
  return useMutation({
    mutationFn: (body: RecommendationRequest) =>
      recommendationApi.getRecommendations(body),
  });
}

// ── Evaluation Hook ────────────────────────────────────────────────────────────

export function useRunEvaluation() {
  return useMutation({
    mutationFn: (body: EvaluationRequest) => evaluationApi.compare(body),
  });
}
