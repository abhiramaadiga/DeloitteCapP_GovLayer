import React from 'react';
import { Database, Layers, Activity } from 'lucide-react';
import Tooltip from '../common/Tooltip';

export default function InfraStatusBar({
  isBackendOnline = true,
  dockerStatus = null,
  dataSourceMode = 'live',
  latencyMs = 0,
}) {
  const isDockerUp = dockerStatus?.docker_connected === true;
  const isDemo = dataSourceMode === 'demo';

  return (
    <div className="flex flex-wrap items-center gap-2.5 font-mono text-xs">
      {/* 1. Backend Server Status Badge */}
      <Tooltip
        content={
          isBackendOnline
            ? `FastAPI Zero-Trust Gateway running on http://localhost:8000 (Roundtrip latency: ${latencyMs || '<2'}ms)`
            : 'FastAPI Gateway offline — running in local isolated frontend fallback'
        }
        position="bottom"
      >
        <div className={`px-3 py-1.5 rounded-xl border flex items-center gap-2 card-hover transition ${
          isBackendOnline
            ? 'bg-zinc-950 border-emerald-900/40 text-emerald-300'
            : 'bg-zinc-950 border-rose-900/40 text-rose-300'
        }`}>
          <Activity className={`w-3.5 h-3.5 ${isBackendOnline ? 'text-emerald-400' : 'text-rose-400'}`} />
          <div className="text-left">
            <span className="text-zinc-500 block text-[9px] uppercase font-sans font-semibold">Backend API</span>
            <span className="flex items-center gap-1.5 font-bold">
              <span className={`w-1.5 h-1.5 rounded-full ${isBackendOnline ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
              <span>{isBackendOnline ? `:8000 LIVE (${latencyMs || 1}ms)` : 'OFFLINE'}</span>
            </span>
          </div>
        </div>
      </Tooltip>

      {/* 2. Docker Engine / Distributed Stack Badge */}
      <Tooltip
        content={
          isDockerUp
            ? 'Docker Engine active: PostgreSQL 16.2 (:5432) + Redis 7 (:6379) + Kafka KRaft (:9092) are fully connected'
            : 'Docker Engine offline: Operating in standalone mode with SQLite WAL database (governance_audit.db) + In-Memory L1 Revocation Cache + Local Queue'
        }
        position="bottom"
      >
        <div className={`px-3 py-1.5 rounded-xl border flex items-center gap-2 card-hover transition ${
          isDockerUp
            ? 'bg-zinc-950 border-emerald-900/40 text-emerald-300'
            : 'bg-zinc-950 border-amber-900/40 text-amber-300'
        }`}>
          <Layers className={`w-3.5 h-3.5 ${isDockerUp ? 'text-emerald-400' : 'text-amber-400'}`} />
          <div className="text-left">
            <span className="text-zinc-500 block text-[9px] uppercase font-sans font-semibold">Docker Stack</span>
            <span className="flex items-center gap-1.5 font-bold">
              <span className={`w-1.5 h-1.5 rounded-full ${isDockerUp ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
              <span>{isDockerUp ? 'DOCKER ACTIVE' : 'STANDALONE (WAL+L1)'}</span>
            </span>
          </div>
        </div>
      </Tooltip>

      {/* 3. Data Source Mode Badge */}
      <Tooltip
        content={
          isDemo
            ? 'Demo Mock Mode: Using simulated baseline transactions and local mock database'
            : 'Live Mode: Direct execution against FastAPI backend endpoints and persistent database'
        }
        position="bottom"
      >
        <div className={`px-3 py-1.5 rounded-xl border flex items-center gap-2 card-hover transition ${
          !isDemo
            ? 'bg-zinc-950 border-cyan-900/40 text-cyan-300'
            : 'bg-zinc-950 border-violet-900/40 text-violet-300'
        }`}>
          <Database className={`w-3.5 h-3.5 ${!isDemo ? 'text-cyan-400' : 'text-violet-400'}`} />
          <div className="text-left">
            <span className="text-zinc-500 block text-[9px] uppercase font-sans font-semibold">Data Source</span>
            <span className="font-bold flex items-center gap-1">
              <span>{!isDemo ? 'LIVE BACKEND' : 'DEMO MOCK'}</span>
            </span>
          </div>
        </div>
      </Tooltip>
    </div>
  );
}
