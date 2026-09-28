import React from 'react';
import {
  Landmark,
  ShieldCheck,
  User,
  Shield,
  Wifi,
  WifiOff,
  LogOut,
  Layers,
  Database,
} from 'lucide-react';
import Tooltip from './common/Tooltip';

export default function Navbar({
  isBackendOnline,
  user,
  onSignOut,
  fleetStatus,
  dockerStatus = null,
  dataSourceMode = 'live',
  onToggleDataSourceMode,
  latencyMs = 0,
}) {
  const quarantinedCount = fleetStatus?.quarantined || 0;
  const isAdmin = user?.role === 'admin';

  return (
    <header className="sticky top-0 z-40 bg-zinc-950/95 backdrop-blur border-b border-zinc-800/80 px-4 sm:px-8 py-3 transition-colors font-sans">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Brand & Subtitle */}
        <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-start">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-zinc-900 border border-zinc-700/80 rounded-xl text-emerald-400 flex items-center justify-center shadow-sm">
              <Landmark className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-base font-bold tracking-tight text-white flex items-center gap-1.5">
                  APEX COMMERCIAL BANK
                </span>
                <span className="text-[10px] uppercase font-mono font-bold tracking-wider px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                  BFSI CORE
                </span>
              </div>
              <p className="text-[11px] text-zinc-400 flex items-center gap-1.5 font-medium">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                Enterprise Banking & Autonomous Security Infrastructure
              </p>
            </div>
          </div>

          {/* Mobile Status Dot */}
          <div className="md:hidden flex items-center gap-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                isBackendOnline ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
              }`}
            />
          </div>
        </div>

        {/* Center: Contextual Role Indicator Badge (No Switcher) */}
        <div className="flex items-center justify-center">
          {isAdmin ? (
            <div className="flex items-center gap-2 px-4 py-1.5 rounded-xl bg-rose-950/60 border border-rose-800/60 text-rose-200 text-xs font-semibold shadow-inner">
              <Shield className="w-3.5 h-3.5 text-rose-400 shrink-0" />
              <span>Cyber SOC Operations Console</span>
              {quarantinedCount > 0 && (
                <span className="ml-1 px-1.5 py-0.2 text-[10px] font-mono font-bold rounded-full bg-rose-900 border border-rose-500/60 text-rose-300 animate-pulse">
                  {quarantinedCount} Quarantined
                </span>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2 px-4 py-1.5 rounded-xl bg-indigo-950/60 border border-indigo-800/60 text-indigo-200 text-xs font-semibold shadow-inner">
              <User className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
              <span>Retail Client Banking Portal</span>
              <span className="text-[10px] font-mono text-zinc-400">
                Acct #{user?.accountId || '401'} ({user?.tier || 'GOLD'})
              </span>
            </div>
          )}
        </div>

        {/* Right Side: Gateway Health, Docker Stack, Data Mode & Session Profile */}
        <div className="flex flex-wrap items-center gap-2.5 w-full md:w-auto justify-end">
          {/* Data Mode Switcher Badge */}
          <Tooltip
            content={
              dataSourceMode === 'live'
                ? 'Operating in Live Backend Data Mode (click to switch to Demo Mock Mode)'
                : 'Operating in Demo Mock Sandbox Mode (click to switch to Live Backend Mode)'
            }
            position="bottom"
          >
            <button
              type="button"
              onClick={() => onToggleDataSourceMode && onToggleDataSourceMode(dataSourceMode === 'live' ? 'demo' : 'live')}
              className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-mono transition hover-lift ${
                dataSourceMode === 'live'
                  ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-300'
                  : 'bg-amber-950/60 border-amber-500/40 text-amber-300'
              }`}
            >
              <Database className="w-3 h-3" />
              <span>{dataSourceMode === 'live' ? 'LIVE DATA' : 'DEMO MOCK'}</span>
            </button>
          </Tooltip>

          {/* Docker Status Badge */}
          <Tooltip
            content={
              dockerStatus?.docker_connected
                ? 'Docker Engine active: PostgreSQL 16 + Redis 7 + Kafka KRaft operational'
                : 'Docker Engine offline: Operating in standalone mode with SQLite WAL database and L1 RAM cache'
            }
            position="bottom"
          >
            <div
              className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-mono transition ${
                dockerStatus?.docker_connected
                  ? 'bg-emerald-950/60 border-emerald-500/30 text-emerald-300'
                  : 'bg-zinc-900 border-zinc-700/80 text-zinc-300'
              }`}
            >
              <Layers className="w-3 h-3 text-zinc-400" />
              <span className="flex items-center gap-1">
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    dockerStatus?.docker_connected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
                  }`}
                />
                <span className="hidden xl:inline">
                  {dockerStatus?.docker_connected ? 'DOCKER ACTIVE' : 'STANDALONE (WAL)'}
                </span>
              </span>
            </div>
          </Tooltip>

          {/* Gateway Status Badge */}
          <Tooltip
            content={
              isBackendOnline
                ? `FastAPI PEP active on http://localhost:8000 (${latencyMs || 1}ms latency)`
                : 'FastAPI offline — using local frontend simulation'
            }
            position="bottom"
          >
            <div
              className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-mono transition ${
                isBackendOnline
                  ? 'bg-emerald-950/60 border-emerald-500/30 text-emerald-300'
                  : 'bg-rose-950/50 border-rose-500/30 text-rose-300'
              }`}
            >
              {isBackendOnline ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
              <span className="flex items-center gap-1">
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    isBackendOnline ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'
                  }`}
                />
                <span>{isBackendOnline ? `PEP :8000 (${latencyMs || 1}ms)` : 'OFFLINE'}</span>
              </span>
            </div>
          </Tooltip>

          {/* Session Profile Card */}
          <div className="flex items-center gap-2.5 pl-3 border-l border-zinc-800">
            <div className="text-right hidden sm:block">
              <p className="text-xs font-bold text-white leading-tight">
                {user?.name || (isAdmin ? 'SOC Lead Auditor' : 'Rahul Sharma')}
              </p>
              <p className="text-[10px] text-zinc-400 font-mono">
                {isAdmin ? 'SecOps Tier-4 Lead' : 'Acct #401 (Gold Tier)'}
              </p>
            </div>

            <div
              className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs shadow-sm border ${
                isAdmin
                  ? 'bg-rose-950/90 text-rose-300 border-rose-700/60'
                  : 'bg-indigo-950/90 text-indigo-300 border-indigo-700/60'
              }`}
            >
              {isAdmin ? 'SOC' : 'RS'}
            </div>

            {/* Sign Out Button */}
            <Tooltip content="Sign out of current authenticated session" position="bottom">
              <button
                type="button"
                onClick={onSignOut}
                className="p-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-rose-300 border border-zinc-800 hover:border-rose-900/60 transition hover-lift"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </Tooltip>
          </div>
        </div>
      </div>
    </header>
  );
}
