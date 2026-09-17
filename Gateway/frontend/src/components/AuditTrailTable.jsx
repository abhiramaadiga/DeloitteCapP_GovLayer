import React, { useState } from 'react';
import { ShieldAlert, ShieldCheck, RefreshCw, Search, Play, Pause, Terminal, ChevronDown, ChevronRight } from 'lucide-react';

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

export default function AuditTrailTable({
  logs,
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
    <div className="bg-slate-900/90 rounded-2xl border border-slate-800 shadow-xl overflow-hidden">
      {/* Header Bar */}
      <div className="p-4 sm:p-5 border-b border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
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
          <p className="text-xs text-slate-400 mt-0.5">
            Tamper-evident logs recording every autonomous agent request and cryptographic policy verdict
          </p>
        </div>

        {/* Controls: Auto-refresh, Manual Refresh */}
        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto justify-between md:justify-end">
          {/* Live stream status */}
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-medium border transition ${
              autoRefresh
                ? 'bg-emerald-950/70 border-emerald-500/50 text-emerald-300'
                : 'bg-slate-800 border-slate-700 text-slate-400'
            }`}
          >
            {autoRefresh ? <Play className="w-3.5 h-3.5 text-emerald-400" /> : <Pause className="w-3.5 h-3.5" />}
            <span>{autoRefresh ? 'LIVE STREAMING' : 'STREAM PAUSED'}</span>
          </button>

          {/* Manual Refresh Button */}
          <button
            onClick={onRefresh}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-medium text-slate-200 transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-emerald-400' : ''}`} />
            <span>Sync</span>
          </button>
        </div>
      </div>

      {/* Filter Tabs & Search Query */}
      <div className="px-4 sm:px-5 py-3 bg-slate-950/50 border-b border-slate-800/80 flex flex-col sm:flex-row items-center justify-between gap-3">
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
                onClick={() => setFilterDecision(tab)}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  isActive
                    ? activeClass
                    : 'bg-slate-800/60 hover:bg-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                {tab}
              </button>
            );
          })}
        </div>

        {/* Search Query */}
        <div className="relative w-full sm:w-72">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search endpoint, agent, or XAI factor..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1 text-xs text-white placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 transition"
          />
        </div>
      </div>

      {/* Audit Logs Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-950/80 text-slate-400 uppercase font-semibold text-[11px] tracking-wider border-b border-slate-800">
            <tr>
              <th className="px-4 py-3 w-8"></th>
              <th className="px-4 py-3">Timestamp</th>
              <th className="px-4 py-3">Agent ID</th>
              <th className="px-4 py-3">Endpoint & Method</th>
              <th className="px-4 py-3">Risk</th>
              <th className="px-4 py-3">PEP Verdict</th>
              <th className="px-4 py-3">Latency</th>
              <th className="px-4 py-3">Explainable AI (XAI) Causal Factors</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {filteredLogs.length === 0 ? (
              <tr>
                <td colSpan={8} className="text-center py-10 text-slate-500 font-sans text-xs">
                  No audit trail records found matching criteria.
                </td>
              </tr>
            ) : (
              filteredLogs.map((log) => {
                const isBlocked = log.decision === 'BLOCKED';
                const isQuarantined = log.decision === 'QUARANTINED';
                const isExpanded = expandedLogId === log.id;
                const risk = log.risk_score || 0.1;

                return (
                  <React.Fragment key={log.id}>
                    <tr
                      onClick={() => toggleExpand(log.id)}
                      className={`cursor-pointer hover:bg-slate-800/40 transition-colors ${
                        isBlocked
                          ? 'bg-rose-950/15'
                          : isQuarantined
                          ? 'bg-purple-950/15'
                          : ''
                      }`}
                    >
                      {/* Expand Chevron */}
                      <td className="px-3 py-3 text-slate-500">
                        {isExpanded ? (
                          <ChevronDown className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronRight className="w-3.5 h-3.5" />
                        )}
                      </td>

                      {/* Timestamp */}
                      <td className="px-4 py-3 text-slate-400 whitespace-nowrap text-[11px]">
                        {log.timestamp}
                      </td>

                      {/* Agent ID & Role */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="font-bold text-slate-200">{log.agent_id}</span>
                        {log.role && (
                          <div className="text-[10px] text-slate-500 font-sans">{log.role}</div>
                        )}
                      </td>

                      {/* Endpoint & Method */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                              log.method === 'GET'
                                ? 'bg-blue-950 text-blue-300 border border-blue-800'
                                : 'bg-amber-950 text-amber-300 border border-amber-800'
                            }`}
                          >
                            {log.method}
                          </span>
                          <span className="text-slate-300 text-xs">{log.endpoint}</span>
                        </div>
                      </td>

                      {/* Risk Score */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span
                          className={`font-bold text-xs ${
                            risk >= 0.7
                              ? 'text-rose-400'
                              : risk >= 0.4
                              ? 'text-amber-400'
                              : 'text-emerald-400'
                          }`}
                        >
                          {risk.toFixed(2)}
                        </span>
                      </td>

                      {/* Verdict Badge */}
                      <td className="px-4 py-3 whitespace-nowrap">
                        {isBlocked ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-950 border border-rose-500/60 text-rose-300">
                            <ShieldAlert className="w-3 h-3" />
                            BLOCKED
                          </span>
                        ) : isQuarantined ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-950 border border-purple-500/60 text-purple-300 animate-pulse">
                            QUARANTINED
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-950 border border-emerald-500/40 text-emerald-300">
                            <ShieldCheck className="w-3 h-3" />
                            ALLOWED
                          </span>
                        )}
                      </td>

                      {/* Latency */}
                      <td className="px-4 py-3 whitespace-nowrap text-[11px] text-cyan-400">
                        {log.latency_ms ? `${log.latency_ms}ms` : '<1.2ms'}
                      </td>

                      {/* XAI Factors (Pills) */}
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {reasons.length > 0 ? (
                            reasons.map((factor, fIdx) => {
                              const factorStr = String(factor);
                              const isViolate =
                                factorStr.toLowerCase().includes('violation') ||
                                factorStr.toLowerCase().includes('denial') ||
                                factorStr.toLowerCase().includes('malicious') ||
                                factorStr.toLowerCase().includes('spike') ||
                                factorStr.toLowerCase().includes('terminated');
                              return (
                                <span
                                  key={fIdx}
                                  className={`text-[10px] px-2 py-0.5 rounded-md font-sans leading-relaxed ${
                                    isViolate
                                      ? 'bg-rose-950/70 border border-rose-600/50 text-rose-300'
                                      : 'bg-slate-800/80 border border-slate-700 text-slate-300'
                                  }`}
                                >
                                  {factorStr}
                                </span>
                              );
                            })
                          ) : (
                            <span className="text-[10px] text-slate-500 font-sans">
                              Benign fast-path execution
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>

                    {/* Expandable Details Row */}
                    {isExpanded && (
                      <tr className="bg-slate-950/90 text-xs">
                        <td colSpan={8} className="p-4 pl-12 border-b border-slate-800/80">
                          <div className="bg-slate-900 rounded-xl p-4 border border-slate-800 font-mono space-y-2">
                            <div className="text-slate-400 font-bold uppercase text-[10px] tracking-wider text-indigo-400 mb-2">
                              Full Cryptographic Audit Envelope (Log #{log.id})
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[11px]">
                              <div>
                                <span className="text-slate-500">Record ID:</span>{' '}
                                <span className="text-slate-300">{log.id}</span>
                              </div>
                              <div>
                                <span className="text-slate-500">Timestamp:</span>{' '}
                                <span className="text-slate-300">{log.timestamp}</span>
                              </div>
                              <div>
                                <span className="text-slate-500">Decision:</span>{' '}
                                <span className="text-slate-300 font-bold">{log.decision}</span>
                              </div>
                              <div>
                                <span className="text-slate-500">Agent ID:</span>{' '}
                                <span className="text-slate-300">{log.agent_id}</span>
                              </div>
                              <div>
                                <span className="text-slate-500">Role Scope:</span>{' '}
                                <span className="text-slate-300">{log.role || 'N/A'}</span>
                              </div>
                              <div>
                                <span className="text-slate-500">PEP Latency:</span>{' '}
                                <span className="text-cyan-400">{log.latency_ms}ms</span>
                              </div>
                            </div>
                            <div className="pt-2 border-t border-slate-800 text-[11px]">
                              <span className="text-slate-500">XAI Causal Factors:</span>
                              <ul className="list-disc list-inside mt-1 space-y-1 text-slate-300 font-sans">
                                {reasons.length > 0 ? (
                                  reasons.map((r, i) => <li key={i}>{String(r)}</li>)
                                ) : (
                                  <li className="text-slate-500">Benign fast-path execution</li>
                                )}
                              </ul>
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
