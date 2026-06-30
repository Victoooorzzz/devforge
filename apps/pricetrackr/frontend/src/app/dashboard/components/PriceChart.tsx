"use client";
import { useState, useEffect } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { format } from "date-fns";
import { Loader2 } from "lucide-react";

interface PricePoint {
  price: number | null;
  in_stock: boolean | null;
  recorded_at: string;
}

interface PriceChartProps {
  trackerId: number;
  label: string;
}

export default function PriceChart({ trackerId, label }: PriceChartProps) {
  const [data, setData] = useState<PricePoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    const fetchHistory = async () => {
      setLoading(true);
      setError(false);
      try {
        const res = await fetch(`/api/history/${trackerId}`);
        if (!res.ok) throw new Error("Failed to fetch");
        const historyData = await res.json();
        if (active) {
          setData(historyData);
        }
      } catch (err) {
        if (active) {
          setError(true);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    fetchHistory();
    return () => {
      active = false;
    };
  }, [trackerId]);

  if (loading) {
    return (
      <div className="h-64 flex items-center justify-center bg-zinc-950/40 rounded-xl border border-white/5 backdrop-blur-md">
        <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
      </div>
    );
  }

  if (error || data.length === 0) {
    return (
      <div className="h-64 flex flex-col items-center justify-center bg-zinc-950/40 rounded-xl border border-white/5 backdrop-blur-md p-4 text-center">
        <p className="text-sm text-zinc-400">
          {error ? "Could not load price history." : "No price history data points yet."}
        </p>
        <p className="text-xs text-zinc-500 mt-1">
          Historical data will appear once Render performs its scheduled scrapes.
        </p>
      </div>
    );
  }

  // Format dates for display
  const chartData = data.map((pt) => ({
    ...pt,
    formattedDate: pt.recorded_at ? format(new Date(pt.recorded_at), "MMM d, h:mm a") : "",
    priceNumber: pt.price !== null ? parseFloat(pt.price as any) : null,
  }));

  const prices = chartData.map((d) => d.priceNumber).filter((p): p is number => p !== null);
  const minPrice = prices.length ? Math.min(...prices) : 0;
  const maxPrice = prices.length ? Math.max(...prices) : 100;
  const yDomain = [
    Math.max(0, Math.floor(minPrice * 0.95)),
    Math.ceil(maxPrice * 1.05),
  ];

  return (
    <div className="bg-zinc-950/30 rounded-xl border border-white/5 backdrop-blur-md p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white tracking-wide truncate max-w-[70%]">
          Price History — {label}
        </h3>
        {prices.length > 0 && (
          <span className="text-xs px-2 py-0.5 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded-full font-mono font-medium">
            Current: ${prices[prices.length - 1].toFixed(2)}
          </span>
        )}
      </div>

      <div className="h-48 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 5, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f1f23" vertical={false} />
            <XAxis
              dataKey="formattedDate"
              stroke="#52525b"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              dy={10}
              tickFormatter={(val) => val.split(",")[0]}
            />
            <YAxis
              domain={yDomain}
              stroke="#52525b"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              dx={-5}
              tickFormatter={(val) => `$${val}`}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const dataPoint = payload[0].payload as any;
                  return (
                    <div className="bg-zinc-900/90 border border-white/10 p-3 rounded-lg backdrop-blur-md shadow-xl text-left space-y-1">
                      <p className="text-[10px] text-zinc-400 font-medium">
                        {dataPoint.formattedDate}
                      </p>
                      <p className="text-sm font-bold font-mono text-indigo-400">
                        Price: ${dataPoint.priceNumber?.toFixed(2)}
                      </p>
                      <p className="text-[10px] flex items-center gap-1">
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${
                            dataPoint.in_stock ? "bg-emerald-500" : "bg-red-500"
                          }`}
                        />
                        <span className={dataPoint.in_stock ? "text-emerald-400" : "text-red-400"}>
                          {dataPoint.in_stock ? "In Stock" : "Out of Stock"}
                        </span>
                      </p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Area
              type="monotone"
              dataKey="priceNumber"
              stroke="#6366f1"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#priceGradient)"
              activeDot={{ r: 4, stroke: "#6366f1", strokeWidth: 1 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
