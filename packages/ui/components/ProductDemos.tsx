"use client";

import React, { useMemo, useState } from "react";
import type { ProductSlug } from "@devforge/core";
import { ActivityTimeline } from "./ActivityTimeline";
import { DemoDataTable, TableStatus } from "./DemoDataTable";
import { JsonViewer } from "./JsonViewer";
import { PriceChart } from "./PriceChart";
import { StatusBadge } from "./StatusBadge";

interface ProductDemoProps {
  slug: ProductSlug;
}

export function ProductDemo({ slug }: ProductDemoProps) {
  if (slug === "filecleaner") return <FileCleanerDemo />;
  if (slug === "webhookmonitor") return <WebhookMonitorDemo />;
  if (slug === "feedbacklens") return <FeedbackLensDemo />;
  if (slug === "pricetrackr") return <PriceTrackrDemo />;
  return <InvoiceFollowDemo />;
}

interface DirtyRow {
  row: string;
  email: string;
  amount: string;
  country: string;
  issue: string;
  status: string;
}

function FileCleanerDemo() {
  const [cleaned, setCleaned] = useState(false);
  const dirtyRows: DirtyRow[] = [
    { row: "001", email: " ANA@Example.com ", amount: "$1,200.00", country: "usa", issue: "Whitespace, case", status: "dirty" },
    { row: "002", email: "ana@example.com", amount: "1200", country: "United States", issue: "Duplicate", status: "dirty" },
    { row: "003", email: "", amount: "N/A", country: "es", issue: "Missing email, invalid amount", status: "dirty" },
    { row: "004", email: "marco@agency.io", amount: "780,50 EUR", country: "Spain", issue: "Currency format", status: "dirty" },
  ];
  const cleanRows: DirtyRow[] = [
    { row: "001", email: "ana@example.com", amount: "1200.00", country: "US", issue: "Normalized", status: "clean" },
    { row: "002", email: "ana@example.com", amount: "merged", country: "US", issue: "Duplicate grouped", status: "review" },
    { row: "003", email: "missing", amount: "flagged", country: "ES", issue: "Needs owner review", status: "review" },
    { row: "004", email: "marco@agency.io", amount: "780.50", country: "ES", issue: "Normalized", status: "clean" },
  ];
  const rows = cleaned ? cleanRows : dirtyRows;

  return (
    <div className="grid gap-6 lg:grid-cols-[1.35fr_0.65fr]">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-mono text-xs" style={{ color: "var(--color-text-secondary)" }}>sales_ops_dirty.csv</p>
            <h3 className="mt-1 text-xl font-semibold" style={{ color: "var(--color-text)" }}>
              {cleaned ? "Clean preview and quality report" : "Dirty file preview"}
            </h3>
          </div>
          <button type="button" onClick={() => setCleaned((value) => !value)} className="btn-primary">
            {cleaned ? "Reset dirty file" : "Run cleaning demo"}
          </button>
        </div>
        <DemoDataTable
          rows={rows}
          getRowKey={(row) => row.row}
          columns={[
            { key: "row", label: "Row" },
            { key: "email", label: "Email" },
            { key: "amount", label: "Amount" },
            { key: "country", label: "Country" },
            { key: "issue", label: "Detected issue" },
            {
              key: "status",
              label: "Status",
              render: (row) => (
                <TableStatus tone={row.status === "clean" ? "success" : row.status === "review" ? "warning" : "danger"}>
                  {row.status}
                </TableStatus>
              ),
            },
          ]}
        />
      </div>
      <div className="space-y-4">
        <div className="surface-card-raised border border-white/10 p-4">
          <h4 className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>Cleaning report</h4>
          <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
            {[
              ["Rows scanned", "4,238"],
              ["Duplicates", cleaned ? "311 grouped" : "311 found"],
              ["Nulls", cleaned ? "42 flagged" : "42 found"],
              ["Format fixes", cleaned ? "1,804 applied" : "1,804 pending"],
            ].map(([label, value]) => (
              <div key={label} className="rounded-md bg-black/30 p-3">
                <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>{label}</p>
                <p className="mt-1 font-semibold" style={{ color: "var(--color-text)" }}>{value}</p>
              </div>
            ))}
          </div>
        </div>
        <div className="surface-card-raised border border-white/10 p-4">
          <h4 className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>Plan gates</h4>
          <div className="mt-3 space-y-2 text-sm">
            <div className="flex items-center justify-between gap-3"><span>Schema rules</span><StatusBadge tone="accent">Pro</StatusBadge></div>
            <div className="flex items-center justify-between gap-3"><span>10k fuzzy rows</span><StatusBadge tone="success">Team</StatusBadge></div>
            <div className="flex items-center justify-between gap-3"><span>Parallel batch</span><StatusBadge tone="success">Team</StatusBadge></div>
          </div>
        </div>
      </div>
    </div>
  );
}

