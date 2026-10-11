import React, { useState, useEffect } from 'react';
import { History, Play, AlertTriangle, ShieldCheck, CheckCircle, XCircle } from 'lucide-react';
import { fetchDecisions } from '../api/rest';
import { SimulationSnapshot } from '../types';

interface TimelineEvent {
  id: string;
  time: number;
  type: 'START' | 'CONFLICT' | 'RECOMMENDATION' | 'DECISION';
  description: string;
  color: string;
  icon: React.ReactNode;
}

interface TimelinePanelProps {
  snapshot: SimulationSnapshot | null;
}

export const TimelinePanel: React.FC<TimelinePanelProps> = ({ snapshot }) => {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (!snapshot) return;

    const newEvents: TimelineEvent[] = [];

    // Base start event
    newEvents.push({
      id: 'evt-start',
      time: 0,
      type: 'START',
      description: 'Scenario started',
      color: 'text-sky-400',
      icon: <Play className="w-4 h-4" />
    });

    // Extract conflicts
    snapshot.conflicts?.forEach((c) => {
      newEvents.push({
        id: `evt-conf-${c.id}`,
        time: snapshot.time, // using current sim time as proxy
        type: 'CONFLICT',
        description: `Conflict ${c.id.substring(0, 8)} detected (${c.severity})`,
        color: c.severity === 'CRITICAL' ? 'text-red-400' : 'text-orange-400',
        icon: <AlertTriangle className="w-4 h-4" />
      });
    });

    // Fetch decisions asynchronously
    fetchDecisions().then(decs => {
      decs.forEach(d => {
        newEvents.push({
          id: `evt-dec-${d.id}`,
          time: d.timestamp,
          type: 'DECISION',
          description: `Decision: ${d.action} recommendation for ${d.conflict_id.substring(0, 8)}`,
          color: d.action === 'ACCEPT' ? 'text-emerald-400' : 'text-red-400',
          icon: d.action === 'ACCEPT' ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />
        });
      });

      // Sort by time
      newEvents.sort((a, b) => a.time - b.time);
      setEvents(newEvents);
    }).catch(console.error);

  }, [snapshot?.time, snapshot?.conflicts]);

  if (!expanded) {
    return (
      <button 
        onClick={() => setExpanded(true)}
        className="absolute top-16 left-4 bg-slate-900 hover:bg-slate-800 text-slate-200 p-2 rounded shadow-lg border border-slate-700 z-20 flex items-center space-x-2 transition"
      >
        <History className="w-4 h-4 text-emerald-400" />
        <span className="text-xs font-bold tracking-wide pr-1">TIMELINE</span>
      </button>
    );
  }

  return (
    <div className="absolute top-16 left-4 w-80 max-h-[60vh] bg-slate-950/95 border border-slate-800/90 rounded-lg shadow-2xl z-20 flex flex-col backdrop-blur-md">
      <div className="flex items-center justify-between border-b border-slate-800 p-3">
        <div className="flex items-center space-x-2 text-emerald-400">
          <History className="w-4 h-4" />
          <h3 className="font-bold text-xs tracking-wider">EVENT TIMELINE (DEMO MODE)</h3>
        </div>
        <button onClick={() => setExpanded(false)} className="text-slate-500 hover:text-slate-300">
          <XCircle className="w-4 h-4" />
        </button>
      </div>

      <div className="p-4 overflow-y-auto space-y-4 custom-scrollbar text-slate-200 text-xs">
        {events.length === 0 ? (
          <div className="text-slate-500 text-center">No events recorded.</div>
        ) : (
          events.map((evt, i) => (
            <div key={evt.id} className="flex space-x-3 items-start relative">
              {i !== events.length - 1 && (
                <div className="absolute left-[7px] top-6 bottom-[-16px] w-[2px] bg-slate-800" />
              )}
              <div className={`mt-0.5 ${evt.color}`}>
                {evt.icon}
              </div>
              <div className="flex-1">
                <div className="flex justify-between">
                  <span className="font-bold">{evt.type}</span>
                  <span className="text-[10px] text-slate-500 font-mono">T+{Math.floor(evt.time)}s</span>
                </div>
                <div className="text-slate-400 mt-0.5 leading-tight">{evt.description}</div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
