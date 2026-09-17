import React from 'react';
import { Search, RefreshCw, X, Filter } from 'lucide-react';

const PRESET_QUERIES = {
  conversations: [
    { label: 'All Chats', query: '' },
    { label: 'Blocked Threats (PEP)', query: 'BLOCKED' },
    { label: 'Flagged for RLHF', query: 'true' },
    { label: 'Account #401', query: '401' },
    { label: 'Prompt Injections', query: 'dump' },
    { label: 'Balance Queries', query: 'balance' },
  ],
  banking_accounts: [
    { label: 'All Accounts', query: '' },
    { label: 'Gold Tier', query: 'GOLD' },
    { label: 'Platinum Tier', query: 'PLATINUM' },
    { label: 'Silver Tier', query: 'SILVER' },
  ],
  banking_transactions: [
    { label: 'All Ledger', query: '' },
    { label: 'Debits (Transfers)', query: 'debit' },
    { label: 'Credits (Deposits)', query: 'credit' },
    { label: 'Settled', query: 'Settled' },
    { label: 'Account #401', query: '401' },
  ],
  audit_logs: [
    { label: 'All Audits', query: '' },
    { label: 'Blocked / High Risk', query: 'BLOCKED' },
    { label: 'Quarantined', query: 'QUARANTINED' },
    { label: 'Support Agent', query: 'Agent-Support-01' },
    { label: 'Treasury Agent', query: 'Agent-Treasury-01' },
  ],
  users: [
    { label: 'All Users', query: '' },
    { label: 'Admin Profiles', query: 'admin' },
    { label: 'Customer Accounts', query: 'customer' },
    { label: 'Rahul Sharma (#401)', query: 'rahul' },
    { label: 'Priya Patel (#402)', query: 'priya' },
    { label: 'Vikram Malhotra (#403)', query: 'vikram' },
  ],
  fixed_deposits: [
    { label: 'All Fixed Deposits', query: '' },
    { label: 'Locked / Active', query: 'LOCKED' },
    { label: 'Liquidated', query: 'LIQUIDATED' },
    { label: 'Account #401', query: '401' },
    { label: 'Account #402', query: '402' },
    { label: 'Account #403', query: '403' },
  ],
  governance_policies: [
    { label: 'All Policies', query: '' },
    { label: 'SOX-404 Rules', query: 'SOX-404' },
    { label: 'PCI-DSS Rules', query: 'PCI-DSS' },
    { label: 'Active Policies', query: 'true' },
    { label: 'Deny Policies', query: 'DENY' },
    { label: 'Allow Policies', query: 'ALLOW' },
  ],
};

export default function SearchFilter({
  searchTerm = '',
  onSearchChange,
  onRefresh,
  refreshing = false,
  dbType = 'postgresql',
  selectedTable = 'conversations',
}) {
  const isPostgres = (dbType || '').toLowerCase() === 'postgresql';
  const presets = PRESET_QUERIES[selectedTable] || [];

  return (
    <div className="border-b border-zinc-800 bg-zinc-950/60 select-none">
      {/* Search and Status Toolbar */}
      <div className="flex flex-wrap items-center gap-3 px-4 py-3">
        {/* Search input */}
        <div className="relative flex items-center">
          <Search className="w-3.5 h-3.5 absolute left-3 text-zinc-500 pointer-events-none" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => onSearchChange && onSearchChange(e.target.value)}
            placeholder="Search across all columns..."
            className="w-64 sm:w-80 pl-9 pr-8 py-1.5 bg-zinc-900 border border-zinc-700 rounded-lg text-zinc-200 placeholder-zinc-500 font-mono text-xs focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 transition-colors"
          />
          {searchTerm && (
            <button
              type="button"
              onClick={() => onSearchChange && onSearchChange('')}
              className="absolute right-2.5 p-0.5 text-zinc-500 hover:text-zinc-300 rounded transition-colors"
              title="Clear search"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Refresh button */}
        <button
          type="button"
          onClick={onRefresh}
          disabled={refreshing}
          title={refreshing ? 'Refreshing...' : 'Refresh table data'}
          className="p-2 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors border border-transparent hover:border-zinc-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5 text-xs font-mono"
        >
          <RefreshCw
            className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-indigo-400' : ''}`}
          />
          <span className="hidden sm:inline">Refresh</span>
        </button>

        {/* DB Type Badge */}
        <div className="ml-auto flex items-center">
          <div
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-900 border border-zinc-800 font-mono text-xs ${
              isPostgres ? 'text-emerald-400' : 'text-amber-400'
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isPostgres ? 'bg-emerald-400' : 'bg-amber-400'
              }`}
            />
            <span className="font-semibold">
              {isPostgres ? 'PostgreSQL 16' : 'SQLite'}
            </span>
          </div>
        </div>
      </div>

      {/* Dynamic Preset Query Chips */}
      {presets.length > 0 && (
        <div className="flex items-center gap-2 px-4 py-2 border-t border-zinc-850 bg-zinc-900/40 overflow-x-auto">
          <div className="flex items-center gap-1 text-[11px] font-mono text-zinc-400 shrink-0 mr-1">
            <Filter className="w-3 h-3 text-indigo-400" />
            <span>Preset Queries:</span>
          </div>
          <div className="flex items-center gap-1.5 overflow-x-auto py-0.5">
            {presets.map((p, idx) => {
              const isActive = (p.query === '' && !searchTerm) || (p.query !== '' && searchTerm.toLowerCase() === p.query.toLowerCase());
              return (
                <button
                  key={idx}
                  type="button"
                  onClick={() => onSearchChange && onSearchChange(p.query)}
                  className={`text-[11px] font-mono whitespace-nowrap px-2.5 py-1 rounded-md border transition hover-lift shrink-0 ${
                    isActive
                      ? 'bg-indigo-950/80 border-indigo-500/80 text-indigo-300 font-semibold shadow-sm'
                      : 'bg-zinc-900/80 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 border-zinc-800'
                  }`}
                >
                  {p.label}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
