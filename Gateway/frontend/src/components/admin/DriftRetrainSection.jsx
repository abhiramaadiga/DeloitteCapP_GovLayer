import React, { useState } from 'react';
import { Cpu, RefreshCw, CheckCircle2, Sparkles, Layers } from 'lucide-react';
import Tooltip from '../common/Tooltip';

export default function DriftRetrainSection({
  driftStatus = null,
  telemetry = null,
  onRetrain,
  retrainLoading = false,
}) {
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
    <div className="bg-zinc-900/90 rounded-2xl border border-zinc-800/90 p-5 shadow-xl flex flex-col justify-between card-hover">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-purple-400" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
              Behavioral ML Drift & Retraining Monitor
            </h3>
          </div>
          <span
            className={`px-2.5 py-1 rounded-full text-[11px] font-bold border flex items-center gap-1.5 font-mono ${
              isDrift
                ? 'bg-amber-950/80 border-amber-500/50 text-amber-300 animate-pulse'
                : 'bg-emerald-950/80 border-emerald-500/50 text-emerald-300'
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${isDrift ? 'bg-amber-400' : 'bg-emerald-400'}`} />
            {isDrift ? 'DRIFT DETECTED' : 'MODEL STABLE'}
          </span>
        </div>

        <p className="text-xs text-zinc-400 mb-4">
          Continuous unsupervised telemetry scoring via Pre-Warmed Isolation Forest (4 Features: Entropy, Velocity, Markov Jumps, Payload Byte Size).
        </p>

        {/* Rolling Window Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4 text-xs font-mono">
          <div className="p-3 bg-zinc-950/70 rounded-xl border border-zinc-800">
            <span className="text-[10px] text-zinc-500 block uppercase">Rolling Window</span>
            <span className="text-base font-bold text-white">{rolling.current_samples ?? 0}</span>
            <span className="text-[10px] text-zinc-500 block">/ {rolling.size ?? 100} evts</span>
          </div>

          <div className="p-3 bg-zinc-950/70 rounded-xl border border-zinc-800">
            <span className="text-[10px] text-zinc-500 block uppercase">Rolling Mean Risk</span>
            <span
              className={`text-base font-bold ${
                (rolling.mean_risk_score ?? 0.15) >= 0.25 ? 'text-amber-400' : 'text-emerald-400'
              }`}
            >
              {Number(rolling.mean_risk_score ?? 0.15).toFixed(3)}
            </span>
            <span className="text-[10px] text-zinc-500 block">Base: 0.150</span>
          </div>

          <div className="p-3 bg-zinc-950/70 rounded-xl border border-zinc-800">
            <span className="text-[10px] text-zinc-500 block uppercase">Anomaly Rate</span>
            <span
              className={`text-base font-bold ${
                (rolling.anomaly_rate ?? 0) > 0.1 ? 'text-rose-400' : 'text-emerald-400'
              }`}
            >
              {(Number(rolling.anomaly_rate ?? 0) * 100).toFixed(1)}%
            </span>
            <span className="text-[10px] text-zinc-500 block">Max: 20.0%</span>
          </div>

          <div className="p-3 bg-zinc-950/70 rounded-xl border border-zinc-800">
            <span className="text-[10px] text-zinc-500 block uppercase">PEP Latency</span>
            <span className="text-base font-bold text-cyan-400">
              {Number(rolling.mean_pep_latency_ms ?? 0.0).toFixed(2)}ms
            </span>
            <span className="text-[10px] text-zinc-500 block">SLA &lt; 5.0ms</span>
          </div>
        </div>

        {/* Retraining Feedback Buffer Progress */}
        <div className="p-3.5 bg-zinc-950/70 rounded-xl border border-zinc-800 space-y-2 mb-4">
          <div className="flex justify-between items-center text-xs font-mono">
            <span className="text-zinc-400 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-purple-400" />
              <span>Feedback Ingestion Buffer</span>
            </span>
            <span className="text-zinc-200 font-bold">
              {buffer.buffered_samples} / {buffer.capacity} samples ({bufferPercent}%)
            </span>
          </div>
          <div className="w-full bg-zinc-800 h-2 rounded-full overflow-hidden">
            <div
              className="bg-gradient-to-r from-indigo-500 to-purple-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${bufferPercent}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-zinc-500 font-mono">
            <span>Min trigger: 20 samples</span>
            <span>Buffered from real-time Kafka telemetry stream</span>
          </div>
        </div>
      </div>

      {/* Retrain Action Button & Feedback */}
      <div>
        {retrainSuccess && (
          <div className="mb-3 p-2.5 bg-emerald-950/80 border border-emerald-500/50 rounded-xl text-emerald-300 text-xs font-mono flex items-center gap-2 animate-fadeIn">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{retrainSuccess}</span>
          </div>
        )}

        <Tooltip content="Recalibrate Isolation Forest weights using buffered telemetry and hot-reload into FastAPI memory" position="top" className="w-full">
          <button
            type="button"
            onClick={handleRetrainClick}
            disabled={retrainLoading}
            className="w-full py-2.5 px-4 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-purple-900/30 transition hover-lift disabled:opacity-50"
          >
            {retrainLoading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Re-fitting Contamination & Splitting Trees...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Retrain Isolation Forest (Hot Reload)</span>
              </>
            )}
          </button>
        </Tooltip>
      </div>
    </div>
  );
}
