import React from 'react';
import { Radio, Clock, Plane, Activity } from 'lucide-react';
import { SimulationSnapshot } from '../types';

interface StatusBarProps {
  wsStatus: 'connected' | 'connecting' | 'disconnected';
  snapshot: SimulationSnapshot | null;
}

export const StatusBar: React.FC<StatusBarProps> = ({ wsStatus, snapshot }) => {
  const getStatusColor = () => {
    switch (wsStatus) {
      case 'connected': return 'text-emerald-400 bg-emerald-950/60 border-emerald-800';
      case 'connecting': return 'text-amber-400 bg-amber-950/60 border-amber-800 animate-pulse';
      case 'disconnected': return 'text-rose-400 bg-rose-950/60 border-rose-800';
    }
  };

  const formatSimTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `T+${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  return (
    <footer className="absolute bottom-0 left-0 w-full h-8 bg-[#050914]/80 border-t border-sky-900/40 px-4 flex items-center justify-between text-[10px] uppercase font-bold text-slate-500 select-none z-20 backdrop-blur-md">
      {/* Left: Connection and System Identity */}
      <div className="flex items-center space-x-4">
        <div className={`flex items-center space-x-1.5 px-2 py-0.5 rounded border ${getStatusColor()}`}>
          <Radio className="w-3 h-3" />
          <span className="tracking-wider">{wsStatus}</span>
        </div>
        <div className="flex items-center space-x-1">
          <span>FEED:</span>
          <span className="text-sky-400">4 Hz TELEMETRY</span>
        </div>
      </div>

      {/* Center: Authoritative Simulation Clock */}
      <div className="flex items-center space-x-3 text-slate-400">
        <Clock className="w-3.5 h-3.5 text-sky-500" />
        <span>SIM CLOCK:</span>
        <span className="text-sky-300 font-mono tracking-widest text-[11px]">
          {snapshot ? formatSimTime(snapshot.time) : 'T+00:00'}
        </span>
        <span className="text-slate-700">|</span>
        <span>
          RATE: <strong className="text-emerald-500">{snapshot ? `${snapshot.speed_multiplier}x` : '1.0x'}</strong>
        </span>
      </div>

      {/* Right: Operational Stats */}
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-1.5">
          <Plane className="w-3.5 h-3.5 text-sky-500" />
          <span>TRACKED:</span>
          <span className="text-sky-300">{snapshot?.aircraft_count ?? 0}</span>
        </div>
      </div>
    </footer>
  );
};
