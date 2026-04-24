// packages/ui/components/DataTable.tsx
"use client";

import React, { useState, useMemo } from "react";

interface Column<T> {
  key: string;
  header: string;
  render?: (item: T) => React.ReactNode;
  sortable?: boolean;
  width?: string;
}

interface DataTableProps<T extends Record<string, unknown>> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (item: T) => void;
  emptyMessage?: string;
  keyField?: string;
}

type SortDirection = "asc" | "desc";

export function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  onRowClick,
  emptyMessage = "No data available",
  keyField = "id",
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDirection("asc");
    }
  };

  const sortedData = useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (aVal == null || bVal == null) return 0;
      const cmp = String(aVal).localeCompare(String(bVal), undefined, { numeric: true });
      return sortDirection === "asc" ? cmp : -cmp;
    });
  }, [data, sortKey, sortDirection]);

  if (data.length === 0) {
    return (
      <div
        className="flex flex-col items-center justify-center py-16 rounded-lg"
        style={{ backgroundColor: "var(--color-surface)" }}
      >
        <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
          {emptyMessage}
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg" style={{ backgroundColor: "var(--color-surface)" }}>
      <table className="w-full">
        <thead>
          <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
            {columns.map((col) => (
              <th
                key={col.key}
                className={`text-left text-xs font-medium uppercase tracking-wide px-4 py-3 ${
                  col.sortable ? "cursor-pointer select-none" : ""
                }`}
                style={{
                  color: "var(--color-text-secondary)",
                  width: col.width,
                }}
                onClick={() => col.sortable && handleSort(col.key)}
              >
                <span className="flex items-center gap-1.5">
                  {col.header}
                  {col.sortable && sortKey === col.key && (
                    <span className="text-xs" style={{ color: "var(--color-accent)" }}>
                      {sortDirection === "asc" ? "\u2191" : "\u2193"}
                    </span>
                  )}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedData.map((item, rowIndex) => (
            <tr
              key={String(item[keyField]) || rowIndex}
              className={`transition-colors duration-150 ${
                onRowClick ? "cursor-pointer" : ""
              }`}
              style={{
                borderBottom:
                  rowIndex < sortedData.length - 1
                    ? "1px solid rgba(38,38,38,0.15)"
                    : "none",
              }}
              onClick={() => onRowClick?.(item)}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.backgroundColor = "var(--color-surface-raised)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.backgroundColor = "transparent";
              }}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className="px-4 py-3 text-sm"
                  style={{ color: "var(--color-text)" }}
                >
                  {col.render ? col.render(item) : String(item[col.key] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
