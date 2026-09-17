import React from 'react';
import { ShieldCheck, AlertTriangle, AlertOctagon, Activity } from 'lucide-react';

export default function ThreatGauge({ threatScore = 0.14 }) {
  // Normalize score between 0.00 and 1.00
  const score = Math.max(0, Math.min(1, Number(threatScore) || 0));
  
  // Angle maps 0 -> -90 deg, 1 -> 90 deg (or 0 -> 180 deg)
  // Let's use 180 degree arc: score 0 is -90deg (left), score 1 is 90deg (right)
  const needleAngle = -90 + score * 180;

  // Determine threat band
  let statusText = 'BENIGN FLEET POSTURE';
  let badgeBg = 'bg-emerald-950/80 border-emerald-500/40 text-emerald-300';
  let StatusIcon = ShieldCheck;

  if (score >= 0.70) {
    statusText = 'CRITICAL ATTACK DETECTED';
    badgeBg = 'bg-rose-950/90 border-rose-500/60 text-rose-200 animate-pulse';
    StatusIcon = AlertOctagon;
  } else if (score >= 0.40) {
    statusText = 'ELEVATED BEHAVIORAL DRIFT';
    badgeBg = 'bg-amber-950/80 border-amber-500/50 text-amber-200';
    StatusIcon = AlertTriangle;
  }

  return (
    <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 flex flex-col items-center justify-between shadow-xl relative overflow-hidden">
      {/* Subtle background glow */}
      <div
        className={`absolute -top-16 -right-16 w-36 h-36 rounded-full blur-3xl opacity-20 pointer-events-none ${
          score >= 0.70 ? 'bg-rose-500' : score >= 0.40 ? 'bg-amber-500' : 'bg-emerald-500'
        }`}
      />

      {/* Header */}
      <div className="w-full flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-slate-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Fleet Threat Speedometer
          </h3>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
          H(X) + Isolation Forest
        </span>
      </div>

      {/* Radial Speedometer Gauge */}
      <div className="relative w-56 h-32 flex items-end justify-center my-1">
        <svg viewBox="0 0 200 110" className="w-full h-full overflow-visible">
          <defs>
            <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#10b981" />
              <stop offset="45%" stopColor="#34d399" />
              <stop offset="55%" stopColor="#f59e0b" />
              <stop offset="75%" stopColor="#f97316" />
              <stop offset="100%" stopColor="#ef4444" />
            </linearGradient>
            <filter id="needleGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="0" stdDeviation="2" floodColor="#ffffff" floodOpacity="0.4" />
            </filter>
          </defs>

          {/* Background Track Arc */}
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="#1e293b"
            strokeWidth="16"
            strokeLinecap="round"
          />

          {/* Colored Gradient Track Arc */}
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="url(#gaugeGradient)"
            strokeWidth="12"
            strokeLinecap="round"
            opacity="0.9"
          />

          {/* Gauge Reference Tick Labels */}
          <text x="14" y="112" fill="#64748b" fontSize="9" fontWeight="bold" textAnchor="middle">0.0</text>
          <text x="100" y="26" fill="#64748b" fontSize="9" fontWeight="bold" textAnchor="middle">0.5</text>
          <text x="186" y="112" fill="#64748b" fontSize="9" fontWeight="bold" textAnchor="middle">1.0</text>

          {/* Needle Center Pivot */}
          <circle cx="100" cy="100" r="8" fill="#334155" stroke="#0f172a" strokeWidth="2" />
          <circle cx="100" cy="100" r="4" fill="#94a3b8" />

          {/* Dynamic Needle */}
          <g
            transform={`rotate(${needleAngle}, 100, 100)`}
            className="transition-transform duration-700 ease-out"
          >
            <line
              x1="100"
              y1="100"
              x2="100"
              y2="28"
              stroke="#ffffff"
              strokeWidth="3.5"
              strokeLinecap="round"
              filter="url(#needleGlow)"
            />
            <circle cx="100" cy="28" r="3" fill="#f43f5e" />
          </g>
        </svg>

        {/* Needle Value Readout */}
        <div className="absolute bottom-0 text-center flex flex-col items-center">
          <span className="text-2xl font-black tracking-tight text-white font-mono">
            {score.toFixed(2)}
          </span>
          <span className="text-[10px] uppercase tracking-widest text-slate-400 font-semibold">
            Threat Index
          </span>
        </div>
      </div>

      {/* Threat Posture Status Badge */}
      <div className={`mt-3 w-full py-1.5 px-3 rounded-xl border flex items-center justify-center gap-2 text-xs font-bold transition-all ${badgeBg}`}>
        <StatusIcon className="w-4 h-4 shrink-0" />
        <span className="truncate">{statusText}</span>
      </div>

      {/* Threshold Guide */}
      <div className="w-full flex justify-between text-[10px] text-slate-500 font-mono mt-2 pt-2 border-t border-slate-800/80">
        <span className="text-emerald-400/80">Safe &lt;0.40</span>
        <span className="text-amber-400/80">Drift 0.40-0.70</span>
        <span className="text-rose-400/80">Block &gt;0.70</span>
      </div>
    </div>
  );
}
