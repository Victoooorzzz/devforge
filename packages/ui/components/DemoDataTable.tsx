import React from "react";
import { StatusBadge, type StatusBadgeTone } from "./StatusBadge";

export interface DemoTableColumn<T> {
  key: keyof T | string;
  label: string;
  render?: (row: T) => React.ReactNode;
}

interface DemoDataTableProps<T> {
  columns: DemoTableColumn<T>[];
  rows: T[];
  getRowKey: (row: T, index: number) => string;
  className?: string;
  rowClassName?: (row: T, index: number) => string;
  cellClassName?: (row: T, column: DemoTableColumn<T>, index: number) => string;
}

export function DemoDataTable<T>({ columns, rows, getRowKey, className = "", rowClassName, cellClassName }: DemoDataTableProps<T>) {
  return (
    <div className={`overflow-hidden rounded-md border border-white/10 ${className}`}>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead style={{ backgroundColor: "rgba(255,255,255,0.04)" }}>
            <tr>
              {columns.map((column) => (
                <th key={String(column.key)} className="px-4 py-3 text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/10">
            {rows.map((row, index) => (
              <tr key={getRowKey(row, index)} className={`bg-black/20 ${rowClassName?.(row, index) || ""}`}>
                {columns.map((column) => (
                  <td key={String(column.key)} className={`px-4 py-3 align-top ${cellClassName?.(row, column, index) || ""}`} style={{ color: "var(--color-text)" }}>
                    {column.render ? column.render(row) : String((row as Record<string, unknown>)[String(column.key)] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function TableStatus({ children, tone = "neutral" }: { children: React.ReactNode; tone?: StatusBadgeTone }) {
  return <StatusBadge tone={tone}>{children}</StatusBadge>;
}
