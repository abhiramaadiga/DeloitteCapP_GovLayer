import React, { useState } from 'react';
import { AlertOctagon, Unlock, Search, Bot } from 'lucide-react';

export default function AgentFleetTable({ agents, onQuarantine, onOpenReinstateModal }) {
  const [searchFilter, setSearchFilter] = useState('');

  const filteredAgents = agents.filter(
    (a) =>
      a.agent_id.toLowerCase().includes(searchFilter.toLowerCase()) ||
      a.role.toLowerCase().includes(searchFilter.toLowerCase()) ||
      a.description.toLowerCase().includes(searchFilter.toLowerCase())
  );

  return (
    <div className="bg-slate-900/90 rounded-2xl border border-slate-800 shadow-xl overflow-hidden">
      {/* Table Header Controls */}
      <div className="p-4 sm:p-5 border-b border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
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
          <p className="text-xs text-slate-400 mt-0.5">
            Cryptographic Passport Status & Real-Time PEP Revocation Controls
          </p>
        </div>

        {/* Search filter */}
        <div className="relative w-full sm:w-64">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            placeholder="Filter agents by role or ID..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 transition"
          />
        </div>
      </div>

      {/* Agents Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-950/80 text-slate-400 uppercase font-semibold text-[11px] tracking-wider border-b border-slate-800">
            <tr>
              <th className="px-5 py-3.5">Agent Identity</th>
              <th className="px-4 py-3.5">Assigned Role</th>
              <th className="px-4 py-3.5">Permitted Tool Scopes</th>
              <th className="px-4 py-3.5">Risk Score</th>
              <th className="px-4 py-3.5">PEP Status</th>
              <th className="px-5 py-3.5 text-right">Governor Control</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {filteredAgents.map((agent) => {
              const isQuarantined = agent.status === 'QUARANTINED';
              const risk = agent.risk_score || 0.1;

              return (
                <tr
                  key={agent.agent_id}
                  className={`hover:bg-slate-800/40 transition-colors ${
                    isQuarantined ? 'bg-rose-950/20' : ''
                  }`}
                >
                  {/* Agent Identity */}
                  <td className="px-5 py-4">
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-8 h-8 rounded-xl flex items-center justify-center font-bold text-xs ${
                          isQuarantined
                            ? 'bg-rose-950 border border-rose-600 text-rose-300 animate-pulse'
                            : 'bg-indigo-950 border border-indigo-700 text-indigo-300'
                        }`}
                      >
                        {isQuarantined ? <AlertOctagon className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                      </div>
                      <div>
                        <div className="font-mono font-bold text-white flex items-center gap-2">
                          {agent.agent_id}
                          {isQuarantined && (
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-rose-500 text-white font-sans font-bold">
                              KILLED
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-400">{agent.description}</p>
                      </div>
                    </div>
                  </td>

                  {/* Role Badge */}
                  <td className="px-4 py-4">
                    <span className="font-mono text-[11px] px-2.5 py-1 rounded-md bg-slate-950 border border-slate-700 text-slate-300">
                      {agent.role}
                    </span>
                  </td>

                  {/* Permitted Tool Scopes */}
                  <td className="px-4 py-4 max-w-xs">
                    <div className="flex flex-wrap gap-1">
                      {agent.allowed_tools?.map((tool, idx) => (
                        <span
                          key={idx}
                          className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-950/80 border border-slate-800 text-slate-400"
                        >
                          {tool}
                        </span>
                      ))}
                    </div>
                  </td>

                  {/* Risk Score */}
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-2">
                      <div className="w-16 bg-slate-800 rounded-full h-2 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            risk >= 0.7 ? 'bg-rose-500' : risk >= 0.4 ? 'bg-amber-500' : 'bg-emerald-500'
                          }`}
                          style={{ width: `${Math.round(risk * 100)}%` }}
                        />
                      </div>
                      <span
                        className={`font-mono text-xs font-bold ${
                          risk >= 0.7 ? 'text-rose-400' : risk >= 0.4 ? 'text-amber-400' : 'text-emerald-400'
                        }`}
                      >
                        {risk.toFixed(2)}
                      </span>
                    </div>
                  </td>

                  {/* PEP Status Badge */}
                  <td className="px-4 py-4">
                    {isQuarantined ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-rose-950/80 border border-rose-500/60 text-rose-300 animate-pulse">
                        <span className="w-2 h-2 rounded-full bg-rose-400" />
                        QUARANTINED
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-950/80 border border-emerald-500/40 text-emerald-300">
                        <span className="w-2 h-2 rounded-full bg-emerald-400" />
                        GOVERNED • ACTIVE
                      </span>
                    )}
                  </td>

                  {/* Actions */}
                  <td className="px-5 py-4 text-right">
                    {isQuarantined ? (
                      <button
                        onClick={() => onOpenReinstateModal(agent)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md shadow-emerald-900/30 transition transform hover:scale-105"
                      >
                        <Unlock className="w-3.5 h-3.5" />
                        <span>Reinstate</span>
                      </button>
                    ) : (
                      <button
                        onClick={() => onQuarantine(agent.agent_id)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-950/80 hover:bg-rose-700 border border-rose-600/50 hover:border-rose-500 text-rose-200 hover:text-white font-bold text-xs shadow-md shadow-rose-950/40 transition transform hover:scale-105"
                      >
                        <AlertOctagon className="w-3.5 h-3.5" />
                        <span>Kill-Switch</span>
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
