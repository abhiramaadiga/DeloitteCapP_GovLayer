import React, { useState } from 'react';
import { Cpu, CheckCircle, Layers, Sparkles } from 'lucide-react';

export default function MlDriftMonitor({ driftStatus, telemetry, onRetrain, retrainLoading }) {
  const [retrainSuccess, setRetrainSuccess] = useState(null);

  const rolling = telemetry?.rolling_window || {
    size: 100,
    current_samples: 84,
    mean_risk_score: 0.142,
    mean_pep_latency_ms: 1.18,
    anomaly_rate: 0.042,
  };

  const buffer = telemetry?.retraining_buffer || {
    buffered_samples: 38,
    capacity: 500,
  };

  const isDrift = driftStatus?.status === 'DRIFT_DETECTED';
  const bufferPercent = Math.min(100, Math.round((buffer.buffered_samples / (buffer.capacity || 500)) * 100));

  const handleRetrainClick = async () => {
    try {
      const res = await onRetrain();
      setRetrainSuccess(res?.message || 'Isolation Forest calibrated with buffered RLHF feedback!');
      setTimeout(() => setRetrainSuccess(null), 5000);
    } catch {
      // handled
    }
  };

  return (
    <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-xl flex flex-col justify-between">
      {/* Header */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-purple-400" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Behavioral ML Drift & Retraining Monitor
            </h3>
          </div>
          <span
            className={`px-2.5 py-1 rounded-full text-[11px] font-bold border flex items-center gap-1.5 ${
              isDrift
                ? 'bg-amber-950/80 border-amber-500/50 text-amber-300 animate-pulse'
                : 'bg-emerald-950/80 border-emerald-500/50 text-emerald-300'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${isDrift ? 'bg-amber-400' : 'bg-emerald-400'}`}
            />
            {isDrift ? 'DRIFT DETECTED' : 'MODEL STABLE'}
          </span>
        </div>

        <p className="text-xs text-slate-400 mb-4">
          Continuous unsupervised telemetry scoring via Pre-Warmed Isolation Forest (4 Features: Entropy, Velocity, Markov Jumps, Payload Byte Size).
        </p>

        {/* Rolling Window Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4 text-xs font-mono">
          <div className="p-3 bg-slate-950/70 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-500 block uppercase">Rolling Window</span>
            <span className="text-base font-bold text-white">{rolling.current_samples}</span>
            <span className="text-[10px] text-slate-500 block">/ {rolling.size} evts</span>
          </div>

          <div className="p-3 bg-slate-950/70 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-500 block uppercase">Rolling Mean Risk</span>
            <span
              className={`text-base font-bold ${
                rolling.mean_risk_score >= 0.25 ? 'text-amber-400' : 'text-emerald-400'
              }`}
            >
              {Number(rolling.mean_risk_score || 0).toFixed(3)}
            </span>
            <span className="text-[10px] text-slate-500 block">Base: 0.150</span>
          </div>

          <div className="p-3 bg-slate-950/70 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-500 block uppercase">Anomaly Rate</span>
            <span
              className={`text-base font-bold ${
                rolling.anomaly_rate > 0.1 ? 'text-rose-400' : 'text-emerald-400'
              }`}
            >
              {(Number(rolling.anomaly_rate || 0) * 100).toFixed(1)}%
            </span>
            <span className="text-[10px] text-slate-500 block">Max: 20.0%</span>
          </div>

          <div className="p-3 bg-slate-950/70 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-500 block uppercase">PEP Latency</span>
            <span className="text-base font-bold text-cyan-400">
              {Number(rolling.mean_pep_latency_ms || 1.15).toFixed(2)}ms
            </span>
            <span className="text-[10px] text-slate-500 block">SLA &lt; 5.0ms</span>
          </div>
        </div>

        {/* Retraining Buffer Progress */}
        <div className="p-3.5 bg-slate-950/60 rounded-xl border border-slate-800/80 mb-4">
          <div className="flex items-center justify-between text-xs mb-1.5">
            <span className="text-slate-400 flex items-center gap-1.5 font-medium">
              <Layers className="w-3.5 h-3.5 text-indigo-400" />
              RLHF Feedback Buffer:
            </span>
            <span className="font-mono font-bold text-slate-200">
              {buffer.buffered_samples} / {buffer.capacity} samples
            </span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
            <div
              className="bg-gradient-to-r from-purple-500 to-indigo-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.max(5, bufferPercent)}%` }}
            />
          </div>
          <p className="text-[10px] text-slate-500 mt-1.5">
            Buffered borderline queries & policy violations ready for continuous online calibration.
          </p>
        </div>

        {/* Retrain Success Banner */}
        {retrainSuccess && (
          <div className="mb-3 p-3 bg-emerald-950/80 border border-emerald-500/50 rounded-xl text-emerald-300 text-xs flex items-center gap-2 animate-fadeIn">
            <CheckCircle className="w-4 h-4 shrink-0 text-emerald-400" />
            <span>{retrainSuccess}</span>
          </div>
        )}
      </div>

      {/* Action Retrain Button */}
      <div className="pt-2 flex items-center justify-between border-t border-slate-800/80">
        <div className="text-[11px] text-slate-400">
          <span className="text-slate-500">Active Pipeline:</span>{' '}
          <span className="font-mono text-slate-300">IsolationForest.joblib</span>
        </div>
        <button
          onClick={handleRetrainClick}
          disabled={retrainLoading}
          className="px-4 py-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold text-xs flex items-center gap-2 shadow-lg shadow-purple-900/30 transition transform hover:scale-102 disabled:opacity-50"
        >
          <Sparkles className={`w-3.5 h-3.5 ${retrainLoading ? 'animate-spin' : ''}`} />
          <span>{retrainLoading ? 'Calibrating Model...' : 'Retrain Isolation Forest'}</span>
        </button>
      </div>
    </div>
  );
}
