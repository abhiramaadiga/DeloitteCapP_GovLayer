import React, { useState } from 'react';
import {
  AlertOctagon,
  Unlock,
  Search,
  Bot,
  User,
  Building,
  Users,
  Shield,
  CheckCircle2,
  Lock,
  Layers,
  ShieldAlert,
  ShieldCheck,
  LayoutGrid,
  Table as TableIcon
} from 'lucide-react';
import Tooltip from '../common/Tooltip';

export default function AgentFleetSection({
  agents = [],
  onQuarantine,
  onOpenReinstateModal,
}) {
  const [searchFilter, setSearchFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('ALL'); // 'ALL' | 'CUSTOMER' | 'INSTITUTIONAL'
  const [viewMode, setViewMode] = useState('cards'); // 'cards' | 'table'

  const customerAgents = agents.filter(
    (a) => a.fleet_type === 'customer' || a.agent_id.startsWith('Agent-Support')
  );
  const institutionalAgents = agents.filter(
    (a) => a.fleet_type === 'institutional' || !a.agent_id.startsWith('Agent-Support')
  );

  const filteredAgents = agents.filter((a) => {
    const isCust = a.fleet_type === 'customer' || a.agent_id.startsWith('Agent-Support');
    if (categoryFilter === 'CUSTOMER' && !isCust) return false;
    if (categoryFilter === 'INSTITUTIONAL' && isCust) return false;

    const term = searchFilter.toLowerCase();
    return (
      a.agent_id.toLowerCase().includes(term) ||
      a.role.toLowerCase().includes(term) ||
      (a.description && a.description.toLowerCase().includes(term)) ||
      (a.customer_name && a.customer_name.toLowerCase().includes(term)) ||
      (a.account_id && a.account_id.toLowerCase().includes(term))
    );
  });

  return (
    <div className="bg-zinc-900/90 rounded-2xl border border-zinc-800/90 shadow-xl overflow-hidden card-hover space-y-0">
      {/* Section Header */}
      <div className="p-4 sm:p-5 border-b border-zinc-800 flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Bot className="w-5 h-5 text-indigo-400" />
              <h3 className="text-sm sm:text-base font-bold text-white">
                Governed Agent Fleet Management
              </h3>
              <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-950 border border-indigo-700/60 text-indigo-300 font-mono">
                {agents.length} Non-Human Identities
              </span>
            </div>
            <p className="text-xs text-zinc-400 mt-0.5">
              Multi-Tenant Agent Isolation: Dedicated Customer Assistants & Institutional Fleet PEP Revocation Controls
            </p>
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            {/* View Mode Toggle */}
            <div className="bg-zinc-950 p-1 rounded-xl border border-zinc-800 flex items-center gap-1">
              <button
                type="button"
                onClick={() => setViewMode('cards')}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
                  viewMode === 'cards'
                    ? 'bg-indigo-600 text-white shadow-md'
                    : 'text-zinc-400 hover:text-white'
                }`}
              >
                <LayoutGrid className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">User-Wise Cards</span>
              </button>
              <button
                type="button"
                onClick={() => setViewMode('table')}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
                  viewMode === 'table'
                    ? 'bg-indigo-600 text-white shadow-md'
                    : 'text-zinc-400 hover:text-white'
                }`}
              >
                <TableIcon className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Full Table</span>
              </button>
            </div>

            {/* Search Input */}
            <div className="relative flex-1 sm:w-64">
              <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                placeholder="Search agent, customer, or account..."
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder:text-zinc-500 focus:outline-none focus:border-indigo-500 transition font-sans"
              />
            </div>
          </div>
        </div>

        {/* Category Filters & Tenant Isolation Explainer */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-zinc-800/60">
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setCategoryFilter('ALL')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
                categoryFilter === 'ALL'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-900/30'
                  : 'bg-zinc-950 text-zinc-400 hover:text-zinc-200 border border-zinc-800'
              }`}
            >
              <Users className="w-3.5 h-3.5" />
              <span>All Governed Fleet ({agents.length})</span>
            </button>

            <button
              type="button"
              onClick={() => setCategoryFilter('CUSTOMER')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
                categoryFilter === 'CUSTOMER'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-900/30'
                  : 'bg-zinc-950 text-zinc-400 hover:text-zinc-200 border border-zinc-800'
              }`}
            >
              <User className="w-3.5 h-3.5 text-emerald-400" />
              <span>Customer Assistants ({customerAgents.length})</span>
            </button>

            <button
              type="button"
              onClick={() => setCategoryFilter('INSTITUTIONAL')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
                categoryFilter === 'INSTITUTIONAL'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-900/30'
                  : 'bg-zinc-950 text-zinc-400 hover:text-zinc-200 border border-zinc-800'
              }`}
            >
              <Building className="w-3.5 h-3.5 text-blue-400" />
              <span>Institutional Fleet ({institutionalAgents.length})</span>
            </button>
          </div>

          <div className="hidden lg:flex items-center gap-2 text-[11px] font-mono text-zinc-400 bg-zinc-950 px-3 py-1 rounded-lg border border-zinc-800">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Per-User Isolation: Blocking one user's agent does NOT affect other users</span>
          </div>
        </div>
      </div>

      {/* VIEW MODE 1: USER-WISE CARDS (Clean, Simple, Easy-to-Understand) */}
      {viewMode === 'cards' && (
        <div className="p-4 sm:p-6 space-y-6">
          {/* Section 1: Customer Virtual Assistants (By User Tenant) */}
          {(categoryFilter === 'ALL' || categoryFilter === 'CUSTOMER') && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <User className="w-4 h-4 text-emerald-400" />
                  <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-300 font-mono">
                    User-Wise Dedicated Assistants (Isolated Per Tenant)
                  </h4>
                </div>
                <span className="text-[11px] font-mono text-zinc-500">
                  Zero Cross-Tenant Contamination
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {customerAgents.map((agent) => {
                  const isQuarantined = agent.status === 'QUARANTINED';
                  const risk = agent.risk_score || 0.1;
                  const tierColors = {
                    PLATINUM: 'bg-purple-950/80 text-purple-300 border-purple-800',
                    GOLD: 'bg-amber-950/80 text-amber-300 border-amber-800',
                    SILVER: 'bg-zinc-800 text-zinc-300 border-zinc-700',
                  };
                  const badgeClass = tierColors[agent.tier] || 'bg-zinc-800 text-zinc-300 border-zinc-700';

                  return (
                    <div
                      key={agent.agent_id}
                      className={`p-5 rounded-2xl border transition-all flex flex-col justify-between ${
                        isQuarantined
                          ? 'bg-rose-950/20 border-rose-800/80 shadow-lg shadow-rose-950/40'
                          : 'bg-zinc-950/80 border-zinc-800 hover:border-zinc-750 shadow-md'
                      }`}
                    >
                      <div>
                        {/* Top Ribbon */}
                        <div className="flex items-start justify-between gap-2 mb-3">
                          <div className="flex items-center gap-2.5">
                            <div
                              className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs shrink-0 ${
                                isQuarantined
                                  ? 'bg-rose-950 border border-rose-600 text-rose-300 animate-pulse'
                                  : 'bg-indigo-950/80 border border-indigo-700/60 text-indigo-300'
                              }`}
                            >
                              {isQuarantined ? <AlertOctagon className="w-4 h-4" /> : <User className="w-4 h-4" />}
                            </div>
                            <div>
                              <h5 className="text-sm font-bold text-white tracking-tight">
                                {agent.customer_name || 'Retail Client'}
                              </h5>
                              <div className="flex items-center gap-1.5 mt-0.5">
                                <span className="text-[10px] font-mono text-zinc-400">
                                  #{agent.account_id}
                                </span>
                                <span className={`text-[9px] font-mono px-1.5 py-0.2 rounded border font-bold ${badgeClass}`}>
                                  {agent.tier || 'RETAIL'}
                                </span>
                              </div>
                            </div>
                          </div>

                          <span
                            className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded-full border flex items-center gap-1 ${
                              isQuarantined
                                ? 'bg-rose-950 border-rose-600 text-rose-300 animate-pulse'
                                : 'bg-emerald-950 border-emerald-700 text-emerald-300'
                            }`}
                          >
                            <span className={`w-1.5 h-1.5 rounded-full ${isQuarantined ? 'bg-rose-400' : 'bg-emerald-400'}`} />
                            <span>{isQuarantined ? 'QUARANTINED' : 'ACTIVE'}</span>
                          </span>
                        </div>

                        {/* Agent Identifier & Scopes */}
                        <div className="space-y-2 py-2.5 border-y border-zinc-850 font-mono text-xs">
                          <div className="flex items-center justify-between text-zinc-400">
                            <span>Assigned Agent:</span>
                            <span className="font-bold text-white">{agent.agent_id}</span>
                          </div>

                          <div className="flex items-center justify-between text-zinc-400">
                            <span>Behavioral Risk:</span>
                            <span className={`font-bold ${risk > 0.6 ? 'text-rose-400' : 'text-emerald-400'}`}>
                              {risk.toFixed(2)} (Nominal)
                            </span>
                          </div>

                          <div>
                            <span className="text-[10px] text-zinc-500 uppercase block mb-1">Permitted Scopes:</span>
                            <div className="flex flex-wrap gap-1">
                              {agent.allowed_tools?.map((tool, idx) => (
                                <span
                                  key={idx}
                                  className="text-[9px] px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-400"
                                >
                                  {tool}
                                </span>
                              ))}
                            </div>
                          </div>

                          {/* Isolation Guarantee Banner */}
                          <div className="pt-1 text-[10px] text-zinc-400 bg-zinc-900/60 p-2 rounded-lg border border-zinc-800/80">
                            {isQuarantined ? (
                              <span className="text-rose-400 font-sans flex items-center gap-1.5">
                                <ShieldAlert className="w-3.5 h-3.5 shrink-0 text-rose-400" />
                                <span>Access suspended for #{agent.account_id} only. Other accounts unaffected.</span>
                              </span>
                            ) : (
                              <span className="text-zinc-400 font-sans flex items-center gap-1.5">
                                <ShieldCheck className="w-3.5 h-3.5 shrink-0 text-emerald-400" />
                                <span>Isolated assistant. Quarantining only blocks #{agent.account_id}.</span>
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Action Button */}
                      <div className="mt-4 pt-1">
                        {isQuarantined ? (
                          <Tooltip content={`Reinstate ${agent.agent_id} for Account #${agent.account_id}`} position="top" className="w-full">
                            <button
                              type="button"
                              onClick={() => onOpenReinstateModal(agent)}
                              className="w-full py-2 px-3 rounded-xl bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/50 text-xs font-semibold flex items-center justify-center gap-1.5 transition hover-lift"
                            >
                              <Unlock className="w-3.5 h-3.5" />
                              <span>Reinstate (FFIEC Compliant)</span>
                            </button>
                          </Tooltip>
                        ) : (
                          <Tooltip content={`Quarantine ${agent.agent_id} without affecting other users`} position="top" className="w-full">
                            <button
                              type="button"
                              onClick={() => onQuarantine(agent.agent_id)}
                              className="w-full py-2 px-3 rounded-xl bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/50 text-xs font-semibold flex items-center justify-center gap-1.5 transition hover-lift"
                            >
                              <AlertOctagon className="w-3.5 h-3.5" />
                              <span>Quarantine Agent</span>
                            </button>
                          </Tooltip>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Section 2: Institutional Infrastructure Fleet */}
          {(categoryFilter === 'ALL' || categoryFilter === 'INSTITUTIONAL') && (
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Building className="w-4 h-4 text-blue-400" />
                  <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-300 font-mono">
                    Institutional Infrastructure Fleet (High-Value Agents)
                  </h4>
                </div>
                <span className="text-[11px] font-mono text-zinc-500">
                  Bank Treasury & Audit Plane
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {institutionalAgents.map((agent) => {
                  const isQuarantined = agent.status === 'QUARANTINED';
                  const risk = agent.risk_score || 0.1;

                  return (
                    <div
                      key={agent.agent_id}
                      className={`p-5 rounded-2xl border transition-all flex flex-col justify-between ${
                        isQuarantined
                          ? 'bg-rose-950/20 border-rose-800/80 shadow-lg'
                          : 'bg-zinc-950/80 border-zinc-800 hover:border-zinc-750 shadow-md'
                      }`}
                    >
                      <div>
                        <div className="flex items-start justify-between gap-2 mb-3">
                          <div className="flex items-center gap-2.5">
                            <div
                              className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs shrink-0 ${
                                isQuarantined
                                  ? 'bg-rose-950 border border-rose-600 text-rose-300 animate-pulse'
                                  : 'bg-blue-950/80 border border-blue-700/60 text-blue-300'
                              }`}
                            >
                              <Building className="w-4 h-4" />
                            </div>
                            <div>
                              <h5 className="text-sm font-bold text-white tracking-tight">
                                {agent.agent_id}
                              </h5>
                              <p className="text-[10px] text-zinc-400 font-mono mt-0.5">
                                {agent.customer_name} • {agent.role}
                              </p>
                            </div>
                          </div>

                          <span
                            className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded-full border flex items-center gap-1 ${
                              isQuarantined
                                ? 'bg-rose-950 border-rose-600 text-rose-300'
                                : 'bg-emerald-950 border-emerald-700 text-emerald-300'
                            }`}
                          >
                            <span className={`w-1.5 h-1.5 rounded-full ${isQuarantined ? 'bg-rose-400' : 'bg-emerald-400'}`} />
                            <span>{isQuarantined ? 'QUARANTINED' : 'ACTIVE'}</span>
                          </span>
                        </div>

                        <p className="text-xs text-zinc-300 mb-3">{agent.description}</p>

                        <div className="space-y-2 py-2.5 border-y border-zinc-850 font-mono text-xs">
                          <div className="flex items-center justify-between text-zinc-400">
                            <span>Risk Score:</span>
                            <span className={`font-bold ${risk > 0.3 ? 'text-amber-400' : 'text-emerald-400'}`}>
                              {risk.toFixed(2)}
                            </span>
                          </div>
                          <div>
                            <span className="text-[10px] text-zinc-500 uppercase block mb-1">Permitted Tools:</span>
                            <div className="flex flex-wrap gap-1">
                              {agent.allowed_tools?.map((tool, idx) => (
                                <span
                                  key={idx}
                                  className="text-[9px] px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-400"
                                >
                                  {tool}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="mt-4 pt-1">
                        {isQuarantined ? (
                          <Tooltip content={`Reinstate institutional agent ${agent.agent_id}`} position="top" className="w-full">
                            <button
                              type="button"
                              onClick={() => onOpenReinstateModal(agent)}
                              className="w-full py-2 px-3 rounded-xl bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/50 text-xs font-semibold flex items-center justify-center gap-1.5 transition hover-lift"
                            >
                              <Unlock className="w-3.5 h-3.5" />
                              <span>Reinstate (FFIEC)</span>
                            </button>
                          </Tooltip>
                        ) : (
                          <Tooltip content={`Revoke ${agent.agent_id} immediately`} position="top" className="w-full">
                            <button
                              type="button"
                              onClick={() => onQuarantine(agent.agent_id)}
                              className="w-full py-2 px-3 rounded-xl bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/50 text-xs font-semibold flex items-center justify-center gap-1.5 transition hover-lift"
                            >
                              <AlertOctagon className="w-3.5 h-3.5" />
                              <span>Quarantine Agent</span>
                            </button>
                          </Tooltip>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* VIEW MODE 2: FULL AGENTS TABLE */}
      {viewMode === 'table' && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-zinc-300">
            <thead className="bg-zinc-950/80 text-zinc-400 uppercase font-semibold text-[11px] tracking-wider border-b border-zinc-800 font-mono">
              <tr>
                <th className="px-5 py-3.5">Agent Identity & Tenant</th>
                <th className="px-4 py-3.5">Assigned Role</th>
                <th className="px-4 py-3.5">Permitted Scopes</th>
                <th className="px-4 py-3.5">Risk Score</th>
                <th className="px-4 py-3.5">PEP Status</th>
                <th className="px-5 py-3.5 text-right">Governor Control</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60">
              {filteredAgents.map((agent) => {
                const isQuarantined = agent.status === 'QUARANTINED';
                const risk = agent.risk_score || 0.1;
                const isCustomerAgent = agent.fleet_type === 'customer' || agent.agent_id.startsWith('Agent-Support');

                return (
                  <tr
                    key={agent.agent_id}
                    className={`hover:bg-zinc-800/40 transition-colors ${
                      isQuarantined ? 'bg-rose-950/20' : ''
                    }`}
                  >
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs shrink-0 ${
                            isQuarantined
                              ? 'bg-rose-950 border border-rose-600 text-rose-300 animate-pulse'
                              : isCustomerAgent
                              ? 'bg-indigo-950/80 border border-indigo-700/60 text-indigo-300'
                              : 'bg-zinc-950 border border-zinc-700 text-zinc-300'
                          }`}
                        >
                          {isQuarantined ? (
                            <AlertOctagon className="w-4 h-4" />
                          ) : isCustomerAgent ? (
                            <User className="w-4 h-4" />
                          ) : (
                            <Bot className="w-4 h-4" />
                          )}
                        </div>
                        <div>
                          <div className="font-mono font-bold text-white flex items-center gap-2">
                            <span>{agent.agent_id}</span>
                            {isQuarantined ? (
                              <span className="text-[9px] px-1.5 py-0.2 rounded bg-rose-600 text-white font-sans font-bold animate-pulse">
                                REVOKED
                              </span>
                            ) : (
                              <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-950 border border-emerald-800 text-emerald-400 font-mono">
                                ACTIVE
                              </span>
                            )}
                          </div>

                          {isCustomerAgent ? (
                            <div className="flex items-center gap-1.5 mt-1 text-[11px]">
                              <span className="text-zinc-200 font-semibold">
                                {agent.customer_name || 'Customer Virtual Assistant'}
                              </span>
                              <span className="text-zinc-500">•</span>
                              <span className="text-zinc-400 font-mono">#{agent.account_id || '401'}</span>
                              {agent.tier && (
                                <span className={`text-[9px] px-1.5 py-0.2 rounded font-mono font-bold ${
                                  agent.tier === 'PLATINUM'
                                    ? 'bg-purple-950/80 text-purple-300 border border-purple-800'
                                    : agent.tier === 'GOLD'
                                    ? 'bg-amber-950/80 text-amber-300 border border-amber-800'
                                    : 'bg-zinc-800 text-zinc-300 border border-zinc-700'
                                }`}>
                                  {agent.tier}
                                </span>
                              )}
                            </div>
                          ) : (
                            <p className="text-[11px] text-zinc-400 mt-0.5">{agent.description}</p>
                          )}
                        </div>
                      </div>
                    </td>

                    <td className="px-4 py-4">
                      <span className="font-mono text-[11px] px-2.5 py-1 rounded-md bg-zinc-950 border border-zinc-700 text-zinc-300">
                        {agent.role}
                      </span>
                    </td>

                    <td className="px-4 py-4">
                      <div className="flex flex-wrap gap-1 max-w-xs font-mono text-[10px]">
                        {agent.allowed_tools?.map((tool, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-0.5 rounded bg-zinc-950 border border-zinc-800 text-zinc-400"
                          >
                            {tool}
                          </span>
                        ))}
                      </div>
                    </td>

                    <td className="px-4 py-4 font-mono">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-zinc-800 h-2 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${
                              risk > 0.6 ? 'bg-rose-500' : risk > 0.3 ? 'bg-amber-500' : 'bg-emerald-500'
                            }`}
                            style={{ width: `${Math.min(100, risk * 100)}%` }}
                          />
                        </div>
                        <span className={`font-bold ${risk > 0.6 ? 'text-rose-400' : 'text-zinc-200'}`}>
                          {risk.toFixed(2)}
                        </span>
                      </div>
                    </td>

                    <td className="px-4 py-4 font-mono">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold border ${
                          isQuarantined
                            ? 'bg-rose-950/80 border-rose-600/60 text-rose-300 animate-pulse'
                            : 'bg-emerald-950/80 border-emerald-600/40 text-emerald-300'
                        }`}
                      >
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${
                            isQuarantined ? 'bg-rose-400' : 'bg-emerald-400'
                          }`}
                        />
                        <span>{isQuarantined ? 'QUARANTINED' : 'ACTIVE & GOVERNED'}</span>
                      </span>
                    </td>

                    <td className="px-5 py-4 text-right">
                      {isQuarantined ? (
                        <Tooltip content={`Reinstate ${agent.agent_id} per FFIEC compliance review`} position="left">
                          <button
                            type="button"
                            onClick={() => onOpenReinstateModal(agent)}
                            className="px-3 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/50 text-xs font-semibold flex items-center gap-1.5 ml-auto transition hover-lift"
                          >
                            <Unlock className="w-3.5 h-3.5" />
                            <span>Reinstate (FFIEC)</span>
                          </button>
                        </Tooltip>
                      ) : (
                        <Tooltip content={`Instantly revoke ${agent.agent_id} token in Redis (<0.2ms)`} position="left">
                          <button
                            type="button"
                            onClick={() => onQuarantine(agent.agent_id)}
                            className="px-3 py-1.5 rounded-lg bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/50 text-xs font-semibold flex items-center gap-1.5 ml-auto transition hover-lift"
                          >
                            <AlertOctagon className="w-3.5 h-3.5" />
                            <span>Emergency Kill</span>
                          </button>
                        </Tooltip>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
