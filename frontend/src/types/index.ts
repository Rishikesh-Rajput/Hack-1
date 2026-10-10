export type AircraftStatus = 'ACTIVE' | 'MANEUVERING' | 'RETURNING' | 'EXITED';

export interface Position {
  latitude: number;
  longitude: number;
  altitude: number;
  timestamp: number;
}

export interface Velocity {
  ground_speed: number;
  vertical_speed: number;
  heading: number;
}

export interface FlightPlan {
  origin: string;
  destination: string;
  cruise_altitude: number;
  cruise_speed: number;
}

export interface Aircraft {
  id: string;
  callsign: string;
  aircraft_type: string;
  position: Position;
  velocity: Velocity;
  flight_plan: FlightPlan;
  status: AircraftStatus;
  is_maneuvering?: boolean;
}

export type SimulationStatus = 'INITIALIZED' | 'PLAYING' | 'PAUSED' | 'COMPLETED';

export interface Conflict {
  id: string;
  aircraft_1_id: string;
  aircraft_2_id: string;
  time_to_conflict_sec: number;
  location: Position;
  severity: string;
  severity_score?: number;
  severity_factors?: string[];
  severity_explanation?: string;
  cpa_time?: number;
  cpa_horizontal_separation_nm?: number;
  cpa_vertical_separation_ft?: number;
  threshold_horizontal_nm?: number;
  threshold_vertical_ft?: number;
  state?: string;
}

export interface SimulationSnapshot {
  time: number;
  status: SimulationStatus;
  speed_multiplier: number;
  aircraft_count: number;
  aircraft: Aircraft[];
  trails?: Record<string, [number, number][]>;
  predicted_trajectories?: Record<string, [number, number][]>;
  conflicts?: Conflict[];
}

export interface Maneuver {
  type: 'HEADING' | 'ALTITUDE' | 'SPEED';
  heading_change: number;
  altitude_change: number;
  speed_change: number;
}

export interface ResolutionCandidate {
  id: string;
  aircraft_id: string;
  maneuver: Maneuver;
  reason: string;
  is_valid: boolean;
  total_score?: number;
  rejection_reason?: string | null;
  simulation_result?: {
    original_conflict_resolved: boolean;
    remaining_conflicts: Conflict[];
    new_conflicts: Conflict[];
    min_horizontal_separation_nm: number;
    min_vertical_separation_ft: number;
  } | null;
}

export interface Recommendation {
  id: string;
  conflict_id: string;
  status: 'RECOMMENDATION_AVAILABLE' | 'NO_FEASIBLE_RECOMMENDATION' | string;
  primary_candidate?: ResolutionCandidate | null;
  alternative_candidates: ResolutionCandidate[];
  explanation: string;
  warnings: string[];
}

export interface ControllerDecision {
  id: string;
  recommendation_id: string;
  conflict_id: string;
  candidate_id?: string | null;
  action: 'ACCEPT' | 'REJECT';
  timestamp: number;
  reason?: string | null;
}

export interface ProviderStatus {
  provider: string;
  active: boolean;
  connected: boolean;
  fresh: boolean;
  aircraft_count: number;
  last_success_at: number | null;
  last_error: string | null;
  rate_limit_remaining: string | null;
  poll_interval_sec: number | null;
}

export interface ScenarioSummary {
  id: string;
  name: string;
  description: string;
  aircraft_count: number;
}

export interface RegionData {
  name: string;
  polygon: [number, number][];
  altitude_floor_ft: number;
  altitude_ceiling_ft: number;
  approach_buffer_nm: number;
}
