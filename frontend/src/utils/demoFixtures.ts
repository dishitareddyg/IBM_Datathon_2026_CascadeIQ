/**
 * Bundled demo fixtures for offline / API-unavailable mode.
 *
 * These are clearly labelled as fixture data in the UI.
 * They are NOT presented as live observations.
 *
 * Used only when the backend is unreachable and the user
 * explicitly enables demo mode.
 */
import type {
  ScenarioConfig,
  HospitalInput,
  AmbulanceInput,
  EmergencyRequestInput,
  RoadDisruption,
  ScenarioInput,
  WeatherStatus,
} from "@/types/api";

// ── Demo Hospitals ─────────────────────────────────────────────────────────────

export const DEMO_HOSPITALS: HospitalInput[] = [
  {
    hospital_id: "H1",
    name: "Victoria Hospital",
    lat: 12.9612,
    lon: 77.5726,
    total_beds: 200,
    available_beds: 80,
    icu_beds: 20,
  },
  {
    hospital_id: "H2",
    name: "Bowring & Lady Curzon Hospital",
    lat: 12.9785,
    lon: 77.6033,
    total_beds: 300,
    available_beds: 120,
    icu_beds: 35,
  },
  {
    hospital_id: "H3",
    name: "Manipal Hospital (Hebbal)",
    lat: 13.0478,
    lon: 77.5912,
    total_beds: 600,
    available_beds: 250,
    icu_beds: 60,
  },
];

// ── Demo Ambulances ────────────────────────────────────────────────────────────

export const DEMO_AMBULANCES: AmbulanceInput[] = [
  { ambulance_id: "A1", lat: 12.9767, lon: 77.5713, is_available: true, assigned_request_id: null },
  { ambulance_id: "A2", lat: 12.9520, lon: 77.5900, is_available: true, assigned_request_id: null },
  { ambulance_id: "A3", lat: 13.0300, lon: 77.5500, is_available: true, assigned_request_id: null },
];

// ── Demo Emergency Requests ────────────────────────────────────────────────────

export const DEMO_REQUESTS: EmergencyRequestInput[] = [
  { request_id: "R1", origin_lat: 12.9352, origin_lon: 77.6245, priority: "CRITICAL" },
  { request_id: "R2", origin_lat: 12.9716, origin_lon: 77.5946, priority: "HIGH" },
  { request_id: "R3", origin_lat: 13.0100, origin_lon: 77.5700, priority: "MEDIUM" },
];

// ── Demo Road Disruptions ──────────────────────────────────────────────────────

export const DEMO_DISRUPTIONS: RoadDisruption[] = [
  {
    edge_id: "demo-edge-1",
    status: "CLOSED",
    severity: 0.9,
    confidence: 0.85,
    cause: "Flash flood — Koramangala (simulated)",
    estimated_by: "flood_risk_model_v1",
  },
  {
    edge_id: "demo-edge-2",
    status: "DEGRADED",
    severity: 0.5,
    confidence: 0.7,
    cause: "Waterlogging — BTM Layout (simulated)",
    estimated_by: "flood_risk_model_v1",
  },
];

// ── Demo Scenario Input ────────────────────────────────────────────────────────

export const DEMO_SCENARIO_INPUT: ScenarioInput = {
  scenario_id: "flood_koramangala_2024",
  seed: 42,
  hospitals: DEMO_HOSPITALS,
  ambulances: DEMO_AMBULANCES,
  emergency_requests: DEMO_REQUESTS,
  road_disruptions: DEMO_DISRUPTIONS,
  simulation_steps: 15,
  weather_mode: "synthetic",
};

// ── Demo Weather Status ────────────────────────────────────────────────────────

export const DEMO_WEATHER_STATUS: WeatherStatus = {
  current_observations: [
    {
      station_id: "BLR-KOR-01",
      lat: 12.9352,
      lon: 77.6245,
      rainfall_mm_1h: 28.4,
      rainfall_mm_24h: 87.2,
      observed_at: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
      source: "SYNTHETIC",
    },
    {
      station_id: "BLR-HBL-01",
      lat: 13.0478,
      lon: 77.5912,
      rainfall_mm_1h: 12.1,
      rainfall_mm_24h: 43.6,
      observed_at: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
      source: "SYNTHETIC",
    },
  ],
  active_warnings: [
    {
      warning_id: "W-DEMO-01",
      warning_type: "HEAVY_RAIN",
      severity: "SEVERE",
      description:
        "Heavy to very heavy rainfall expected over Bengaluru Urban district. Possible waterlogging in low-lying areas.",
      issued_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      valid_until: new Date(Date.now() + 6 * 60 * 60 * 1000).toISOString(),
      affected_area: null,
      source: "SYNTHETIC",
    },
  ],
  data_freshness: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
  disclaimer:
    "⚠️  Weather data shown here is SIMULATED for research and educational purposes. It does NOT represent actual IMD observations. Do not use for real emergency decision-making.",
};

// ── Bundled Scenario Catalogue ─────────────────────────────────────────────────

export const DEMO_SCENARIOS: ScenarioConfig[] = [
  {
    scenario_id: "flood_koramangala_2024",
    display_name: "Koramangala Flash Flood — 2024",
    description:
      "Simulates the August 2024 flash-flood event in Koramangala, Bengaluru. Multiple arterial roads are partially or fully inundated. Hospitals in the southern corridor experience increased demand while northern routes remain largely passable.",
    weather_mode: "synthetic",
    default_simulation_steps: 15,
    tags: ["flood", "koramangala", "high-severity", "2024"],
  },
  {
    scenario_id: "monsoon_north_blr_moderate",
    display_name: "North Bengaluru Moderate Monsoon",
    description:
      "A moderate monsoon scenario affecting Hebbal, Yelahanka, and Kengeri. Road degradation is spread across the network rather than concentrated in a single locality.",
    weather_mode: "synthetic",
    default_simulation_steps: 10,
    tags: ["monsoon", "north-bengaluru", "moderate"],
  },
  {
    scenario_id: "extreme_rainfall_citywide",
    display_name: "Extreme Citywide Rainfall — Stress Test",
    description:
      "A high-severity stress-test scenario in which ≥100 mm/24h rainfall is recorded across all monitoring stations, triggering CRITICAL flood risk across the district.",
    weather_mode: "synthetic",
    default_simulation_steps: 25,
    tags: ["extreme", "stress-test", "citywide", "critical"],
  },
];
