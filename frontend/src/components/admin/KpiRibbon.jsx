import React from 'react';
import { Bot, Zap, Activity, Server, ShieldCheck, Database } from 'lucide-react';
import Tooltip from '../common/Tooltip';

export default function KpiRibbon({
  totalAgents = 4,
  quarantinedCount = 0,
  telemetry = null,
  isBackendOnline = true,
}) {
  const activeCount = totalAgents - quarantinedCount;
  const rolling = telemetry?.rolling_window || {};
  const pepLatency = (rolling.mean_pep_latency_ms != null ? Number(rolling.mean_pep_latency_ms) : 1.18).toFixed(2);
  const anomalyRate = (rolling.anomaly_rate != null ? Number(rolling.anomaly_rate) * 100 : 0.0).toFixed(1);
  const isKafkaUp = telemetry?.kafka_connected;

  const kpis = [
    {
      title: 'Governed Fleet',
      value: `${activeCount} / ${totalAgents}`,
      badge: quarantinedCount > 0 ? `${quarantinedCount} Quarantined` : 'All Active',
      badgeColor: quarantinedCount > 0 ? 'text-rose-400' : 'text-emerald-400',
      icon: Bot,
      tooltip: 'Active Non-Human Identity agents versus quarantined agents under real-time PEP control',
    },
    {
      title: 'Fast-Path Latency',
      value: `${pepLatency} ms`,
      badge: 'SLA < 5.0 ms',
      badgeColor: 'text-emerald-400',
      icon: Zap,
      tooltip: 'Inline latency overhead introduced by Policy Enforcement Point evaluation and token verification',
    },
    {
      title: 'Anomaly Rate',
      value: `${anomalyRate}%`,
      badge: 'Target < 5.0%',
      badgeColor: Number(anomalyRate) > 5 ? 'text-rose-400' : 'text-emerald-400',
      icon: Activity,
      tooltip: 'Rolling window percentage of requests flagged by Isolation Forest as statistical outliers',
    },
    {
      title: 'Streaming Bus',
      value: isKafkaUp ? 'KRaft :9092' : isBackendOnline ? 'FastAPI Sync' : 'Simulated',
      badge: isKafkaUp ? 'KRaft Active' : 'Event Queue',
      badgeColor: isKafkaUp ? 'text-emerald-400' : 'text-amber-400',
      icon: Server,
      tooltip: 'Apache Kafka 3.7 KRaft cluster streaming high-velocity telemetry on agentic-iam.telemetry',
    },
    {
      title: 'Policy Engine',
      value: 'Least-Privilege',
      badge: 'SOX-404 Enforced',
      badgeColor: 'text-emerald-400',
      icon: ShieldCheck,
      tooltip: 'Zero-Trust RBAC and contextual guardrail engine rejecting unauthorized tool invocations',
    },
    {
      title: 'System of Record',
      value: 'PostgreSQL 16',
      badge: 'Immutable Ledger',
      badgeColor: 'text-emerald-400',
      icon: Database,
      tooltip: 'Cryptographically indexed PostgreSQL 16 container storing tamper-evident audit logs',
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
      {kpis.map((kpi, idx) => {
        const IconComponent = kpi.icon;
        return (
          <Tooltip key={idx} content={kpi.tooltip} position="top" className="w-full">
            <div className="w-full bg-zinc-900/90 rounded-xl border border-zinc-800/90 p-4 shadow-lg card-hover">
              <div className="flex items-center justify-between text-zinc-400 mb-2">
                <span className="text-[10px] font-bold uppercase tracking-wider font-mono">
                  {kpi.title}
                </span>
                <IconComponent className="w-4 h-4 text-zinc-400" />
              </div>
              <div className="text-xl sm:text-2xl font-bold font-mono text-white tracking-tight tabular-nums">
                {kpi.value}
              </div>
              <div className={`mt-1 text-[11px] font-mono font-semibold flex items-center gap-1 ${kpi.badgeColor}`}>
                <span className="w-1.5 h-1.5 rounded-full bg-current" />
                <span>{kpi.badge}</span>
              </div>
            </div>
          </Tooltip>
        );
      })}
    </div>
  );
}
