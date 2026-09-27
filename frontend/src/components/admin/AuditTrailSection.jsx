import React, { useState } from 'react';
import { Terminal, RefreshCw, Search, Play, Pause, ChevronDown, ChevronRight } from 'lucide-react';
import Tooltip from '../common/Tooltip';

const normalizeXaiReasons = (reasons) => {
  if (Array.isArray(reasons)) return reasons;
  if (typeof reasons === 'string') {
    try {
      const parsed = JSON.parse(reasons);
      if (Array.isArray(parsed)) return parsed;
    } catch {}
    return [reasons];
  }
  return [];
};

export default function AuditTrailSection({
  logs = [],
  filterDecision,
  setFilterDecision,
  onRefresh,
  autoRefresh,
  setAutoRefresh,
  loading,
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedLogId, setExpandedLogId] = useState(null);

  const filteredLogs = logs.filter((log) => {
    const matchesDecision = filterDecision === 'ALL' || log.decision === filterDecision;
    const reasons = normalizeXaiReasons(log.xai_reasons);
    const matchesSearch =
      !searchQuery.trim() ||
      log.agent_id?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.endpoint?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.role?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      reasons.some((r) => String(r).toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesDecision && matchesSearch;
  });

  const toggleExpand = (id) => {
    setExpandedLogId(expandedLogId === id ? null : id);
  };

  return (
    <div className="bg-zinc-900/90 rounded-2xl border border-zinc-800/90 shadow-xl overflow-hidden card-hover">
      {/* Header Bar */}
      <div className="p-4 sm:p-5 border-b border-zinc-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Terminal className="w-5 h-5 text-emerald-400" />
            <h3 className="text-sm sm:text-base font-bold text-white">
              Live Security Audit Trail & Explainable AI (XAI)
            </h3>
            <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-950 border border-emerald-700/60 text-emerald-300 font-mono">
              SOX-404 Immutable Stream
            </span>
          </div>
          <p className="text-xs text-zinc-400 mt-0.5">
            Tamper-evident logs recording every autonomous agent request and cryptographic policy verdict
          </p>
        </div>

        {/* Controls: Auto-refresh, Manual Refresh */}
        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto justify-between md:justify-end">
          <Tooltip content={autoRefresh ? "Pause auto-polling every 4 seconds" : "Resume auto-polling stream"} position="top">
            <button
              type="button"
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-medium border transition hover-lift ${
                autoRefresh
                  ? 'bg-emerald-950/70 border-emerald-500/50 text-emerald-300'
                  : 'bg-zinc-800 border-zinc-700 text-zinc-400'
              }`}
            >
              {autoRefresh ? <Play className="w-3.5 h-3.5 text-emerald-400" /> : <Pause className="w-3.5 h-3.5" />}
              <span>{autoRefresh ? 'LIVE STREAM' : 'STREAM PAUSED'}</span>
            </button>
          </Tooltip>

          <Tooltip content="Manually refresh PostgreSQL audit records" position="top">
            <button
              type="button"
              onClick={onRefresh}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-xs font-medium text-zinc-200 transition hover-lift disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-emerald-400' : ''}`} />
              <span>Sync</span>
            </button>
          </Tooltip>
        </div>
      </div>

      {/* Filter Tabs & Search Query */}
      <div className="px-4 sm:px-5 py-3 bg-zinc-950/50 border-b border-zinc-800/80 flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Decision Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
          {['ALL', 'ALLOWED', 'BLOCKED', 'QUARANTINED'].map((tab) => {
            const isActive = filterDecision === tab;
            let activeClass = 'bg-indigo-600 text-white shadow-md';
            if (tab === 'ALLOWED') activeClass = 'bg-emerald-600 text-white shadow-md shadow-emerald-900/30';
            if (tab === 'BLOCKED') activeClass = 'bg-rose-600 text-white shadow-md shadow-rose-900/30';
            if (tab === 'QUARANTINED') activeClass = 'bg-purple-600 text-white shadow-md shadow-purple-900/30';

            return (
              <button
                key={tab}
                type="button"
                onClick={() => setFilterDecision(tab)}
                className={`px-3 py-1 rounded-lg text-xs font-mono font-semibold transition ${
                  isActive
                    ? activeClass
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60'
                }`}
              >
                {tab}
              </button>
            );
          })}
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-64">
          <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search endpoint, agent, or XAI factor..."
            className="w-full bg-zinc-950 border border-zinc-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder:text-zinc-500 focus:outline-none focus:border-indigo-500 transition font-sans"
          />
        </div>
      </div>

      {/* Logs Table */}
      <div className="overflow-x-auto max-h-[460px] overflow-y-auto">
        <table className="w-full text-left text-xs text-zinc-300">
          <thead className="sticky top-0 bg-zinc-950/95 backdrop-blur text-zinc-400 uppercase font-semibold text-[11px] tracking-wider border-b border-zinc-800 font-mono z-10">
            <tr>
              <th className="px-4 py-3">Timestamp</th>
              <th className="px-4 py-3">Agent ID</th>
              <th className="px-4 py-3">Action Endpoint</th>
              <th className="px-3 py-3">Decision</th>
              <th className="px-3 py-3">Latency</th>
              <th className="px-3 py-3">Risk</th>
              <th className="px-4 py-3">Explainable AI (XAI) Factors</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/60 font-mono">
            {filteredLogs.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-10 text-zinc-500">
                  {loading ? 'Fetching audit records from PostgreSQL...' : 'No audit records matching query criteria.'}
                </td>
              </tr>
            ) : (
              filteredLogs.map((log) => {
                const isBlocked = log.decision === 'BLOCKED' || log.decision === 'QUARANTINED';
                const isAllowed = log.decision === 'ALLOWED';
                const reasons = normalizeXaiReasons(log.xai_reasons);
                const isExpanded = expandedLogId === log.id;

                return (
                  <React.Fragment key={log.id}>
                    <tr
                      onClick={() => toggleExpand(log.id)}
                      className={`cursor-pointer hover:bg-zinc-800/40 transition-colors ${
                        isBlocked ? 'bg-rose-950/15' : ''
                      }`}
                    >
                      <td className="px-4 py-3 text-zinc-400 whitespace-nowrap text-[11px]">
                        <div className="flex items-center gap-1.5">
                          {isExpanded ? <ChevronDown className="w-3 h-3 text-zinc-400" /> : <ChevronRight className="w-3 h-3 text-zinc-500" />}
                          <span>{log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : 'Just now'}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 font-bold text-white whitespace-nowrap">
                        {log.agent_id}
                      </td>
                      <td className="px-4 py-3 text-zinc-200">
                        <span className="px-2 py-0.5 rounded bg-zinc-950 border border-zinc-800 text-[11px]">
                          {log.endpoint}
                        </span>
                      </td>
                      <td className="px-3 py-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                            isAllowed
                              ? 'bg-emerald-950/80 border-emerald-500/40 text-emerald-300'
                              : 'bg-rose-950/80 border-rose-500/40 text-rose-300'
                          }`}
                        >
                          {log.decision}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-zinc-400 tabular-nums">
                        {Number(log.pep_latency_ms || 1.15).toFixed(2)}ms
                      </td>
                      <td className="px-3 py-3 tabular-nums">
                        <span className={log.risk_score > 0.6 ? 'text-rose-400 font-bold' : 'text-zinc-300'}>
                          {Number(log.risk_score || 0.1).toFixed(2)}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {reasons.length === 0 ? (
                            <span className="text-[10px] text-zinc-500">BENIGN_FAST_PATH</span>
                          ) : (
                            reasons.map((r, i) => (
                              <span
                                key={i}
                                className={`text-[10px] px-1.5 py-0.2 rounded border ${
                                  String(r).includes('HIGH') || String(r).includes('BURST') || String(r).includes('VIOLATION')
                                    ? 'bg-rose-950 border-rose-800 text-rose-300'
                                    : 'bg-zinc-950 border-zinc-800 text-zinc-400'
                                }`}
                              >
                                {r}
                              </span>
                            ))
                          )}
                        </div>
                      </td>
                    </tr>

                    {/* Expandable Technical Detail */}
                    {isExpanded && (
                      <tr className="bg-zinc-950/90 text-[11px] text-zinc-400">
                        <td colSpan={7} className="px-6 py-4 space-y-2 border-t border-b border-zinc-800">
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div>
                              <span className="text-[10px] uppercase text-zinc-500 block">Record UUID</span>
                              <span className="text-zinc-200">{log.id}</span>
                            </div>
                            <div>
                              <span className="text-[10px] uppercase text-zinc-500 block">NHI Assigned Role</span>
                              <span className="text-zinc-200">{log.role || 'tier1_customer_service'}</span>
                            </div>
                            <div>
                              <span className="text-[10px] uppercase text-zinc-500 block">Governance Engine</span>
                              <span className="text-emerald-400 font-semibold">FastAPI PEP + Isolation Forest</span>
                            </div>
                            <div>
                              <span className="text-[10px] uppercase text-zinc-500 block">Compliance Standard</span>
                              <span className="text-indigo-400 font-semibold">SOX Section 404 / FFIEC Cat-3</span>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
