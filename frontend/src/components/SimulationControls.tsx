import React from 'react';
import { Play, Pause, RotateCcw, StepForward, Gauge } from 'lucide-react';
import { ScenarioSummary, SimulationSnapshot } from '../types';

interface SimulationControlsProps {
  scenarios: ScenarioSummary[];
  selectedScenario: string;
  onSelectScenario: (scenarioId: string) => void;
  snapshot: SimulationSnapshot | null;
  onControl: (action: 'play' | 'pause' | 'step' | 'reset' | 'live' | 'sim', speed?: number) => void;
}

export const SimulationControls: React.FC<SimulationControlsProps> = ({
  scenarios,
  selectedScenario,
  onSelectScenario,
  snapshot,
  onControl,
}) => {
  const isPlaying = snapshot?.status === 'PLAYING';
  const speed = snapshot?.speed_multiplier ?? 1.0;

  return (
    <header className="absolute top-0 left-0 w-full h-12 bg-[#050914]/80 border-b border-sky-900/40 px-4 flex items-center justify-between z-20 backdrop-blur-md select-none">
      {/* Brand & Project Identity */}
      <div className="flex items-center space-x-3">
        <div className="w-8 h-8 rounded bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center">
          <div className="w-2 h-2 bg-emerald-400 rounded-full animate-ping" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="font-bold text-sky-400 tracking-wider text-sm mono">SFO TWR</h1>
            <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-emerald-950/50 border border-emerald-800/60 text-emerald-400">
              RADAR ACTIVE
            </span>
          </div>
        </div>
      </div>

      {/* Scenario Selector & Description */}
      <div className="flex items-center space-x-3">
        <label className="text-xs mono text-slate-400 uppercase font-semibold">MODE:</label>
        <button
          onClick={() => onControl('live')}
          className="bg-emerald-950 border border-emerald-500/50 text-emerald-400 text-xs px-2 py-1 rounded hover:bg-emerald-900 transition font-bold"
        >
          LIVE DATA
        </button>
        <label className="text-xs mono text-slate-400 uppercase font-semibold ml-2">SIM:</label>
        <select
          value={selectedScenario}
          onChange={(e) => {
            onControl('sim'); // Force sim mode
            onSelectScenario(e.target.value);
          }}
          className="bg-slate-900 border border-slate-700/80 rounded px-2.5 py-1 text-xs mono text-slate-200 focus:outline-none focus:border-sky-500 transition cursor-pointer"
        >
          {scenarios.map((sc) => (
            <option key={sc.id} value={sc.id}>
              {sc.name} ({sc.aircraft_count} AC)
            </option>
          ))}
        </select>
      </div>

      {/* Playback Controls & Speed */}
      <div className="flex items-center space-x-2 mono">
        {/* Play / Pause Toggle */}
        <button
          onClick={() => onControl(isPlaying ? 'pause' : 'play')}
          className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-semibold transition border ${
            isPlaying
              ? 'bg-amber-950/70 border-amber-600 text-amber-300 hover:bg-amber-900'
              : 'bg-emerald-950/70 border-emerald-600 text-emerald-300 hover:bg-emerald-900'
          }`}
          title={isPlaying ? 'Pause Simulation' : 'Start Simulation'}
        >
          {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 fill-current" />}
          <span>{isPlaying ? 'PAUSE' : 'START'}</span>
        </button>

        {/* Step Forward */}
        <button
          onClick={() => onControl('step')}
          disabled={isPlaying}
          className="flex items-center space-x-1 px-2.5 py-1.5 rounded text-xs border border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition"
          title="Single Step (+1s)"
        >
          <StepForward className="w-3.5 h-3.5" />
          <span>STEP</span>
        </button>

        {/* Reset */}
        <button
          onClick={() => onControl('reset')}
          className="flex items-center space-x-1 px-2.5 py-1.5 rounded text-xs border border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800 transition"
          title="Reset to Initial State"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>RESET</span>
        </button>

        <div className="h-5 w-px bg-slate-800 mx-1" />

        {/* Speed Selector */}
        <div className="flex items-center space-x-1 bg-slate-900 p-0.5 rounded border border-slate-800">
          <Gauge className="w-3 h-3 text-slate-400 ml-1.5 mr-0.5" />
          {[1.0, 2.0, 5.0].map((s) => (
            <button
              key={s}
              onClick={() => onControl(isPlaying ? 'play' : 'pause', s)}
              className={`px-2 py-0.5 text-[11px] rounded transition ${
                speed === s
                  ? 'bg-sky-600 text-white font-bold shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>
    </header>
  );
};
