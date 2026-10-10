import { ControllerDecision, ProviderStatus, Recommendation, RegionData, ScenarioSummary, SimulationSnapshot } from '../types';

const API_BASE = '/api';

export async function fetchScenarios(): Promise<ScenarioSummary[]> {
  const res = await fetch(`${API_BASE}/scenarios`);
  if (!res.ok) throw new Error('Failed to fetch scenarios');
  return res.json();
}

export async function fetchMonitoringRegion(): Promise<RegionData> {
  const res = await fetch(`${API_BASE}/region`);
  if (!res.ok) throw new Error('Failed to fetch monitoring region');
  return res.json();
}

export async function loadScenario(scenarioId: string): Promise<SimulationSnapshot> {
  const res = await fetch(`${API_BASE}/simulation/load`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_id: scenarioId }),
  });
  if (!res.ok) throw new Error('Failed to load scenario');
  return res.json();
}

export async function controlSimulation(
  action: 'play' | 'pause' | 'step' | 'reset' | 'live' | 'sim',
  speed?: number
): Promise<SimulationSnapshot> {
  const res = await fetch(`${API_BASE}/simulation/control`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, speed }),
  });
  if (!res.ok) throw new Error(`Failed to execute simulation action: ${action}`);
  return res.json();
}

export async function fetchSimulationState(): Promise<SimulationSnapshot> {
  const res = await fetch(`${API_BASE}/simulation/state`);
  if (!res.ok) throw new Error('Failed to fetch simulation state');
  return res.json();
}

export async function fetchProviderStatus(): Promise<ProviderStatus> {
  const res = await fetch(`${API_BASE}/provider/status`);
  if (!res.ok) throw new Error('Failed to fetch live provider status');
  return res.json();
}

export async function fetchConflictRecommendation(conflictId: string): Promise<Recommendation> {
  const res = await fetch(`${API_BASE}/simulation/conflicts/${conflictId}/recommendation`);
  if (!res.ok) throw new Error('Failed to fetch conflict recommendation');
  return res.json();
}

export async function askAssistant(query: string, conflictId?: string): Promise<string> {
  const res = await fetch(`${API_BASE}/simulation/assistant`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, conflict_id: conflictId }),
  });
  if (!res.ok) throw new Error('Failed to query assistant');
  const data = await res.json();
  return data.answer;
}

export async function recordDecision(payload: { recommendation_id: string; conflict_id: string; candidate_id?: string; action: 'ACCEPT' | 'REJECT'; reason?: string }): Promise<ControllerDecision> {
  const res = await fetch(`${API_BASE}/simulation/decisions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to record decision');
  return res.json();
}

export async function fetchDecisions(): Promise<ControllerDecision[]> {
  const res = await fetch(`${API_BASE}/simulation/decisions`);
  if (!res.ok) throw new Error('Failed to fetch decisions');
  return res.json();
}

export async function runEvaluation(scenarioId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/evaluation/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_id: scenarioId }),
  });
  if (!res.ok) throw new Error('Failed to run evaluation');
  return res.json();
}