interface WebhookRow {
  id: string;
  method: string;
  provider: string;
  status: string;
  latency: string;
}

function WebhookMonitorDemo() {
  const events: WebhookRow[] = [
    { id: "evt_1042", method: "POST", provider: "Stripe", status: "failed", latency: "842 ms" },
    { id: "evt_1041", method: "POST", provider: "GitHub", status: "ok", latency: "188 ms" },
    { id: "evt_1040", method: "POST", provider: "Shopify", status: "retrying", latency: "1.2 s" },
  ];
  const [selectedId, setSelectedId] = useState(events[0].id);
  const selected = events.find((event) => event.id === selectedId) || events[0];
  const payload = {
    id: selected.id,
    provider: selected.provider.toLowerCase(),
    type: selected.provider === "Stripe" ? "invoice.payment_failed" : "order.updated",
    retry_count: selected.status === "retrying" ? 2 : 0,
    signature_valid: selected.status !== "failed",
  };
  const headers = {
    "content-type": "application/json",
    "user-agent": `${selected.provider}-Webhook/1.0`,
    "x-devforge-endpoint": "/hooks/prod-8f2",
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
      <div className="space-y-4">
        <div className="surface-card-raised border border-white/10 p-4">
          <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>Endpoint</p>
          <div className="mt-3 rounded-md bg-black/40 p-3 font-mono text-xs" style={{ color: "var(--color-text)" }}>
            https://api.devforgeapp.pro/webhooks/prod-8f2
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <StatusBadge tone="success">Receiving</StatusBadge>
            <StatusBadge tone="accent">Signature check</StatusBadge>
            <StatusBadge tone="locked">Free: replay locked</StatusBadge>
          </div>
        </div>
        <DemoDataTable
          rows={events}
          getRowKey={(row) => row.id}
          columns={[
            { key: "id", label: "Event", render: (row) => <button type="button" onClick={() => setSelectedId(row.id)} className="font-mono text-xs underline" style={{ color: row.id === selectedId ? "var(--color-accent)" : "var(--color-text)" }}>{row.id}</button> },
            { key: "provider", label: "Provider" },
            { key: "status", label: "Status", render: (row) => <TableStatus tone={row.status === "ok" ? "success" : row.status === "retrying" ? "warning" : "danger"}>{row.status}</TableStatus> },
            { key: "latency", label: "Latency" },
          ]}
        />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <JsonViewer title="Payload" value={payload} />
        <JsonViewer title="Headers" value={headers} />
        <div className="surface-card-raised border border-white/10 p-4 md:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h4 className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>Replay and diff preview</h4>
            <div className="flex gap-2">
              <button type="button" className="btn-secondary">Replay</button>
              <button type="button" className="btn-secondary">Open diff</button>
            </div>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-3 text-sm">
            <div className="rounded-md bg-black/30 p-3"><p className="text-xs text-neutral-400">Body diff</p><p className="mt-1 text-white">3 fields changed</p></div>
            <div className="rounded-md bg-black/30 p-3"><p className="text-xs text-neutral-400">Search</p><p className="mt-1 text-white">event.type contains invoice</p></div>
            <div className="rounded-md bg-black/30 p-3"><p className="text-xs text-neutral-400">Retention</p><p className="mt-1 text-white">30 days on Pro</p></div>
          </div>
        </div>
      </div>
    </div>
  );
}

