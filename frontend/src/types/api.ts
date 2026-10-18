/**
 * API type definitions mirroring the CascadeIQ backend Pydantic schemas.
 * Field names match the backend exactly – do not rename without coordinating
 * a backend schema change.
 */

// ── Common ─────────────────────────────────────────────────────────────────────

export interface BoundingBox {
  min_lat: number;
  min_lon: number;
  max_lat: number;
  max_lon: number;
}

export interface SuccessResponse<T> {
  data: T;
  metadata: Record<string, unknown>;
  generated_at: string;
}

export interface ErrorResponse {
  error: string;
  message: string;
  detail: Record<string, unknown>;
}

// ── City ───────────────────────────────────────────────────────────────────────

export type NodeType = "intersection" | "hospital" | "facility";
export type RoadStatus = "OPEN" | "DEGRADED" | "CLOSED";

export interface NodeSchema {
  node_id: string;
  lat: number;
  lon: number;
  node_type: NodeType;
}

export interface EdgeSchema {
  edge_id: string;
  source_node: string;
  target_node: string;
  length_m: number;
  road_type: string;
  status: RoadStatus;
  speed_kmh: number;
  travel_time_s: number;
  oneway: boolean;
  flood_risk: number;
  confidence: number | null;
}

export interface GraphMetadataSchema {
  node_count: number;
  edge_count: number;
  bbox: BoundingBox;
  crs: string;
  source: string;
  retrieved_at: string;
  network_type: string;
}

export interface CityGraphResponse {
  metadata: GraphMetadataSchema;
  nodes: NodeSchema[];
  edges: EdgeSchema[];
}

export interface CityMetadataResponse {
  district: string;
  state: string;
  country: string;
  area_km2: number;
  bbox: BoundingBox;
  crs: string;
  population_approx: number;
  data_sources: string[];
  boundary_provenance: string;
  boundary_note: string;
}

// ── Weather ────────────────────────────────────────────────────────────────────

export type WeatherSource = "IMD" | "SYNTHETIC" | "HISTORICAL";
export type WarningSeverity = "WATCH" | "WARNING" | "SEVERE" | "EXTREME";

export interface RainfallObservation {
  station_id: string;
  lat: number;
  lon: number;
  rainfall_mm_1h: number;
  rainfall_mm_24h: number;
  observed_at: string;
  source: WeatherSource;
}

export interface WeatherWarning {
  warning_id: string;
  warning_type: string;
  severity: WarningSeverity;
  description: string;
  issued_at: string;
  valid_until: string;
  affected_area: BoundingBox | null;
  source: WeatherSource;
}

export interface WeatherStatus {
  current_observations: RainfallObservation[];
  active_warnings: WeatherWarning[];
  data_freshness: string;
  disclaimer: string;
}

// ── Scenarios ──────────────────────────────────────────────────────────────────

export type WeatherMode = "synthetic" | "historical" | "live";

export interface ScenarioConfig {
  scenario_id: string;
  display_name: string;
  description: string;
  weather_mode: WeatherMode;
  default_simulation_steps: number;
  tags: string[];
}

export interface HospitalInput {
  hospital_id: string;
  name: string;
  lat: number;
  lon: number;
  total_beds: number;
  available_beds: number;
  icu_beds: number;
}

export interface AmbulanceInput {
  ambulance_id: string;
  lat: number;
  lon: number;
  is_available: boolean;
  assigned_request_id: string | null;
}

export interface EmergencyRequestInput {
  request_id: string;
  origin_lat: number;
  origin_lon: number;
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  created_at?: string;
}

export interface RoadDisruption {
  edge_id: string;
  status: RoadStatus;
  severity: number;
  confidence: number;
  cause: string;
  estimated_by: string;
}

export interface ScenarioInput {
  scenario_id: string;
  seed: number;
  hospitals: HospitalInput[];
  ambulances: AmbulanceInput[];
  emergency_requests: EmergencyRequestInput[];
  road_disruptions: RoadDisruption[];
  simulation_steps: number;
  weather_mode: WeatherMode;
}

// ── Simulation ─────────────────────────────────────────────────────────────────

export type SimulationStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";

export interface RouteSegment {
  edge_ids: string[];
  total_distance_m: number;
  total_time_s: number;
  is_feasible: boolean;
}

export interface AmbulanceAssignment {
  ambulance_id: string;
  request_id: string;
  hospital_id: string | null;
  route: RouteSegment;
  estimated_arrival_s: number;
}

export interface CascadeEventSchema {
  step_index: number;
  event_type: string;
  description: string;
  affected_entity_id: string;
  severity: number;
  provenance: string;
}

export interface CascadeStep {
  step_index: number;
  timestamp: string;
  active_disruptions: string[];
  unreachable_requests: string[];
  isolated_facilities: string[];
  hospital_loads: Record<string, number>;
  cascade_events: CascadeEventSchema[];
}

export interface SimulationResult {
  simulation_id: string;
  scenario_id: string;
  seed: number;
  status: SimulationStatus;
  steps: CascadeStep[];
  final_assignments: AmbulanceAssignment[];
  created_at: string;
  completed_at: string | null;
  disclaimer: string;
}

// ── Recommendations ────────────────────────────────────────────────────────────

export type InterventionType = "REROUTE" | "DIVERT" | "PREPOSITION";

export interface InterventionAction {
  action_id: string;
  type: InterventionType;
  description: string;
  target_ambulance_id: string | null;
  target_request_id: string | null;
  target_hospital_id: string | null;
  new_route: RouteSegment | null;
  feasible: boolean;
  infeasibility_reason: string | null;
  objective_score: number | null;
  response_time_s: number | null;
  hospital_overload: number | null;
  intervention_cost: number;
}

export interface RecommendationRequest {
  simulation_id: string;
  objective_lambda: number;
  objective_mu: number;
  max_recommendations: number;
}

export interface RecommendationResult {
  simulation_id: string;
  ranked_interventions: InterventionAction[];
  objective_scores: Record<string, number>;
  computation_latency_ms: number;
  method_note: string;
}

// ── Evaluation ─────────────────────────────────────────────────────────────────

export interface EvaluationMetric {
  name: string;
  value: number | null;
  unit: string;
  denominator: number | null;
  explanation: string;
}

export interface PolicyResult {
  policy_name: string;
  metrics: EvaluationMetric[];
  simulation_id: string;
}

export interface EvaluationRequest {
  scenario_input: ScenarioInput;
  objective_lambda: number;
  objective_mu: number;
}

export interface EvaluationResponse {
  baseline: PolicyResult;
  cascadeiq: PolicyResult;
  comparison_note: string;
  ran_at: string;
}

// ── Health ─────────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  version: string;
  graph_loaded: boolean;
  study_area: string;
  timestamp: string;
}
