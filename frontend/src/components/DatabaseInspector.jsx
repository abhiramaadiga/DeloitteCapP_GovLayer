import React, { useState, useEffect, useCallback } from 'react';
import { Database, AlertTriangle } from 'lucide-react';
import { getDbTables, getTableSchema, getTableRows } from '../services/api';
import TableSidebar from './database/TableSidebar';
import SchemaPanel from './database/SchemaPanel';
import DataGrid from './database/DataGrid';
import PaginationBar from './database/PaginationBar';
import SearchFilter from './database/SearchFilter';

export default function DatabaseInspector({ isBackendOnline }) {
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState(null);
  const [schema, setSchema] = useState(null);
  const [schemaOpen, setSchemaOpen] = useState(true);
  const [rows, setRows] = useState([]);
  const [columns, setColumns] = useState([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [totalRows, setTotalRows] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [sortColumn, setSortColumn] = useState(null);
  const [sortDir, setSortDir] = useState('desc');
  const [searchTerm, setSearchTerm] = useState('');
  const [tablesLoading, setTablesLoading] = useState(true);
  const [dataLoading, setDataLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load table list on mount
  useEffect(() => {
    let mounted = true;
    const loadTables = async () => {
      setTablesLoading(true);
      try {
        const list = await getDbTables();
        if (mounted) {
          setTables(list);
          if (list.length > 0) {
            setSelectedTable((prev) => prev || list[0].name);
          }
        }
      } catch (err) {
        if (mounted) setError(err.message);
      } finally {
        if (mounted) setTablesLoading(false);
      }
    };
    loadTables();
    return () => { mounted = false; };
  }, []);

  // Load schema when table changes
  useEffect(() => {
    if (!selectedTable) return;
    let mounted = true;
    const loadSchema = async () => {
      try {
        const s = await getTableSchema(selectedTable);
        if (mounted) setSchema(s);
      } catch {
        if (mounted) setSchema(null);
      }
    };
    loadSchema();
    return () => { mounted = false; };
  }, [selectedTable]);

  // Load rows when table, page, sort, or search changes
  const loadRows = useCallback(async () => {
    if (!selectedTable) return;
    setDataLoading(true);
    setError(null);
    try {
      const result = await getTableRows(
        selectedTable,
        page,
        pageSize,
        sortColumn,
        sortDir,
        searchTerm || null
      );
      setRows(result.rows || []);
      setColumns(result.columns || []);
      setTotalRows(result.total_rows || 0);
      setTotalPages(result.total_pages || 1);
    } catch (err) {
      setError(err.message);
      setRows([]);
    } finally {
      setDataLoading(false);
    }
  }, [selectedTable, page, pageSize, sortColumn, sortDir, searchTerm]);

  useEffect(() => {
    if (selectedTable) {
      loadRows();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTable, page, pageSize, sortColumn, sortDir, searchTerm]);

  // Reset pagination when table or search changes
  const handleSelectTable = (tableName) => {
    setSelectedTable(tableName);
    setPage(1);
    setSortColumn(null);
    setSortDir('desc');
    setSearchTerm('');
  };

  const handleSort = (colName) => {
    if (sortColumn === colName) {
      setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(colName);
      setSortDir('asc');
    }
    setPage(1);
  };

  const handleSearchChange = (term) => {
    setSearchTerm(term);
    setPage(1);
  };

  const handlePageSizeChange = (newSize) => {
    setPageSize(newSize);
    setPage(1);
  };

  const dbType = isBackendOnline ? 'postgresql' : 'sqlite';

  return (
    <div className="flex h-[740px] max-h-[calc(100vh-180px)] min-h-[520px] bg-zinc-900/90 border border-zinc-800/90 rounded-2xl overflow-hidden shadow-2xl animate-page-enter">
      {/* Left Sidebar: Table List */}
      <TableSidebar
        tables={tables}
        selectedTable={selectedTable}
        onSelectTable={handleSelectTable}
        loading={tablesLoading}
      />

      {/* Right Content: Schema + Grid + Pagination */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header Bar */}
        <div className="flex items-center gap-3 px-5 py-3 border-b border-zinc-800 bg-zinc-950">
          <Database className="w-4 h-4 text-indigo-400" />
          <h2 className="text-sm font-semibold text-zinc-200 tracking-wide">
            {selectedTable ? (
              <>
                <span className="text-zinc-500">governance_db</span>
                <span className="text-zinc-600 mx-1.5">/</span>
                <span className="font-mono text-indigo-300">{selectedTable}</span>
              </>
            ) : (
              'Database Inspector'
            )}
          </h2>
          {schema && (
            <span className="text-[11px] font-mono text-zinc-500 ml-auto">
              {schema.row_count?.toLocaleString()} rows  ·  {schema.columns?.length} columns
            </span>
          )}
        </div>

        {/* Search & Filter Toolbar */}
        <SearchFilter
          searchTerm={searchTerm}
          onSearchChange={handleSearchChange}
          onRefresh={loadRows}
          refreshing={dataLoading}
          dbType={dbType}
          selectedTable={selectedTable}
        />

        {/* Collapsible Schema Panel */}
        {schema && (
          <SchemaPanel
            schema={schema}
            isOpen={schemaOpen}
            onToggle={() => setSchemaOpen((prev) => !prev)}
          />
        )}

        {/* Error Banner */}
        {error && (
          <div className="flex items-center gap-2 px-4 py-2 bg-rose-950/50 border-b border-rose-800/50 text-rose-300 text-xs">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Data Grid */}
        <div className="flex-1 overflow-hidden">
          <DataGrid
            columns={columns}
            rows={rows}
            sortColumn={sortColumn}
            sortDir={sortDir}
            onSort={handleSort}
            loading={dataLoading}
          />
        </div>

        {/* Pagination */}
        <PaginationBar
          page={page}
          totalPages={totalPages}
          totalRows={totalRows}
          pageSize={pageSize}
          onPageChange={setPage}
          onPageSizeChange={handlePageSizeChange}
        />
      </div>
    </div>
  );
}