interface FeedbackRow {
  id: string;
  source: string;
  text: string;
  sentiment: string;
  theme: string;
  status: string;
}

function FeedbackLensDemo() {
  const [filter, setFilter] = useState("all");
  const feedback: FeedbackRow[] = [
    { id: "fb-21", source: "Canny", text: "CSV import fails with accented headers", sentiment: "negative", theme: "Import reliability", status: "urgent" },
    { id: "fb-20", source: "Email", text: "Love the dashboard but need weekly digest", sentiment: "positive", theme: "Reporting", status: "open" },
    { id: "fb-19", source: "GitHub", text: "Same import bug as ticket 21", sentiment: "negative", theme: "Import reliability", status: "duplicate" },
    { id: "fb-18", source: "Manual", text: "Can you add SSO for agencies?", sentiment: "neutral", theme: "Team admin", status: "open" },
  ];
  const visibleRows = filter === "all" ? feedback : feedback.filter((row) => row.status === filter);

  return (
    <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            {["all", "urgent", "duplicate"].map((item) => (
              <button key={item} type="button" onClick={() => setFilter(item)} className={filter === item ? "btn-primary" : "btn-secondary"}>
                {item}
              </button>
            ))}
          </div>
          <StatusBadge tone="accent">4 sources connected</StatusBadge>
        </div>
        <DemoDataTable
          rows={visibleRows}
          getRowKey={(row) => row.id}
          columns={[
            { key: "source", label: "Source" },
            { key: "text", label: "Feedback" },
            { key: "sentiment", label: "Sentiment", render: (row) => <TableStatus tone={row.sentiment === "positive" ? "success" : row.sentiment === "negative" ? "danger" : "neutral"}>{row.sentiment}</TableStatus> },
            { key: "theme", label: "Theme" },
            { key: "status", label: "Status", render: (row) => <TableStatus tone={row.status === "urgent" ? "danger" : row.status === "duplicate" ? "warning" : "neutral"}>{row.status}</TableStatus> },
          ]}
        />
      </div>
      <div className="space-y-4">
        <div className="surface-card-raised border border-white/10 p-4">
          <h4 className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>Cluster insight</h4>
          <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
            Import reliability is the top complaint this week. Two reports are duplicates, one is urgent, and the GitHub issue action is ready on Pro.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <StatusBadge tone="danger">negative spike</StatusBadge>
            <StatusBadge tone="warning">duplicate group</StatusBadge>
            <StatusBadge tone="accent">GitHub issue draft</StatusBadge>
          </div>
        </div>
        <JsonViewer
          title="Weekly digest preview"
          value={{
            total_feedback: 284,
            urgent: 17,
            top_themes: ["Import reliability", "Weekly digest", "Team admin"],
            action: "Create GitHub issue from fb-21 cluster",
          }}
        />
      </div>
    </div>
  );
}

function PriceTrackrDemo() {
  const [selector, setSelector] = useState(".price-current");
  const products = [
    { sku: "cam-001", url: "shop.example/camera", price: "$219.99", state: "dropped", check: "15 min ago" },
    { sku: "desk-881", url: "market.example/desk", price: "$349.00", state: "unchanged", check: "1 hr ago" },
    { sku: "ssd-240", url: "retail.example/ssd", price: "paused", state: "error paused", check: "2 hrs ago" },
  ];
  const chartPoints = [
    { label: "Mon", value: 249.99 },
    { label: "Tue", value: 239.99 },
    { label: "Wed", value: 239.99 },
    { label: "Thu", value: 229.99 },
    { label: "Fri", value: 219.99 },
  ];

  return (
    <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
      <div className="space-y-4">
        <DemoDataTable
          rows={products}
          getRowKey={(row) => row.sku}
          columns={[
            { key: "sku", label: "SKU" },
            { key: "url", label: "URL" },
            { key: "price", label: "Price" },
            { key: "state", label: "State", render: (row) => <TableStatus tone={row.state === "dropped" ? "success" : row.state === "error paused" ? "danger" : "neutral"}>{row.state}</TableStatus> },
            { key: "check", label: "Last check" },
          ]}
        />
        <div className="surface-card-raised border border-white/10 p-4">
          <label className="text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>Custom selector</label>
          <div className="mt-3 flex gap-2">
            <input value={selector} onChange={(event) => setSelector(event.target.value)} className="input-field" />
            <button type="button" className="btn-secondary">Test</button>
          </div>
          <p className="mt-2 text-xs" style={{ color: "var(--color-text-secondary)" }}>Team can run checks every 10 minutes; Pro starts at hourly checks.</p>
        </div>
      </div>
      <div className="space-y-4">
        <PriceChart points={chartPoints} />
        <div className="grid gap-3 md:grid-cols-3">
          <div className="surface-card-raised border border-white/10 p-4"><p className="text-xs text-neutral-400">Alert</p><p className="mt-1 font-semibold text-white">below $225</p></div>
          <div className="surface-card-raised border border-white/10 p-4"><p className="text-xs text-neutral-400">Webhook</p><p className="mt-1 font-semibold text-white">Pro enabled</p></div>
          <div className="surface-card-raised border border-white/10 p-4"><p className="text-xs text-neutral-400">Selector</p><p className="mt-1 font-semibold text-white">{selector}</p></div>
        </div>
      </div>
    </div>
  );
}

