import React, { useState } from 'react';
import { BarChart2, Loader2, X, CheckCircle, AlertTriangle } from 'lucide-react';
import { runEvaluation } from '../api/rest';

interface EvaluationPanelProps {
  scenarioId: string;
}

export const EvaluationPanel: React.FC<EvaluationPanelProps> = ({ scenarioId }) => {
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const handleRun = async () => {
    setLoading(true);
    setExpanded(true);
    try {
      const res = await runEvaluation(scenarioId);
      setMetrics(res);
    } catch (err) {
      console.error(err);
      alert('Failed to run evaluation metrics.');
      setExpanded(false);
    } finally {
      setLoading(false);
    }
  };

  if (!expanded) {
    return (
      <button 
        onClick={handleRun}
        className="absolute top-4 left-4 bg-slate-900 hover:bg-slate-800 text-slate-200 p-2 rounded shadow-lg border border-slate-700 z-20 flex items-center space-x-2 transition"
      >
        <BarChart2 className="w-4 h-4 text-purple-400" />
        <span className="text-xs font-bold tracking-wide pr-1">EVALUATE</span>
      </button>
    );
  }

  return (
    <div className="absolute top-4 left-4 w-80 bg-slate-950/95 border border-slate-800/90 rounded-lg shadow-2xl z-20 flex flex-col backdrop-blur-md">
      <div className="flex items-center justify-between border-b border-slate-800 p-3">
        <div className="flex items-center space-x-2 text-purple-400">
          <BarChart2 className="w-4 h-4" />
          <h3 className="font-bold text-xs tracking-wider">SCENARIO METRICS</h3>
        </div>
        <button onClick={() => setExpanded(false)} className="text-slate-500 hover:text-slate-300">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="p-4 space-y-4 text-slate-200">
        {loading ? (
          <div className="flex flex-col items-center justify-center space-y-3 py-6 text-slate-400">
            <Loader2 className="w-6 h-6 animate-spin text-purple-400" />
            <span className="text-xs">Running isolated pipeline...</span>
          </div>
        ) : metrics ? (
          <>
            <div className="text-xs border-b border-slate-800 pb-3">
              <div className="text-slate-400 text-[10px] uppercase">Scenario</div>
              <div className="font-bold text-sky-400 truncate">{metrics.scenario}</div>
              <div className="text-slate-500 mt-1">Total Aircraft: {metrics.total_aircraft}</div>
            </div>

            <div>
              <div className="text-slate-400 text-[10px] uppercase mb-1">Conflicts</div>
              <div className="flex items-center justify-between bg-slate-900/50 p-2 rounded border border-slate-800">
                <span className="text-xs">Detected</span>
                <span className="font-bold">{metrics.conflicts.detected_count}</span>
              </div>
            </div>

            {metrics.conflicts.detected_count > 0 && metrics.resolutions && (
              <div>
                <div className="text-slate-400 text-[10px] uppercase mb-1">Resolution Feasibility</div>
                <div className="space-y-1">
                  <div className="flex items-center justify-between bg-emerald-900/20 p-2 rounded border border-emerald-900/50">
                    <span className="text-xs flex items-center gap-1.5"><CheckCircle className="w-3.5 h-3.5 text-emerald-500" /> Feasible</span>
                    <span className="font-bold text-emerald-400">{metrics.resolutions.feasible_count}</span>
                  </div>
                  <div className="flex items-center justify-between bg-red-900/20 p-2 rounded border border-red-900/50">
                    <span className="text-xs flex items-center gap-1.5"><AlertTriangle className="w-3.5 h-3.5 text-red-500" /> Infeasible</span>
                    <span className="font-bold text-red-400">{metrics.resolutions.infeasible_count}</span>
                  </div>
                  <div className="text-[10px] text-slate-500 text-right mt-1">
                    {metrics.resolutions.candidates_evaluated} total candidates evaluated
                  </div>
                </div>
              </div>
            )}

            <div>
              <div className="text-slate-400 text-[10px] uppercase mb-1">Processing Time (ms)</div>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between bg-slate-900/50 p-1.5 rounded">
                  <span className="text-slate-400">Detection</span>
                  <span className="font-mono">{metrics.processing_times_ms.detection_and_propagation} ms</span>
                </div>
                {metrics.processing_times_ms.scoring_and_recommendation !== undefined && (
                  <div className="flex justify-between bg-slate-900/50 p-1.5 rounded">
                    <span className="text-slate-400">Resolution</span>
                    <span className="font-mono">{metrics.processing_times_ms.scoring_and_recommendation} ms</span>
                  </div>
                )}
              </div>
            </div>
            
            <button onClick={handleRun} className="w-full mt-2 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-bold rounded transition">
              RERUN EVALUATION
            </button>
          </>
        ) : (
          <div className="text-center text-xs text-red-400 py-4">Failed to load metrics.</div>
        )}
      </div>
    </div>
  );
};
