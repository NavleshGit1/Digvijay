import React, { useMemo, useState } from "react";
import { ChevronDown, ChevronUp, ChevronsUpDown, Search } from "lucide-react";
import { Button } from "../ui/Button";
import { EmptyState } from "../feedback/EmptyState";
import { ErrorState } from "../feedback/ErrorState";

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => React.ReactNode;
  sortable?: boolean;
  align?: "left" | "center" | "right";
  width?: string;
}

export interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  keyField: keyof T | ((row: T) => string);
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  emptyTitle?: string;
  emptyMessage?: string;
  searchPlaceholder?: string;
  searchFilter?: (row: T, query: string) => boolean;
  pageSize?: number;
  filters?: React.ReactNode;
  actions?: React.ReactNode;
  onRowClick?: (row: T) => void;
}

export function DataTable<T extends Record<string, any>>({
  data,
  columns,
  keyField,
  loading = false,
  error = null,
  onRetry,
  emptyTitle = "No records found",
  emptyMessage = "No items match your active filters or search criteria.",
  searchPlaceholder = "Search records...",
  searchFilter,
  pageSize = 15,
  filters,
  actions,
  onRowClick,
}: DataTableProps<T>) {
  const [searchQuery, setSearchQuery] = useState("");
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(pageSize);

  // Filter rows
  const filteredData = useMemo(() => {
    if (!searchQuery.trim()) return data;
    const query = searchQuery.toLowerCase().trim();

    if (searchFilter) {
      return data.filter((row) => searchFilter(row, query));
    }

    // Default search across string and number fields
    return data.filter((row) => {
      return Object.values(row).some((val) => {
        if (val === null || val === undefined) return false;
        if (typeof val === "string" || typeof val === "number") {
          return String(val).toLowerCase().includes(query);
        }
        return false;
      });
    });
  }, [data, searchQuery, searchFilter]);

  // Sort rows
  const sortedData = useMemo(() => {
    if (!sortKey) return filteredData;
    return [...filteredData].sort((a, b) => {
      const valA = a[sortKey];
      const valB = b[sortKey];

      if (valA === valB) return 0;
      if (valA === null || valA === undefined) return 1;
      if (valB === null || valB === undefined) return -1;

      if (typeof valA === "number" && typeof valB === "number") {
        return sortDirection === "asc" ? valA - valB : valB - valA;
      }

      const strA = String(valA).toLowerCase();
      const strB = String(valB).toLowerCase();
      return sortDirection === "asc" ? strA.localeCompare(strB) : strB.localeCompare(strA);
    });
  }, [filteredData, sortKey, sortDirection]);

  // Paginate rows
  const totalRows = sortedData.length;
  const totalPages = Math.max(1, Math.ceil(totalRows / rowsPerPage));
  const validPage = Math.min(currentPage, totalPages);

  const paginatedData = useMemo(() => {
    const startIdx = (validPage - 1) * rowsPerPage;
    return sortedData.slice(startIdx, startIdx + rowsPerPage);
  }, [sortedData, validPage, rowsPerPage]);

  const handleSort = (columnKey: string, isSortable?: boolean) => {
    if (!isSortable) return;
    if (sortKey === columnKey) {
      if (sortDirection === "asc") {
        setSortDirection("desc");
      } else {
        setSortKey(null);
        setSortDirection("asc");
      }
    } else {
      setSortKey(columnKey);
      setSortDirection("asc");
    }
  };

  const getRowKey = (row: T, index: number): string => {
    if (typeof keyField === "function") {
      return keyField(row);
    }
    return String(row[keyField] ?? index);
  };

  if (error) {
    return (
      <div className="p-4">
        <ErrorState title="Failed to load table data" detail={error} onRetry={onRetry} />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Top Filter & Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-1 max-w-md relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            placeholder={searchPlaceholder}
            className="w-full pl-9 pr-3 py-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
          />
          {searchQuery && (
            <button
              onClick={() => {
                setSearchQuery("");
                setCurrentPage(1);
              }}
              className="text-xs text-slate-400 hover:text-slate-600 px-1.5 py-0.5 rounded"
            >
              Clear
            </button>
          )}
        </div>

        <div className="flex items-center gap-2 flex-wrap justify-end">
          {filters}
          {actions}
        </div>
      </div>

      {/* Table Container */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-600">
            <thead className="bg-slate-50/90 text-[11px] uppercase tracking-wider font-semibold text-slate-500 border-b border-slate-200">
              <tr>
                {columns.map((col) => {
                  const isSorted = sortKey === col.key;
                  return (
                    <th
                      key={col.key}
                      style={{ width: col.width }}
                      onClick={() => handleSort(col.key, col.sortable)}
                      className={`px-4 py-3 select-none ${
                        col.sortable ? "cursor-pointer hover:bg-slate-100/70" : ""
                      } ${
                        col.align === "right"
                          ? "text-right"
                          : col.align === "center"
                          ? "text-center"
                          : "text-left"
                      }`}
                    >
                      <div
                        className={`inline-flex items-center gap-1.5 ${
                          col.align === "right"
                            ? "justify-end"
                            : col.align === "center"
                            ? "justify-center"
                            : "justify-start"
                        }`}
                      >
                        <span>{col.header}</span>
                        {col.sortable && (
                          <span className="text-slate-400">
                            {isSorted ? (
                              sortDirection === "asc" ? (
                                <ChevronUp className="w-3.5 h-3.5 text-blue-600" />
                              ) : (
                                <ChevronDown className="w-3.5 h-3.5 text-blue-600" />
                              )
                            ) : (
                              <ChevronsUpDown className="w-3.5 h-3.5 opacity-40 hover:opacity-100" />
                            )}
                          </span>
                        )}
                      </div>
                    </th>
                  );
                })}
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-100 text-xs">
              {loading ? (
                // Loading Skeleton Rows
                Array.from({ length: 6 }).map((_, i) => (
                  <tr key={`skel-${i}`} className="animate-pulse">
                    {columns.map((_, cIdx) => (
                      <td key={`skel-c-${cIdx}`} className="px-4 py-3.5">
                        <div className="h-4 bg-slate-100 rounded w-4/5"></div>
                      </td>
                    ))}
                  </tr>
                ))
              ) : paginatedData.length === 0 ? (
                <tr>
                  <td colSpan={columns.length} className="p-8 text-center">
                    <EmptyState
                      title={emptyTitle}
                      description={emptyMessage}
                      actionLabel={searchQuery ? "Clear Search" : undefined}
                      onAction={searchQuery ? () => setSearchQuery("") : undefined}
                    />
                  </td>
                </tr>
              ) : (
                paginatedData.map((row, rIdx) => {
                  const key = getRowKey(row, rIdx);
                  return (
                    <tr
                      key={key}
                      onClick={() => onRowClick?.(row)}
                      className={`hover:bg-blue-50/40 transition-colors duration-150 ${
                        onRowClick ? "cursor-pointer" : ""
                      }`}
                    >
                      {columns.map((col) => {
                        const cellContent = col.render ? col.render(row) : row[col.key];
                        return (
                          <td
                            key={`${key}-${col.key}`}
                            className={`px-4 py-3 ${
                              col.align === "right"
                                ? "text-right"
                                : col.align === "center"
                                ? "text-center"
                                : "text-left"
                            }`}
                          >
                            {cellContent}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination & Footer */}
        <div className="px-4 py-3 bg-slate-50/70 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <span>
              Showing{" "}
              <strong className="text-slate-700">
                {totalRows === 0 ? 0 : (validPage - 1) * rowsPerPage + 1}
              </strong>{" "}
              to{" "}
              <strong className="text-slate-700">
                {Math.min(validPage * rowsPerPage, totalRows)}
              </strong>{" "}
              of <strong className="text-slate-700">{totalRows}</strong> records
            </span>

            <select
              value={rowsPerPage}
              onChange={(e) => {
                setRowsPerPage(Number(e.target.value));
                setCurrentPage(1);
              }}
              className="ml-2 text-xs border border-slate-200 rounded px-1.5 py-0.5 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value={10}>10 / page</option>
              <option value={15}>15 / page</option>
              <option value={25}>25 / page</option>
              <option value={50}>50 / page</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <Button
              variant="outline"
              size="sm"
              disabled={validPage <= 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            >
              Previous
            </Button>
            <span className="px-2 text-slate-600 font-medium">
              Page {validPage} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={validPage >= totalPages}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            >
              Next
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
