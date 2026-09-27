import React from 'react';
import {
  ChevronsLeft,
  ChevronLeft,
  ChevronRight,
  ChevronsRight,
} from 'lucide-react';

export default function PaginationBar({
  page = 1,
  totalPages = 1,
  totalRows = 0,
  pageSize = 10,
  onPageChange,
  onPageSizeChange,
}) {
  const currentPage = Math.max(1, Number(page) || 1);
  const total = Math.max(0, Number(totalRows) || 0);
  const size = Math.max(1, Number(pageSize) || 10);
  const pages = Math.max(1, Number(totalPages) || 1);

  const start = total === 0 ? 0 : (currentPage - 1) * size + 1;
  const end = total === 0 ? 0 : Math.min(currentPage * size, total);

  const isFirstDisabled = currentPage <= 1;
  const isLastDisabled = currentPage >= pages;

  return (
    <div className="flex items-center justify-between px-4 py-3 border-t border-zinc-800 bg-zinc-900/60 select-none">
      {/* Left side: Range & count display */}
      <div className="text-xs text-zinc-500">
        Showing {start}-{end} of {total} rows
      </div>

      {/* Center: Navigation controls */}
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => onPageChange && onPageChange(1)}
          disabled={isFirstDisabled}
          title="First page"
          className="p-1.5 rounded hover:bg-zinc-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-zinc-400 hover:text-zinc-200 disabled:hover:bg-transparent disabled:hover:text-zinc-400"
        >
          <ChevronsLeft className="w-4 h-4" />
        </button>

        <button
          type="button"
          onClick={() => onPageChange && onPageChange(currentPage - 1)}
          disabled={isFirstDisabled}
          title="Previous page"
          className="p-1.5 rounded hover:bg-zinc-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-zinc-400 hover:text-zinc-200 disabled:hover:bg-transparent disabled:hover:text-zinc-400"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        <span className="px-2 text-xs font-mono text-zinc-400">
          {currentPage} / {pages}
        </span>

        <button
          type="button"
          onClick={() => onPageChange && onPageChange(currentPage + 1)}
          disabled={isLastDisabled}
          title="Next page"
          className="p-1.5 rounded hover:bg-zinc-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-zinc-400 hover:text-zinc-200 disabled:hover:bg-transparent disabled:hover:text-zinc-400"
        >
          <ChevronRight className="w-4 h-4" />
        </button>

        <button
          type="button"
          onClick={() => onPageChange && onPageChange(pages)}
          disabled={isLastDisabled}
          title="Last page"
          className="p-1.5 rounded hover:bg-zinc-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-zinc-400 hover:text-zinc-200 disabled:hover:bg-transparent disabled:hover:text-zinc-400"
        >
          <ChevronsRight className="w-4 h-4" />
        </button>
      </div>

      {/* Right side: Rows per page selector */}
      <div className="flex items-center gap-2">
        <label htmlFor="rows-per-page-select" className="text-zinc-500 text-xs">
          Rows:
        </label>
        <select
          id="rows-per-page-select"
          value={size}
          onChange={(e) =>
            onPageSizeChange && onPageSizeChange(Number(e.target.value))
          }
          className="bg-zinc-800 border border-zinc-700 rounded text-xs text-zinc-300 px-2 py-1 focus:border-indigo-500 focus:outline-none cursor-pointer"
        >
          <option value={10}>10</option>
          <option value={25}>25</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
        </select>
      </div>
    </div>
  );
}
