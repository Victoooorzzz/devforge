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
  file: string;
  rows: string;
  problems: string;
  suggestedFix: string;
  status: string;
}

function FileCleanerDemo() {
  const [cleaned, setCleaned] = useState(false);
  const [isCleaning, setIsCleaning] = useState(false);
  const dirtyRows: DirtyRow[] = [
    { file: "customers_lima_dirty.csv", rows: "2,481", problems: "17 headers, 83 duplicates, 12 invalid emails", suggestedFix: "Normalize + dedupe", status: "Needs review" },
    { file: "invoices_march.xlsx", rows: "640", problems: "mixed dates, empty totals, S/. text in amount", suggestedFix: "Validate amounts", status: "Ready" },
    { file: "partners_export.json", rows: "1,200", problems: "nested fields, missing IDs, odd casing", suggestedFix: "Flatten schema", status: "Processing" },
  ];
  const cleanRows: DirtyRow[] = [
    { file: "customers_lima_dirty.csv", rows: "2,398", problems: "83 duplicates grouped, 12 emails flagged", suggestedFix: "Preview export", status: "Review" },
    { file: "invoices_march.xlsx", rows: "640", problems: "31 dates normalized, 4 empty totals flagged", suggestedFix: "Approve fixes", status: "Ready" },
    { file: "partners_export.json", rows: "1,200", problems: "schema flattened, 19 missing IDs flagged", suggestedFix: "Manual review", status: "Review" },
  ];
  const rows = cleaned ? cleanRows : dirtyRows;
  const handleCleaningDemo = () => {
    if (isCleaning) return;
    if (cleaned) {
      setCleaned(false);
      return;
    }

    setIsCleaning(true);
    window.setTimeout(() => {
      setCleaned(true);
      setIsCleaning(false);
    }, 720);
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[1.35fr_0.65fr]">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-mono text-xs" style={{ color: "var(--color-text-secondary)" }}>sales_ops_dirty.csv</p>
            <h3 className="mt-1 text-xl font-semibold" style={{ color: "var(--color-text)" }}>
              {cleaned ? "Clean preview and quality report" : "Files with real cleanup problems"}
            </h3>
          </div>
          <button type="button" onClick={handleCleaningDemo} className="cleaning-demo-button btn-primary" disabled={isCleaning}>
            {isCleaning ? "Cleaning rows..." : cleaned ? "Reset dirty file" : "Run cleaning demo"}
          </button>
        </div>
        <DemoDataTable
          rows={rows}
          getRowKey={(row) => row.file}
          className={isCleaning ? "cleaning-table-active" : ""}
          rowClassName={(row, index) => row.status === "dirty" || isCleaning ? `dirty-row-transition dirty-row-${index}` : "clean-row-transition"}
          cellClassName={(row, column) => {
            const key = String(column.key);
            return row.status === "dirty" && key !== "row" ? "dirty-cell" : "";
          }}
          columns={[
            { key: "file", label: "File" },
            { key: "rows", label: "Rows" },
            { key: "problems", label: "Problems" },
            { key: "suggestedFix", label: "Suggested fix" },
            {
              key: "status",
              label: "Status",
              render: (row) => (
                <TableStatus tone={row.status === "Ready" ? "success" : row.status === "Review" || row.status === "Needs review" ? "warning" : "accent"}>
                  {row.status}
                </TableStatus>
              ),
            },
          ]}
        />
      </div>
      <div className="space-y-4">
        <div className="demo-pulse surface-card-raised border border-white/10 p-4">
          <h4 className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>Before / after sample</h4>
          <div className="mt-3 space-y-3 font-mono text-xs leading-relaxed">
            <div className="rounded-md bg-black/30 p-3">
              <p style={{ color: "var(--color-accent)" }}>Before</p>
              <p className="mt-2 whitespace-pre-line" style={{ color: "var(--color-text-secondary)" }}>Nombre Cliente | E-mail | monto S/. | fecha pago{"\n"}ACME SAC | test@ | S/ 1,200 | 12-31-24{"\n"}ACME SAC | test@ | 1200 | 31/12/2024</p>
            </div>
            <div className="rounded-md bg-black/30 p-3">
              <p style={{ color: "var(--color-accent)" }}>After</p>
              <p className="mt-2 whitespace-pre-line" style={{ color: "var(--color-text)" }}>customer_name | email | amount_pen | payment_date{"\n"}ACME SAC | test@acme.pe | 1200.00 | 2024-12-31</p>
            </div>
          </div>
        </div>
        <div className="demo-pulse surface-card-raised border border-white/10 p-4">
          <h4 className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>Cleaning report</h4>
          <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
            {[
              ["Rows scanned", "4,321"],
              ["Duplicate rows", cleaned ? "83 grouped" : "83 found"],
              ["Invalid emails", cleaned ? "12 flagged" : "12 found"],
              ["Headers renamed", cleaned ? "17 mapped" : "17 pending"],
            ].map(([label, value]) => (
              <div key={label} className="rounded-md bg-black/30 p-3">
                <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>{label}</p>
                <p className="mt-1 font-semibold" style={{ color: "var(--color-text)" }}>{value}</p>
              </div>
            ))}
          </div>
        </div>
        <div className="demo-pulse surface-card-raised border border-white/10 p-4">
          <h4 className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>Plan gates</h4>
          <div className="mt-3 space-y-2 text-sm">
            <div className="flex items-center justify-between gap-3"><span>Schema rules</span><StatusBadge tone="accent">Pro</StatusBadge></div>
            <a href="/register?plan=pro" className="plan-gate-row" data-tooltip="Available on Pro. Upgrade now"><span>10k fuzzy rows</span><StatusBadge tone="accent">Pro</StatusBadge></a>
            <a href="/register?plan=pro" className="plan-gate-row" data-tooltip="Available on Pro. Upgrade now"><span>Parallel batch</span><StatusBadge tone="accent">Pro</StatusBadge></a>
          </div>
        </div>
      </div>
    </div>
  );
}

