import React, { useEffect, useState } from 'react';
import { AlertTriangle, X, CheckCircle2, XCircle, Info } from 'lucide-react';
import { Conflict } from '../types';
import { fetchConflictRecommendation, recordDecision, fetchDecisions } from '../api/rest';

interface ConflictPanelProps {
  conflict: Conflict | null;
  onClose: () => void;
}

export const ConflictPanel: React.FC<ConflictPanelProps> = ({ conflict, onClose }) => {
  const [recommendation, setRecommendation] = useState<any>(null);
  const [decision, setDecision] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    if (conflict) {
      setLoading(true);
      fetchConflictRecommendation(conflict.id)
        .then((rec) => {
          setRecommendation(rec);
          fetchDecisions().then((decs) => {
            const match = decs.find((d) => d.recommendation_id === rec.id);
            setDecision(match || null);
          }).catch(console.error);
        })
        .catch(console.error)
        .finally(() => setLoading(false));
    } else {
      setRecommendation(null);
      setDecision(null);
    }
  }, [conflict]);

  const handleAction = async (action: 'ACCEPT' | 'REJECT') => {
    if (!recommendation?.primary_candidate || !conflict) return;
    setActionLoading(true);
    try {
      const dec = await recordDecision({
        recommendation_id: recommendation.id,
        conflict_id: conflict.id,
        candidate_id: recommendation.primary_candidate.id,
        action,
        reason: ""
      });
      setDecision(dec);
    } catch (err) {
      console.error(err);
      alert("Failed to record decision.");
    } finally {
      setActionLoading(false);
    }
  };

  if (!conflict) return null;

  return (
    <div className="absolute right-4 top-20 w-80 bg-[#0b1120]/95 border border-red-900/50 rounded shadow-[0_0_15px_rgba(220,38,38,0.3)] z-20 backdrop-blur-md font-mono text-slate-300">
      <div className="flex items-center justify-between border-b border-red-900/50 p-3 bg-red-900/20 rounded-t">
        <h2 className="font-bold text-xs tracking-widest text-red-400 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" /> EMERGENCY ALERTS
        </h2>
        <button onClick={onClose} className="text-red-500 hover:text-red-300 transition">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="p-4 space-y-4 text-xs">
        {/* Main Alert Identity */}
        <div className="bg-[#450a0a] text-white p-3 rounded border border-red-700/50 flex justify-between items-start">
          <div>
            <div className="text-lg font-bold text-red-200">{conflict.aircraft_1_id} / {conflict.aircraft_2_id}</div>
            <div className="text-[10px] text-red-400 font-bold uppercase mt-1 px-1.5 py-0.5 bg-red-950 inline-block border border-red-800">
              {conflict.severity} CONFLICT
            </div>
          </div>
          <div className="text-right">
            <div className="text-[10px] text-red-400">TTC</div>
            <div className="font-bold text-xl">{Math.round(conflict.time_to_conflict_sec)}s</div>
          </div>
        </div>

        <div className="bg-[#0f172a] border border-slate-800 p-3 rounded">
          <div className="text-[10px] text-slate-500 mb-1">SYSTEM EXPLANATION</div>
          <div className="text-slate-300 text-xs leading-relaxed">{conflict.severity_explanation}</div>
        </div>

        {loading ? (
          <div className="text-center text-sky-400 py-4 animate-pulse">GENERATING RESOLUTION...</div>
        ) : recommendation ? (
          <div className="bg-[#0f172a] border border-slate-800 p-3 rounded">
             <div className="text-[10px] text-slate-500 mb-1">AI RECOMMENDATION</div>
             {recommendation.primary_candidate ? (
                <>
                  <div className="text-emerald-400 font-bold mb-2">
                    Action: {recommendation.primary_candidate.maneuver.type}
                  </div>
                  <div className="text-slate-300 text-xs mb-3 italic">
                    "{recommendation.explanation}"
                  </div>

                  {decision ? (
                    <div className={`mt-3 p-2 rounded flex items-center justify-center space-x-2 border font-bold text-xs ${
                      decision.action === 'ACCEPT' ? 'bg-emerald-900/40 border-emerald-500/50 text-emerald-400' : 'bg-red-900/40 border-red-500/50 text-red-400'
                    }`}>
                      {decision.action === 'ACCEPT' ? 'MANEUVER ACCEPTED' : 'MANEUVER REJECTED'}
                    </div>
                  ) : (
                    <div className="flex space-x-2 mt-3">
                      <button onClick={() => handleAction('ACCEPT')} className="flex-1 bg-red-700 hover:bg-red-600 text-white font-bold py-2 px-3 rounded text-[11px] transition">
                        ACK / DISPATCH
                      </button>
                      <button onClick={() => handleAction('REJECT')} className="flex-1 bg-slate-800 hover:bg-slate-700 text-white font-bold py-2 px-3 rounded border border-slate-600 text-[11px] transition">
                        REJECT
                      </button>
                    </div>
                  )}
                </>
             ) : (
                <div className="text-red-400">NO FEASIBLE RECOMMENDATION</div>
             )}
          </div>
        ) : null}
      </div>
    </div>
  );
};
