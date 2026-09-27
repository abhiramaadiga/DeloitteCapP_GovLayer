import React from 'react';
import { Database, Table2 } from 'lucide-react';

export default function TableSidebar({
  tables = [],
  selectedTable = '',
  onSelectTable,
  loading = false,
}) {
  return (
    <aside className="w-56 border-r border-zinc-800 bg-zinc-900/60 h-full flex flex-col shrink-0 overflow-y-auto select-none">
      {/* Header */}
      <div className="px-3.5 py-3 border-b border-zinc-800 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-indigo-400" />
          <span className="font-semibold text-xs tracking-wider uppercase text-zinc-300 font-sans">
            Tables
          </span>
        </div>
        <div className="flex items-center gap-1.5" title="Connected to PostgreSQL 16">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-[11px] font-mono text-emerald-400 font-medium">
            PostgreSQL 16
          </span>
        </div>
      </div>

      {/* Tables List */}
      <div className="flex-1 overflow-y-auto py-1">
        {loading ? (
          <div className="p-2 space-y-1.5 animate-pulse">
            {[...Array(6)].map((_, idx) => (
              <div
                key={idx}
                className="h-8 rounded-md bg-zinc-800/40 w-full flex items-center justify-between px-2.5"
              >
                <div className="flex items-center gap-2 flex-1">
                  <div className="w-3.5 h-3.5 rounded bg-zinc-700/60 shrink-0" />
                  <div className="h-3 bg-zinc-700/60 rounded w-20" />
                </div>
                <div className="w-6 h-4 rounded bg-zinc-700/60" />
              </div>
            ))}
          </div>
        ) : tables.length === 0 ? (
          <div className="p-4 text-center text-xs text-zinc-500 font-sans">
            No tables found
          </div>
        ) : (
          <ul className="space-y-0.5">
            {tables.map((table) => {
              const isSelected = selectedTable === table.name;
              return (
                <li key={table.name}>
                  <button
                    type="button"
                    onClick={() => onSelectTable && onSelectTable(table.name)}
                    className={`w-full flex items-center justify-between px-3 py-2 text-left text-xs transition-colors group ${
                      isSelected
                        ? 'bg-indigo-950/50 border-l-2 border-indigo-500 text-indigo-200'
                        : 'border-l-2 border-transparent text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0 pr-2">
                      <Table2
                        className={`w-3.5 h-3.5 shrink-0 ${
                          isSelected
                            ? 'text-indigo-400'
                            : 'text-zinc-500 group-hover:text-zinc-400'
                        }`}
                      />
                      <span
                        className="font-mono text-sm truncate"
                        title={table.name}
                      >
                        {table.name}
                      </span>
                    </div>
                    <span className="px-1.5 py-0.5 rounded bg-zinc-700 text-zinc-300 text-xs font-mono shrink-0">
                      {typeof table.row_count === 'number'
                        ? table.row_count.toLocaleString()
                        : (table.row_count ?? 0)}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </aside>
  );
}
