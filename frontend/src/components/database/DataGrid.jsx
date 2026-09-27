import React from 'react';
import { ArrowUp, ArrowDown, FileX } from 'lucide-react';

/**
 * Format and inspect cell values for DataGrid.
 * Handles NULLs, booleans, numbers, dates, objects, and strings with tooltip support.
 */
function renderCellValue(val) {
  if (val === null || val === undefined) {
    return {
      isNumeric: false,
      rawText: 'NULL',
      element: <span className="italic text-zinc-600 font-normal">NULL</span>,
    };
  }

  if (typeof val === 'boolean') {
    const text = val ? 'true' : 'false';
    return {
      isNumeric: false,
      rawText: text,
      element: (
        <span className="inline-flex items-center gap-1.5">
          <span
            className={`inline-block w-1.5 h-1.5 rounded-full shrink-0 ${
              val ? 'bg-emerald-400' : 'bg-rose-400'
            }`}
          />
          <span className={val ? 'text-emerald-400' : 'text-rose-400 font-medium'}>
            {text}
          </span>
        </span>
      ),
    };
  }

  if (typeof val === 'number' || typeof val === 'bigint') {
    const text = String(val);
    return {
      isNumeric: true,
      rawText: text,
      element: <span>{text}</span>,
    };
  }

  if (typeof val === 'string') {
    const trimmed = val.trim();
    const isNum =
      trimmed !== '' &&
      !isNaN(Number(trimmed)) &&
      /^-?\d+(\.\d+)?$/.test(trimmed);

    return {
      isNumeric: isNum,
      rawText: val,
      element: <span>{val}</span>,
    };
  }

  if (val instanceof Date) {
    const text = val.toISOString();
    return {
      isNumeric: false,
      rawText: text,
      element: <span>{text}</span>,
    };
  }

  if (typeof val === 'object') {
    const text = JSON.stringify(val);
    return {
      isNumeric: false,
      rawText: text,
      element: <span>{text}</span>,
    };
  }

  const text = String(val);
  return {
    isNumeric: false,
    rawText: text,
    element: <span>{text}</span>,
  };
}

export default function DataGrid({
  columns = [],
  rows = [],
  sortColumn = '',
  sortDir = 'asc',
  onSort,
  loading = false,
}) {
  const colCount = columns && columns.length > 0 ? columns.length : 6;

  return (
    <div className="overflow-x-auto overflow-y-auto max-h-[calc(100vh-340px)] border border-zinc-800 bg-zinc-950/40 rounded-lg relative select-text">
      <table className="w-full text-xs font-mono border-collapse">
        <thead className="sticky top-0 bg-zinc-900 border-b border-zinc-700 z-10">
          <tr>
            {columns.map((col) => {
              const isSorted = sortColumn === col;
              return (
                <th
                  key={col}
                  onClick={() => onSort && onSort(col)}
                  className={`px-3 py-2.5 text-left font-semibold uppercase tracking-wider text-[11px] cursor-pointer hover:text-zinc-200 transition-colors select-none ${
                    isSorted ? 'text-zinc-200' : 'text-zinc-400'
                  }`}
                  title={`Sort by ${col}`}
                >
                  <div className="inline-flex items-center gap-1.5">
                    <span>{col}</span>
                    {isSorted && (
                      sortDir === 'desc' ? (
                        <ArrowDown className="w-3 h-3 text-indigo-400 shrink-0" />
                      ) : (
                        <ArrowUp className="w-3 h-3 text-indigo-400 shrink-0" />
                      )
                    )}
                  </div>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {loading ? (
            Array.from({ length: 8 }).map((_, rowIndex) => (
              <tr
                key={`skeleton-${rowIndex}`}
                className="border-b border-zinc-800/50 even:bg-zinc-900/30 odd:bg-transparent"
              >
                {Array.from({ length: colCount }).map((_, colIndex) => (
                  <td key={`skeleton-cell-${colIndex}`} className="px-3 py-2.5">
                    <div className="bg-zinc-800/40 h-4 rounded animate-pulse" />
                  </td>
                ))}
              </tr>
            ))
          ) : rows && rows.length > 0 ? (
            rows.map((row, rowIndex) => {
              const rowKey = row?.id ?? row?._id ?? row?.uuid ?? rowIndex;
              return (
                <tr
                  key={rowKey}
                  className="hover:bg-zinc-800/60 transition-colors border-b border-zinc-800/50 even:bg-zinc-900/30 odd:bg-transparent"
                >
                  {columns.map((col) => {
                    const cellValue = row ? row[col] : undefined;
                    const cell = renderCellValue(cellValue);
                    const showTooltip =
                      Boolean(cell.rawText) && cell.rawText.length > 60;

                    return (
                      <td
                        key={col}
                        title={showTooltip ? cell.rawText : undefined}
                        className={`px-3 py-2 text-zinc-300 whitespace-nowrap max-w-[280px] truncate ${
                          cell.isNumeric ? 'text-right' : 'text-left'
                        }`}
                      >
                        {cell.element}
                      </td>
                    );
                  })}
                </tr>
              );
            })
          ) : (
            <tr>
              <td
                colSpan={Math.max(colCount, 1)}
                className="py-16 text-center"
              >
                <div className="flex flex-col items-center justify-center text-zinc-500 gap-2">
                  <FileX className="w-8 h-8 text-zinc-600 stroke-[1.5]" />
                  <span className="text-sm font-sans text-zinc-400 font-normal">
                    No records found
                  </span>
                </div>
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