function InvoiceFollowDemo() {
  const [selected, setSelected] = useState("INV-1048");
  const invoices = [
    { id: "INV-1048", customer: "Northstar Studio", amount: "$2,400", state: "overdue", nlp: "promise to pay" },
    { id: "INV-1047", customer: "Pixel Ops", amount: "$980", state: "pending", nlp: "no reply" },
    { id: "INV-1046", customer: "Acme Labs", amount: "$1,800", state: "paid", nlp: "paid via Stripe" },
    { id: "INV-1045", customer: "Orbit Works", amount: "$640", state: "disputed", nlp: "pause reminders" },
  ];
  const current = invoices.find((invoice) => invoice.id === selected) || invoices[0];
  const timeline = useMemo(() => [
    { time: "Day 0", title: "Invoice imported", description: `${current.id} synced from CSV with customer and due date.`, status: current.state, tone: current.state === "paid" ? "success" as const : current.state === "disputed" ? "danger" as const : "warning" as const },
    { time: "Day 3", title: "Reminder sent", description: "Friendly follow-up email scheduled from the workspace mailbox.", status: "sent", tone: "success" as const },
    { time: "Day 7", title: "Reply classified", description: `NLP classified the latest reply as ${current.nlp}.`, status: "NLP", tone: "accent" as const },
  ], [current]);

  return (
    <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
      <div className="space-y-4">
        <DemoDataTable
          rows={invoices}
          getRowKey={(row) => row.id}
          columns={[
            { key: "id", label: "Invoice", render: (row) => <button type="button" onClick={() => setSelected(row.id)} className="font-mono text-xs underline" style={{ color: row.id === selected ? "var(--color-accent)" : "var(--color-text)" }}>{row.id}</button> },
            { key: "customer", label: "Customer" },
            { key: "amount", label: "Amount" },
            { key: "state", label: "Status", render: (row) => <TableStatus tone={row.state === "paid" ? "success" : row.state === "disputed" ? "danger" : row.state === "overdue" ? "warning" : "neutral"}>{row.state}</TableStatus> },
            { key: "nlp", label: "Reply" },
          ]}
        />
        <div className="surface-card-raised border border-white/10 p-4">
          <h4 className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>Payment reconciliation</h4>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <div className="rounded-md bg-black/30 p-3"><p className="text-xs text-neutral-400">Stripe</p><p className="mt-1 text-white">2 payments matched</p></div>
            <div className="rounded-md bg-black/30 p-3"><p className="text-xs text-neutral-400">PayPal</p><p className="mt-1 text-white">1 pending review</p></div>
          </div>
        </div>
      </div>
      <div className="space-y-4">
        <ActivityTimeline items={timeline} />
        <JsonViewer
          title="Weekly financial digest"
          value={{
            overdue_amount: "$4,020",
            promised_amount: "$2,400",
            disputed_count: 1,
            next_action: `Send human review for ${current.id}`,
          }}
        />
      </div>
    </div>
  );
}