interface WebhookRow {
  id: string;
  time: string;
  method: string;
  endpoint: string;
  provider: string;
  status: string;
  latency: string;
  attempt: string;
  response: string;
}

function WebhookMonitorDemo() {
  const events: WebhookRow[] = [
    { id: "evt_1P9xA2", time: "12:04:18.221", method: "POST", endpoint: "/webhooks/stripe", provider: "Stripe", status: "500", latency: "842 ms", attempt: "1/3", response: "missing customer_id" },
    { id: "evt_1P9xA2_r1", time: "12:04:49.003", method: "POST", endpoint: "/webhooks/stripe", provider: "Stripe", status: "200", latency: "118 ms", attempt: "replay 1", response: "accepted" },
    { id: "gh_891a", time: "12:07:03.552", method: "POST", endpoint: "/webhooks/github", provider: "GitHub", status: "timeout", latency: "3.0 s", attempt: "2/3", response: "worker busy" },
  ];
  const [selectedId, setSelectedId] = useState(events[0].id);
  const selected = events.find((event) => event.id === selectedId) || events[0];
  const payload = {
    id: selected.id,
    provider: selected.provider.toLowerCase(),
    type: selected.provider === "Stripe" ? "invoice.payment_failed" : "order.updated",
    customer: selected.status === "500" ? null : "cus_9x81",
    metadata: { customer_id: "cus_9x81" },
    amount_due: 12900,
    retry_count: selected.attempt.includes("/") ? Number(selected.attempt.charAt(0)) : 0,
    signature_valid: true,
  };
  const headers = {
    "x-signature": "valid",
    "content-type": "application/json",
    "user-agent": `${selected.provider}-Webhook/1.0`,
    "idempotency-key": "wh_8a91...",
    "x-devforge-endpoint": "/hooks/prod-8f2",
  };

  return (
    <div className="grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
      <div className="min-w-0 space-y-4">
        <div className="demo-pulse surface-card-raised border border-white/10 p-4">
          <p className="text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>Terminal capture</p>
          <div className="mt-3 rounded-md bg-black/40 p-3 font-mono text-xs leading-relaxed" style={{ color: "var(--color-text)" }}>
            <p>$ devforge-monitor listen --endpoint stripe-prod</p>
            <p>[12:04:18.221] POST /webhooks/stripe 500 842ms attempt=1 event=invoice.payment_failed</p>
            <p>[12:04:19.006] signature=valid id=evt_1P9xA2 retry_after=30s</p>
            <p>[12:04:19.441] response.body="Cannot read property 'customer_id' of undefined"</p>
            <p>[12:04:49.003] POST /webhooks/stripe 200 118ms attempt=2 replay=true</p>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <StatusBadge tone="success">Receiving</StatusBadge>
            <StatusBadge tone="accent">Signature check</StatusBadge>
            <StatusBadge tone="locked">Sensitive fields masked</StatusBadge>
          </div>
        </div>
        <DemoDataTable
          rows={events}
          getRowKey={(row) => row.id}
          columns={[
            { key: "time", label: "Time" },
            { key: "id", label: "Event", render: (row) => <button type="button" onClick={() => setSelectedId(row.id)} className="font-mono text-xs underline" style={{ color: row.id === selectedId ? "var(--color-accent)" : "var(--color-text)" }}>{row.id}</button> },
            { key: "endpoint", label: "Endpoint" },
            { key: "attempt", label: "Attempt" },
            { key: "status", label: "Status", render: (row) => <TableStatus tone={row.status === "200" ? "success" : row.status === "timeout" ? "warning" : "danger"}>{row.status}</TableStatus> },
            { key: "latency", label: "Latency" },
            { key: "response", label: "Response" },
          ]}
        />
      </div>
      <div className="grid min-w-0 gap-4 md:grid-cols-2">
        <div className="surface-card-raised border border-white/10 p-4 md:col-span-2">
          <div className="flex flex-wrap gap-2">
            {["Overview", "Payload", "Headers", "Response", "Replay history"].map((tab) => (
              <StatusBadge key={tab} tone={tab === "Payload" ? "accent" : "neutral"}>{tab}</StatusBadge>
            ))}
          </div>
        </div>
        <JsonViewer title="Payload" value={payload} />
        <JsonViewer title="Headers" value={headers} />
        <div className="surface-card-raised border border-white/10 p-4 md:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h4 className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>Response and replay history</h4>
            <div className="flex flex-wrap gap-2">
              <button type="button" className="btn-secondary">Replay this event</button>
              <button type="button" className="btn-secondary">Copy cURL</button>
            </div>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-3 text-sm">
            <div className="rounded-md bg-black/30 p-3"><p className="text-xs text-neutral-400">Attempt 1</p><p className="mt-1 text-white">500 - missing customer_id</p></div>
            <div className="rounded-md bg-black/30 p-3"><p className="text-xs text-neutral-400">Attempt 2</p><p className="mt-1 text-white">500 - timeout after 3s</p></div>
            <div className="rounded-md bg-black/30 p-3"><p className="text-xs text-neutral-400">Replay 1</p><p className="mt-1 text-white">200 - accepted</p></div>
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
  theme: string;
  confidence: string;
  duplicateOf: string;
  action: string;
  status: string;
}

function FeedbackLensDemo() {
  const [filter, setFilter] = useState("all");
  const feedback: FeedbackRow[] = [
    { id: "fb-21", source: "CSV import", text: "csv import broke again w/ accents... same as last week :(", theme: "Import reliability", confidence: "92%", duplicateOf: "BUG-21", action: "Link duplicate", status: "urgent" },
    { id: "fb-20", source: "Email", text: "Not sure if bug or me but weekly digest never arrived", theme: "Reporting", confidence: "81%", duplicateOf: "-", action: "Investigate", status: "review" },
    { id: "fb-19", source: "Pasted note", text: "this is basically ticket #214, right?", theme: "Import reliability", confidence: "88%", duplicateOf: "BUG-21", action: "Merge thread", status: "duplicate" },
    { id: "fb-18", source: "Sales note", text: "+1 on SSO. We can't onboard agency clients without it.", theme: "Team admin", confidence: "76%", duplicateOf: "-", action: "Add to roadmap", status: "review" },
    { id: "fb-17", source: "Support note", text: "dashboard is nice but i need export before friday", theme: "Exports", confidence: "69%", duplicateOf: "-", action: "Human review", status: "review" },
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
          <StatusBadge tone="accent">4 inputs reviewed</StatusBadge>
        </div>
        <DemoDataTable
          rows={visibleRows}
          getRowKey={(row) => row.id}
          columns={[
            { key: "source", label: "Source" },
            { key: "text", label: "Raw feedback" },
            { key: "theme", label: "Theme" },
            { key: "confidence", label: "Confidence" },
            { key: "duplicateOf", label: "Duplicate of" },
            { key: "action", label: "Suggested action" },
            { key: "status", label: "Review", render: (row) => <TableStatus tone={row.status === "urgent" ? "danger" : row.status === "duplicate" ? "warning" : "accent"}>{row.status}</TableStatus> },
          ]}
        />
      </div>
      <div className="space-y-4">
        <div className="demo-pulse surface-card-raised border border-white/10 p-4">
          <h4 className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>Duplicate cluster breakdown</h4>
          <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
            Cluster: CSV import fails with accented headers. Inputs include CSV rows, forwarded messages, pasted notes, and support notes. Likely UTF-8 normalization issue during header mapping.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <StatusBadge tone="danger">negative spike</StatusBadge>
            <StatusBadge tone="warning">duplicate group</StatusBadge>
            <StatusBadge tone="accent">Action draft</StatusBadge>
          </div>
        </div>
        <div className="surface-card-raised border border-white/10 p-4">
          <h4 className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>Weekly feedback digest</h4>
          <ol className="mt-3 list-decimal space-y-3 pl-5 text-sm leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
            <li>Import reliability is the loudest issue this week. 4 reports, 2 duplicates, 1 urgent customer.</li>
            <li>Weekly digest requests are increasing. Mostly positive users asking for reporting automation.</li>
            <li>SSO is becoming a sales blocker for agencies. Low volume, high revenue impact.</li>
          </ol>
        </div>
        <JsonViewer title="Digest JSON option" value={{ top_theme: "Import reliability", reports: 4, duplicates: 2, human_review: true }} />
      </div>
    </div>
  );
}

function PriceTrackrDemo() {
  const [selector, setSelector] = useState(".price-current");
  const products = [
    { product: "Basic Plan", competitor: "AcmeTools", source: "acme.example/pricing", lastPrice: "$49", currentPrice: "$39", change: "-20%", stock: "In stock", check: "2 min ago", signal: "Alert" },
    { product: "Pro Plan", competitor: "NorthCRM", source: "north.example/pro", lastPrice: "$99", currentPrice: "$99", change: "0%", stock: "Low stock", check: "8 min ago", signal: "Watch" },
    { product: "Bundle", competitor: "Stackly", source: "stackly.example/bundle", lastPrice: "$149", currentPrice: "$119", change: "-20%", stock: "In stock", check: "14 min ago", signal: "Review" },
  ];
  const chartPoints = [
    { label: "Mon", value: 249.99 },
    { label: "Tue", value: 239.99 },
    { label: "Wed", value: 239.99 },
    { label: "Thu", value: 229.99 },
    { label: "Fri", value: 219.99 },
  ];

  return (
    <div className="grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
      <div className="min-w-0 space-y-4">
        <DemoDataTable
          rows={products}
          getRowKey={(row) => row.product}
          columns={[
            { key: "product", label: "Product" },
            { key: "competitor", label: "Competitor" },
            { key: "source", label: "Source" },
            { key: "lastPrice", label: "Last" },
            { key: "currentPrice", label: "Current" },
            { key: "change", label: "Change" },
            { key: "stock", label: "Stock" },
            { key: "check", label: "Last checked" },
            { key: "signal", label: "Signal", render: (row) => <TableStatus tone={row.signal === "Alert" ? "danger" : row.signal === "Review" ? "warning" : "neutral"}>{row.signal}</TableStatus> },
          ]}
        />
        <div className="demo-pulse surface-card-raised border border-white/10 p-4">
          <label className="text-xs font-semibold uppercase" style={{ color: "var(--color-text-secondary)" }}>Custom selector</label>
          <div className="mt-3 flex gap-2">
            <input value={selector} onChange={(event) => setSelector(event.target.value)} className="input-field" />
            <button type="button" className="btn-secondary">Test</button>
          </div>
          <p className="mt-2 text-xs" style={{ color: "var(--color-text-secondary)" }}>Demo data shown. Production checks depend on your tracked URLs and refresh limits.</p>
          <p className="mt-2 text-xs" style={{ color: "var(--color-text-secondary)" }}>Team can run checks every 10 minutes; Pro starts at hourly checks.</p>
        </div>
      </div>
      <div className="min-w-0 space-y-4">
        <PriceChart points={chartPoints} />
        <div className="surface-card-raised border border-white/10 p-4">
          <h4 className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>Why this matters</h4>
          <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
            Competitor dropped 20% in 3 days while staying in stock. Review the campaign, but do not auto-match yet because the margin floor is close.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1 2xl:grid-cols-3">
          <div className="surface-card-raised border border-white/10 p-4"><p className="text-xs text-neutral-400">Your price</p><p className="mt-1 font-semibold text-white">$99</p></div>
          <div className="surface-card-raised border border-white/10 p-4"><p className="text-xs text-neutral-400">Competitor</p><p className="mt-1 font-semibold text-white">$79</p></div>
          <div className="surface-card-raised border border-white/10 p-4"><p className="text-xs text-neutral-400">Recommended</p><p className="mt-1 font-semibold text-white">Watch, do not match</p></div>
        </div>
      </div>
    </div>
  );
}

function InvoiceFollowDemo() {
  const [selected, setSelected] = useState("INV-2041");
  const invoices = [
    { id: "INV-2041", customer: "Clara Studio", amount: "$1,200", due: "Mar 28", state: "Due soon", next: "Send reminder in 2 days" },
    { id: "INV-2038", customer: "North Labs", amount: "$800", due: "Mar 12", state: "Overdue", next: "Needs approval" },
    { id: "INV-2029", customer: "Pixel Co.", amount: "$450", due: "Feb 20", state: "Partial paid", next: "Reconcile balance" },
    { id: "INV-2022", customer: "Orbit Works", amount: "$640", due: "Feb 04", state: "Disputed", next: "Pause reminders" },
  ];
  const current = invoices.find((invoice) => invoice.id === selected) || invoices[0];
  const timeline = useMemo(() => [
    { time: "Day 0", title: "Invoice sent", description: `${current.id} for ${current.customer} sent with payment link.`, status: "sent", tone: "success" as const },
    { time: "Day 3", title: "Friendly reminder", description: "Subject: Quick reminder about invoice. Requires approval: no.", status: "polite", tone: "accent" as const },
    { time: "Day 7", title: "Firm follow-up", description: "Requires approval before sending. Pause if the client replies or disputes.", status: "review", tone: "warning" as const },
    { time: "Day 14", title: "Manual review", description: "No automatic email. Ask the owner to review before sending.", status: "manual", tone: "danger" as const },
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
            { key: "due", label: "Due date" },
            { key: "state", label: "Status", render: (row) => <TableStatus tone={row.state === "Paid" ? "success" : row.state === "Disputed" ? "danger" : row.state === "Overdue" || row.state === "Partial paid" ? "warning" : "neutral"}>{row.state}</TableStatus> },
            { key: "next", label: "Next action" },
          ]}
        />
        <div className="surface-card-raised border border-white/10 p-4">
          <h4 className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>Email preview</h4>
          <div className="mt-3 rounded-md bg-black/30 p-3 text-sm leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>
            <p className="font-semibold" style={{ color: "var(--color-text)" }}>Subject: Quick reminder about invoice {current.id}</p>
            <p className="mt-3">Hi Clara,</p>
            <p className="mt-2">Just a quick reminder that invoice {current.id} for March development work is due on Friday.</p>
            <p className="mt-2">You can view or pay it here: [payment link]</p>
            <p className="mt-2">Thanks,<br />Victor</p>
          </div>
        </div>
        <div className="surface-card-raised border border-white/10 p-4">
          <h4 className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>Follow-ups with brakes, not autopilot</h4>
          <div className="mt-3 grid gap-2 text-sm" style={{ color: "var(--color-text-secondary)" }}>
            {["Manual approval before firm reminders", "Pause reminders when a client replies", "Mark invoices as disputed or partially paid", "Sensitive client notes stay private"].map((item) => (
              <p key={item}>{item}</p>
            ))}
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
