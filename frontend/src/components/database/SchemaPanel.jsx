import React from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

export default function SchemaPanel({
  schema = null,
  isOpen = false,
  onToggle,
}) {
  const columns = schema?.columns || [];
  const columnCount = columns.length;

  return (
    <div className="bg-zinc-900/80 border-b border-zinc-800 px-4 py-2 select-none">
      {/* Toggle Button */}
      <button
        type="button"
        onClick={onToggle}
        className="flex items-center gap-2 text-xs font-medium text-zinc-300 hover:text-zinc-100 transition-colors py-0.5 group focus:outline-none"
      >
        {isOpen ? (
          <ChevronUp className="w-4 h-4 text-zinc-400 group-hover:text-zinc-200 transition-colors" />
        ) : (
          <ChevronDown className="w-4 h-4 text-zinc-400 group-hover:text-zinc-200 transition-colors" />
        )}
        <span className="font-sans">
          Schema ({columnCount} {columnCount === 1 ? 'column' : 'columns'})
        </span>
        {schema?.table && (
          <span className="text-zinc-500 font-mono text-[11px]">
            &bull; {schema.table}
          </span>
        )}
      </button>

      {/* Expanded Column Badges Strip */}
      {isOpen && (
        <div className="mt-2 pt-2 border-t border-zinc-800/60 flex items-center gap-2 overflow-x-auto pb-1.5 animate-slide-up">
          {columns.length === 0 ? (
            <span className="text-xs text-zinc-500 font-sans italic py-1">
              No column definitions available
            </span>
          ) : (
            columns.map((col) => {
              const isPk = Boolean(col.primary_key);
              const isNullable = Boolean(col.nullable);

              return (
                <div
                  key={col.name}
                  className={`flex flex-col shrink-0 px-2.5 py-1.5 rounded-lg bg-zinc-950 border text-left min-w-[120px] ${
                    isPk ? 'border-emerald-800/60 ring-1 ring-emerald-500/20' : 'border-zinc-800'
                  }`}
                >
                  {/* Column Header: Dot, Name, PK, NULL */}
                  <div className="flex items-center gap-1.5">
                    {isPk && (
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
                    )}
                    <span className="font-mono text-xs text-zinc-200 font-medium truncate max-w-[130px]" title={col.name}>
                      {col.name}
                    </span>
                    {isPk && (
                      <span className="px-1 py-0.5 text-[9px] font-mono font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800/60 rounded leading-none">
                        PK
                      </span>
                    )}
                    {isNullable && (
                      <span className="text-[10px] font-mono font-semibold text-amber-400 leading-none ml-auto">
                        NULL
                      </span>
                    )}
                  </div>

                  {/* Column Type label beneath */}
                  <div className="mt-1 flex items-center justify-between gap-2">
                    <span className="font-mono text-[11px] text-zinc-500 lowercase truncate max-w-[120px]" title={col.type}>
                      {col.type || 'text'}
                    </span>
                    {col.default !== null && col.default !== undefined && (
                      <span
                        className="text-[10px] font-mono text-zinc-600 truncate max-w-[70px]"
                        title={`Default: ${col.default}`}
                      >
                        ={String(col.default)}
                      </span>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
