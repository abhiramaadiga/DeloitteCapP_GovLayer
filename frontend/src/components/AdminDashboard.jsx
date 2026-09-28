import React, { useState } from 'react';
import KpiRibbon from './admin/KpiRibbon';
import InfraStatusBar from './admin/InfraStatusBar';
import ThreatGauge from './ThreatGauge';
import AgentFleetSection from './admin/AgentFleetSection';
import AuditTrailSection from './admin/AuditTrailSection';
import DriftRetrainSection from './admin/DriftRetrainSection';
import ReinstatementModal from './ReinstatementModal';
import DatabaseInspector from './DatabaseInspector';
import PolicyManagementSection from './admin/PolicyManagementSection';
import Tooltip from './common/Tooltip';
import { RotateCcw, AlertTriangle, Loader2, X, ShieldCheck, Database, Sliders } from 'lucide-react';

export default function AdminDashboard({
  telemetry = null,
  driftStatus = null,
  agents = [],
  auditLogs = [],
  filterDecision,
  setFilterDecision,
  onRefreshLogs,
  autoRefresh,
  setAutoRefresh,
  logsLoading,
  onQuarantineAgent,
  onLiftQuarantine,
  onRetrainModel,
  retrainLoading,
  isBackendOnline = true,
  onResetSystemValues,
  resetLoading = false,
  dockerStatus = null,
  dataSourceMode = 'live',
  onToggleDataSourceMode,
  latencyMs = 0,
}) {
  const [activeAdminTab, setActiveAdminTab] = useState('soc'); // 'soc' | 'db'
  const [selectedAgentForReinstate, setSelectedAgentForReinstate] = useState(null);
  const [reinstateModalOpen, setReinstateModalOpen] = useState(false);
  const [resetModalOpen, setResetModalOpen] = useState(false);

  const totalAgents = agents.length;
  const quarantinedCount = agents.filter((a) => a.status === 'QUARANTINED').length;

  const telemetryRisk = telemetry?.rolling_window?.mean_risk_score || 0.14;
  const effectiveThreatScore = quarantinedCount > 0 ? Math.max(telemetryRisk, 0.72) : telemetryRisk;

  const handleOpenReinstate = (agent) => {
    setSelectedAgentForReinstate(agent);
    setReinstateModalOpen(true);
  };

  const handleConfirmReinstate = async (agentId, justification, analystId) => {
    await onLiftQuarantine(agentId, justification, analystId);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-8 py-8 space-y-6 animate-page-enter">
      {/* Top Banner with Title & Infrastructure Badges */}
      <div className="bg-zinc-900/90 rounded-2xl border border-zinc-800/90 p-6 shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 backdrop-blur card-hover">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-xs uppercase font-mono font-bold tracking-widest text-rose-400 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
              Cyber SOC Operations Command
            </span>
            <span className="text-[10px] bg-rose-950 text-rose-300 border border-rose-800/80 px-2 py-0.5 rounded-full font-mono">
              FFIEC Cat-3 Governed
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Autonomous Agent Security & Governance Console
          </h1>
          <p className="text-xs sm:text-sm text-zinc-400 mt-1">
            Real-time policy enforcement, non-human identity revocation, and continuous ML drift surveillance.
          </p>
        </div>

        {/* Infrastructure Status Badges, Data Mode Switcher and Reset Values Button */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 shrink-0">
          <InfraStatusBar
            isBackendOnline={isBackendOnline}
            dockerStatus={dockerStatus}
            dataSourceMode={dataSourceMode}
            latencyMs={latencyMs}
          />

          {/* Interactive Data Mode Toggle Switch (Live Backend vs Demo Mock) */}
          <div className="flex items-center gap-1 p-1 bg-zinc-950/90 border border-zinc-800 rounded-xl shadow-inner font-mono text-xs">
            <button
              type="button"
              onClick={() => onToggleDataSourceMode && onToggleDataSourceMode('live')}
              className={`px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1.5 transition ${
                dataSourceMode === 'live'
                  ? 'bg-emerald-950/80 border border-emerald-500/50 text-emerald-300 shadow-sm'
                  : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900/50'
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${dataSourceMode === 'live' ? 'bg-emerald-400 animate-pulse' : 'bg-zinc-600'}`} />
              <span>Live Data</span>
            </button>
            <button
              type="button"
              onClick={() => onToggleDataSourceMode && onToggleDataSourceMode('demo')}
              className={`px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1.5 transition ${
                dataSourceMode === 'demo'
                  ? 'bg-amber-950/80 border border-amber-500/50 text-amber-300 shadow-sm'
                  : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900/50'
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${dataSourceMode === 'demo' ? 'bg-amber-400' : 'bg-zinc-600'}`} />
              <span>Demo Mock</span>
            </button>
          </div>
          
          {onResetSystemValues && (
            <Tooltip content="Restore all balances, deposits, transaction ledger, and ML telemetry to clean initial baseline" position="bottom">
              <button
                type="button"
                onClick={() => setResetModalOpen(true)}
                disabled={resetLoading}
                className="px-3.5 py-2 rounded-xl bg-zinc-850 hover:bg-zinc-800 border border-zinc-700/80 hover:border-amber-600/70 text-zinc-200 hover:text-amber-300 text-xs font-semibold flex items-center gap-2 shadow-md transition hover-lift disabled:opacity-50"
              >
                {resetLoading ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-400" />
                ) : (
                  <RotateCcw className="w-3.5 h-3.5 text-amber-400" />
                )}
                <span>Reset Values</span>
              </button>
            </Tooltip>
          )}
        </div>
      </div>

      {/* Main Navigation Tabs */}
      <div className="flex items-center gap-2 p-1.5 bg-zinc-900/90 border border-zinc-800 rounded-2xl shadow-lg backdrop-blur">
        <button
          type="button"
          onClick={() => setActiveAdminTab('soc')}
          className={`flex-1 sm:flex-initial px-5 py-2.5 rounded-xl font-semibold text-xs sm:text-sm flex items-center justify-center gap-2 transition ${
            activeAdminTab === 'soc'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-900/30'
              : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60'
          }`}
        >
          <ShieldCheck className="w-4 h-4 text-indigo-200" />
          <span>Security Operations Overview</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveAdminTab('policies')}
          className={`flex-1 sm:flex-initial px-5 py-2.5 rounded-xl font-semibold text-xs sm:text-sm flex items-center justify-center gap-2 transition ${
            activeAdminTab === 'policies'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-900/30'
              : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60'
          }`}
        >
          <Sliders className="w-4 h-4 text-indigo-200" />
          <span>Policy Governance</span>
          <span className="hidden sm:inline text-[10px] font-mono px-2 py-0.5 rounded-full bg-zinc-950/80 border border-zinc-700/80 text-emerald-300 ml-1">
            Live PEP
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveAdminTab('db')}
          className={`flex-1 sm:flex-initial px-5 py-2.5 rounded-xl font-semibold text-xs sm:text-sm flex items-center justify-center gap-2 transition ${
            activeAdminTab === 'db'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-900/30'
              : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60'
          }`}
        >
          <Database className="w-4 h-4 text-indigo-200" />
          <span>Database Explorer</span>
          <span className="hidden sm:inline text-[10px] font-mono px-2 py-0.5 rounded-full bg-zinc-950/80 border border-zinc-700/80 text-indigo-300 ml-1">
            PostgreSQL 16
          </span>
        </button>
      </div>

      {/* TAB CONTENT 1: SOC OVERVIEW */}
      {activeAdminTab === 'soc' && (
        <div className="space-y-8 animate-fadeIn">
          {/* KPI Ribbon: 6 Executive Metrics */}
          <KpiRibbon
            totalAgents={totalAgents}
            quarantinedCount={quarantinedCount}
            telemetry={telemetry}
            isBackendOnline={isBackendOnline}
          />

      {/* Mid-Row: Threat Speedometer & ML Drift Monitor */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-5">
          <ThreatGauge threatScore={effectiveThreatScore} />
        </div>
        <div className="lg:col-span-7">
          <DriftRetrainSection
            driftStatus={driftStatus}
            telemetry={telemetry}
            onRetrain={onRetrainModel}
            retrainLoading={retrainLoading}
          />
        </div>
      </div>

      {/* Governed Agent Fleet Management */}
      <AgentFleetSection
        agents={agents}
        onQuarantine={onQuarantineAgent}
        onOpenReinstateModal={handleOpenReinstate}
      />

      {/* Live Security Audit Trail */}
      <AuditTrailSection
        logs={auditLogs}
        filterDecision={filterDecision}
        setFilterDecision={setFilterDecision}
        onRefresh={onRefreshLogs}
        autoRefresh={autoRefresh}
        setAutoRefresh={setAutoRefresh}
        loading={logsLoading}
      />
    </div>
  )}

  {/* TAB CONTENT 2: POLICY GOVERNANCE */}
  {activeAdminTab === 'policies' && (
    <div className="animate-fadeIn">
      <PolicyManagementSection isBackendOnline={isBackendOnline} />
    </div>
  )}

  {/* TAB CONTENT 3: DATABASE EXPLORER */}
  {activeAdminTab === 'db' && (
    <div className="animate-fadeIn">
      <DatabaseInspector isBackendOnline={isBackendOnline} />
    </div>
  )}

  {/* FFIEC Reinstatement Modal */}
  <ReinstatementModal
    isOpen={reinstateModalOpen}
    onClose={() => setReinstateModalOpen(false)}
    agent={selectedAgentForReinstate}
    onConfirm={handleConfirmReinstate}
    onConfirmReinstate={handleConfirmReinstate}
  />

      {/* System Reset Confirmation Modal */}
      {resetModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-fadeIn">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-5 card-hover popup-scale">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
              <div className="flex items-center gap-2.5 text-amber-400 font-bold text-base">
                <AlertTriangle className="w-5 h-5" />
                <span>Reset Demo System Values</span>
              </div>
              <button
                type="button"
                onClick={() => setResetModalOpen(false)}
                className="p-1 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-zinc-300 leading-relaxed">
              This operation will restore all demo balances, accounts, and security controls back to their fresh initial state:
            </p>

            <ul className="text-xs text-zinc-400 space-y-2 bg-zinc-950/80 p-3.5 rounded-xl border border-zinc-800/80 font-mono">
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                <span>Rahul Sharma (#401) balance: ₹84,250.00</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
                <span>Fixed Deposit (#FD-901): LOCKED (₹500,000.00)</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                <span>Transaction Activity Ledger: Restored to baseline</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                <span>Agent Fleet Quarantines: Reinstated to ACTIVE</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
                <span>ML Telemetry & Buffers: Reset to baseline</span>
              </li>
            </ul>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setResetModalOpen(false)}
                disabled={resetLoading}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={async () => {
                  if (onResetSystemValues) {
                    await onResetSystemValues();
                  }
                  setResetModalOpen(false);
                }}
                disabled={resetLoading}
                className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold flex items-center gap-2 shadow-lg shadow-amber-950/50 transition hover-lift disabled:opacity-50"
              >
                {resetLoading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Resetting Values...</span>
                  </>
                ) : (
                  <>
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Confirm Reset</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

