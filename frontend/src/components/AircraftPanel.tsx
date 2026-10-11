import React from 'react';
import { Plane, Navigation, Activity, X } from 'lucide-react';
import { Aircraft } from '../types';

interface AircraftPanelProps {
  aircraft: Aircraft | null;
  onClose: () => void;
}

export const AircraftPanel: React.FC<AircraftPanelProps> = ({ aircraft, onClose }) => {
  if (!aircraft) return null;

  return (
    <div className="absolute left-4 top-20 w-72 bg-[#0b1120]/95 border border-indigo-900/50 rounded shadow-[0_0_15px_rgba(30,58,138,0.3)] z-20 backdrop-blur-md font-mono text-slate-300">
      <div className="flex items-center justify-between border-b border-indigo-900/50 p-3 bg-[#1e3a8a]/20 rounded-t">
        <h2 className="font-bold text-xs tracking-widest text-sky-400">FLIGHT DATA</h2>
        <button onClick={onClose} className="text-sky-500 hover:text-sky-300 transition">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="p-4 space-y-4">
        {/* Main Identity */}
        <div className="bg-[#1e40af] text-white p-3 rounded shadow-inner border border-blue-600/50">
          <div className="text-xl font-bold tracking-wider">{aircraft.callsign}</div>
          <div className="text-[10px] text-blue-200 uppercase mt-1">COMMERCIAL AIRCRAFT</div>
          <div className="flex items-center space-x-1.5 mt-2 text-[10px] font-bold text-emerald-400">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>ACTIVE TRACKING</span>
          </div>
        </div>

        {/* Telemetry Grid */}
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-[#0f172a] border border-slate-800 p-2 rounded">
            <div className="text-[10px] text-slate-500 mb-1">ALT</div>
            <div className="text-sm font-bold text-sky-300">{Math.round(aircraft.position.altitude).toLocaleString()}ft</div>
          </div>
          <div className="bg-[#0f172a] border border-slate-800 p-2 rounded">
            <div className="text-[10px] text-slate-500 mb-1">SPD</div>
            <div className="text-sm font-bold text-sky-300">{Math.round(aircraft.velocity.ground_speed)}kts</div>
          </div>
          <div className="bg-[#0f172a] border border-slate-800 p-2 rounded col-span-2">
            <div className="text-[10px] text-slate-500 mb-1">HDG</div>
            <div className="text-sm font-bold text-sky-300">{Math.round(aircraft.velocity.heading)}°</div>
          </div>
          <div className="bg-[#0f172a] border border-slate-800 p-2 rounded">
            <div className="text-[10px] text-slate-500 mb-1">LAT</div>
            <div className="text-xs text-slate-300">{aircraft.position.latitude.toFixed(4)}</div>
          </div>
          <div className="bg-[#0f172a] border border-slate-800 p-2 rounded">
            <div className="text-[10px] text-slate-500 mb-1">LNG</div>
            <div className="text-xs text-slate-300">{aircraft.position.longitude.toFixed(4)}</div>
          </div>
        </div>
      </div>
    </div>
  );
};
