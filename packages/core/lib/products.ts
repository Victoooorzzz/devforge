export type ProductSlug = "filecleaner" | "webhookmonitor" | "feedbacklens" | "pricetrackr" | "invoicefollow";
export type PlanSlug = "free" | "pro" | "team";

export interface ProductPlan {
  slug: PlanSlug;
  name: string;
  price: number;
  priceLabel: string;
  description: string;
  cta: string;
  highlights: string[];
  limits: string[];
}

export interface FeatureComparisonRow {
  feature: string;
  free: string;
  pro: string;
  team: string;
}

export interface ProductFAQ {
  question: string;
  answer: string;
}

export interface ProductBriefCard {
  label: string;
  title: string;
  body: string;
}

export interface ProductProofBlock {
  label: string;
  body: string;
}

export interface ProductUniqueSection {
  eyebrow: string;
  title: string;
  description: string;
  blocks: ProductProofBlock[];
  badges?: string[];
}

export interface DevForgeProduct {
  slug: ProductSlug;
  name: string;
  shortName: string;
  domain: string;
  url: string;
  dashboardPath: string;
  accentColor: string;
  status: "live" | "beta";
  category: string;
  headline: string;
  description: string;
  founderNote: string;
  proofPoint: string;
  seoTitle: string;
  seoDescription: string;
  keywords: string[];
  problem: string;
  solution: string;
  audience: string;
  briefCards: ProductBriefCard[];
  uniqueSection: ProductUniqueSection;
  featureSectionTitle: string;
  featureSectionDescription: string;
  useCaseSectionTitle: string;
  useCaseSectionDescription: string;
  pricingSectionTitle: string;
  pricingSectionDescription: string;
  comparisonSectionTitle: string;
  faqSectionTitle: string;
  relatedSectionTitle: string;
  features: string[];
  useCases: string[];
  demoTitle: string;
  demoDescription: string;
  plans: ProductPlan[];
  comparison: FeatureComparisonRow[];
  dashboardFeatures: string[];
  faq: ProductFAQ[];
}

export const PLAN_ORDER: PlanSlug[] = ["free", "pro", "team"];

const sharedPlans = (product: string, beta = false): ProductPlan[] => [
  {
    slug: "free",
    name: "Free",
    price: 0,
    priceLabel: "$0",
    description: `Try ${product} with starter limits and no credit card.`,
    cta: "Start free",
    highlights: ["No credit card", "Core workflow", "Upgrade when usage grows"],
    limits: [],
  },
  {
    slug: "pro",
    name: "Pro",
    price: 9.99,
    priceLabel: "$9.99",
    description: "For solo builders and small teams running real workflows.",
    cta: "Start Pro",
    highlights: ["Higher limits", "Advanced automation", "Production retention"],
    limits: [],
  },
  {
    slug: "team",
    name: "Team",
    price: 49,
    priceLabel: "$49",
    description: "For agencies, operators, and teams managing more volume.",
    cta: "Start Team",
    highlights: ["Team-scale limits", "Longer retention", "Expanded automation"],
    limits: [],
  },
];

const feedbackLensPlans = (): ProductPlan[] => [
  {
    slug: "free",
    name: "Free",
    price: 0,
    priceLabel: "$0",
    description: "Try FeedbackLens with starter limits and no credit card.",
    cta: "Start free",
    highlights: ["No credit card", "Manual paste and CSV import", "Upgrade when usage grows"],
    limits: [],
  },
  {
    slug: "pro",
    name: "Pro",
    price: 19,
    priceLabel: "$19",
    description: "For founders and product teams turning feedback into action every week.",
    cta: "Start Pro",
    highlights: ["Higher feedback limits", "Semantic deduplication", "Weekly digest"],
    limits: [],
  },
  {
    slug: "team",
    name: "Team",
    price: 79,
    priceLabel: "$79",
    description: "For teams managing higher feedback volume across larger import batches.",
    cta: "Start Team",
    highlights: ["Team-scale limits", "365-day history", "Higher import volume"],
    limits: [],
  },
];

function withLimits(plans: ProductPlan[], limits: Record<PlanSlug, string[]>): ProductPlan[] {
  return plans.map((plan) => ({ ...plan, limits: limits[plan.slug] }));
}

const ALL_PRODUCTS: DevForgeProduct[] = [
  {
    slug: "filecleaner",
    name: "FileCleaner",
    shortName: "FileCleaner",
    domain: "filecleaner.devforgeapp.pro",
    url: "https://filecleaner.devforgeapp.pro",
    dashboardPath: "/dashboard",
    accentColor: "#F59E0B",
    status: "live",
    category: "Data operations",
    headline: "Clean broken CSVs before they break your import.",
    description: "Fix messy headers, duplicate rows, weird encodings, empty columns, and inconsistent customer fields before they reach your database.",
    founderNote: "Built because \"just fix the spreadsheet real quick\" is where afternoons go to die.",
    proofPoint: "Demo data shown. Production cleanup uses your uploaded file, preserves the original, and keeps a change report for review.",
    seoTitle: "FileCleaner - CSV and Excel cleaning tool by DevForge",
    seoDescription: "Clean CSV, Excel, JSON, and image files with normalization, schema checks, anomaly detection, fuzzy duplicate detection, and export-ready reports.",
    keywords: ["data cleaning tool", "CSV cleaner", "Excel cleaning tool", "file cleanup", "schema validation"],
    problem: "Messy exports create duplicate rows, invalid emails, inconsistent dates, empty totals, and silent analytics errors.",
    solution: "Preview the file, normalize headers and formats, group duplicates, flag invalid rows, then export only after review.",
    audience: "Data analysts, operators, agencies, founders, and support teams importing customer, invoice, or marketplace files.",
    briefCards: [
      {
        label: "Messy headers",
        title: "\"Nombre Cliente\" -> customer_name",
        body: "\"Monto S/.\" -> amount_pen, \"fecha pago\" -> payment_date, and odd casing mapped before import.",
      },
      {
        label: "Duplicate rows",
        title: "Repeated emails, invoice IDs, SKUs, and customer keys",
        body: "Duplicates are grouped for review instead of silently creating bad records.",
      },
      {
        label: "Audit report",
        title: "Changed, dropped, needs review",
        body: "See every normalized field, every removed row, and the leftovers that still need a human.",
      },
    ],
    uniqueSection: {
      eyebrow: "Before / after",
      title: "Before / After file cleanup",
      description: "The demo intentionally shows ugly file data: broken emails, duplicate rows, mixed dates, and values that should not be imported blindly.",
      blocks: [
        {
          label: "Before",
          body: "Nombre Cliente | E-mail | monto S/. | fecha pago | Estado\nACME SAC | test@ | S/ 1,200 | 12-31-24 | pagadoo\nACME SAC | test@ | 1200 | 31/12/2024 | pagado\n<empty> | NULL | -- | soon | pending",
        },
        {
          label: "After",
          body: "customer_name | email | amount_pen | payment_date | status\nACME SAC | test@acme.pe | 1200.00 | 2024-12-31 | paid",
        },
      ],
      badges: ["3 duplicate rows found", "2 invalid emails", "1 date format normalized", "4 headers renamed"],
    },
    featureSectionTitle: "From broken export to safe import",
    featureSectionDescription: "Public demos stay safe, but the workflow mirrors production cleanup: preview, normalize, dedupe, validate, approve, export.",
    useCaseSectionTitle: "Files that usually ruin an afternoon",
    useCaseSectionDescription: "FileCleaner is intentionally narrow: it catches the spreadsheet mess that appears right before data enters a real system.",
    pricingSectionTitle: "What each cleanup tier actually unlocks",
    pricingSectionDescription: "Start with Free for small files, move to Pro for fuzzy matching and validation, or use Team when batch volume and retention matter.",
    comparisonSectionTitle: "Cleanup limits by file risk",
    faqSectionTitle: "Before you upload a file",
    relatedSectionTitle: "Works well with these DevForge tools",
    features: [
      "Header mapping",
      "Duplicate detection",
      "Format normalization",
      "Review before export",
      "Cleanup report",
      "EXIF and utility cleanup",
    ],
    useCases: [
      "HubSpot exports with duplicate leads",
      "Marketplace CSVs with broken product fields",
      "Invoice spreadsheets with mixed date formats",
      "Customer lists with invalid emails",
      "Legacy Excel files before database import",
    ],
    demoTitle: "Dirty files waiting for review",
    demoDescription: "Preview realistic files with invalid emails, mixed dates, duplicate customers, empty totals, suggested fixes, and statuses that still need approval.",
    plans: withLimits(sharedPlans("FileCleaner"), {
      free: ["10 MB max file size", "Basic cleaning", "1 active normalization rule", "EXIF cleanup up to 5 MB", "24h retention", "CSV/XLSX/JSON export"],
      pro: ["100 MB max file size", "Expanded normalization", "Anomaly detection", "Fuzzy duplicates up to 1,000 rows", "5 schema rules per file", "48h retention", "10-file sequential batch"],
      team: ["500 MB max file size", "Fuzzy duplicates up to 10,000 rows", "EXIF cleanup up to 150 MB", "7 day retention", "Parallel batch processing", "Expanded rules and full report"],
    }),
    comparison: [
      { feature: "File size", free: "10 MB", pro: "100 MB", team: "500 MB" },
      { feature: "Normalization", free: "1 rule", pro: "Expanded rules", team: "Expanded rules" },
      { feature: "Anomaly detection", free: "No", pro: "Yes", team: "Yes" },
      { feature: "Fuzzy duplicates", free: "No", pro: "1,000 rows", team: "10,000 rows" },
      { feature: "Schema validation", free: "No", pro: "5 rules/file", team: "Expanded" },
      { feature: "Retention", free: "24 hours", pro: "48 hours", team: "7 days" },
      { feature: "Batch", free: "No", pro: "10 sequential", team: "Parallel" },
    ],
    dashboardFeatures: ["Upload and preview", "Cleaning rules", "Schema validation", "Anomaly view", "Fuzzy duplicates", "Report exports", "Usage quota"],
    faq: [
      { question: "Can I review changes before exporting?", answer: "Yes. FileCleaner previews changed headers, normalized values, duplicates, and invalid rows before you download the cleaned file." },
      { question: "Does FileCleaner modify my original file?", answer: "No. The original stays intact; exports are generated as cleaned copies with a change report." },
      { question: "What happens with invalid rows?", answer: "Invalid rows are flagged for review, not silently deleted. You decide whether to fix, exclude, or export them." },
      { question: "Can it detect duplicate customers by email or ID?", answer: "Yes. Exact and fuzzy duplicate detection can use emails, invoice IDs, SKUs, customer keys, or configured columns." },
      { question: "Can I save cleanup rules for future files?", answer: "Saved rules are part of the paid workflow so recurring exports can reuse the same mappings and validations." },
    ],
  },
  {
    slug: "webhookmonitor",
    name: "Webhook Monitor",
    shortName: "Webhook Monitor",
    domain: "webhookmonitor.devforgeapp.pro",
    url: "https://webhookmonitor.devforgeapp.pro",
    dashboardPath: "/dashboard",
    accentColor: "#8B5CF6",
    status: "live",
    category: "Developer operations",
    headline: "Replay failed webhooks with the full evidence attached.",
    description: "Capture payloads, headers, status codes, latency, attempts, and responses so failed deliveries stop becoming archaeology.",
    founderNote: "Built after debugging webhook retries with twelve tabs open and zero useful logs.",
    proofPoint: "Replay preserves headers, body, status code, latency, attempt history, and masked sensitive fields.",
    seoTitle: "Webhook Monitor - Webhook debugging tool by DevForge",
    seoDescription: "Inspect, replay, diff, search, export, and validate webhooks with signature validation, forwarding rules, and automatic retry support.",
    keywords: ["webhook debugging tool", "webhook monitor", "webhook replay", "webhook diff", "signature validation"],
    problem: "Webhook failures disappear into logs, retries are hard to reproduce, and payload changes hide inside large JSON bodies.",
    solution: "Capture the full request, inspect payload and headers, verify signatures, replay one event, and keep the failure timeline attached.",
    audience: "Backend developers, API integrators, agencies, SaaS founders, and small teams shipping payment or automation flows.",
    briefCards: [
      {
        label: "Captured request",
        title: "POST /webhooks/stripe 500 842ms",
        body: "Event type, provider, endpoint, attempt number, signature status, and response body stay together.",
      },
      {
        label: "Replay context",
        title: "Original headers and body preserved",
        body: "Replay a single event without asking the provider to resend the whole batch.",
      },
      {
        label: "Sensitive data",
        title: "Mask fields before teammates inspect payloads",
        body: "Authorization, cookies, tokens, API keys, and configured payload paths stay hidden in previews.",
      },
    ],
    uniqueSection: {
      eyebrow: "Incident autopsy",
      title: "Failed webhook autopsy",
      description: "A failed delivery is useful only when the request, failure, and replay result can be read in one place.",
      blocks: [
        { label: "Request", body: "POST /webhooks/stripe\nEvent: invoice.payment_failed\nSignature: valid\nAttempt: 1 of 3" },
        { label: "Failure", body: "Status: 500\nLatency: 842ms\nError: Missing customer_id\nResponse: Cannot read property 'customer_id' of undefined" },
        { label: "Replay result", body: "Status: 200\nLatency: 118ms\nFixed after mapping customer_id from metadata." },
      ],
      badges: ["Replay this event", "Copy cURL", "View headers", "Mask sensitive fields"],
    },
    featureSectionTitle: "Every failed delivery, explained",
    featureSectionDescription: "The product is built around evidence: payload, headers, response, attempt timeline, signature state, and replay result.",
    useCaseSectionTitle: "Incidents worth keeping evidence for",
    useCaseSectionDescription: "Webhook Monitor is for integration failures where one missing field or timeout can break payment, order, or automation flows.",
    pricingSectionTitle: "What each webhook tier actually unlocks",
    pricingSectionDescription: "Free captures a small endpoint, Pro adds replay and validation, and Team raises event volume, payload size, and retention.",
    comparisonSectionTitle: "Webhook limits by incident volume",
    faqSectionTitle: "Before you capture production webhooks",
    relatedSectionTitle: "Pair webhook evidence with these tools",
    features: ["Payload capture", "Replay safely", "Failure timeline", "Signature checks", "Endpoint health", "Export cURL/Postman"],
    useCases: [
      "Stripe invoice webhooks failing after a deploy",
      "GitHub events timing out during CI spikes",
      "Shopify order webhooks missing customer metadata",
      "Internal webhook consumers returning 500s",
      "Retrying a batch after fixing a parser bug",
    ],
    demoTitle: "Webhook incident replay demo",
    demoDescription: "Inspect failed events with timestamps, payload, headers, response body, retry history, signature status, and a replay result.",
    plans: withLimits(sharedPlans("Webhook Monitor"), {
      free: ["1 endpoint", "100 events/day", "7 days log retention", "256 KB max payload", "Encryption", "cURL export"],
      pro: ["10 endpoints", "10,000 events/day", "30 days retention", "1 MB max payload", "Signature validation", "3 forwarding rules", "Manual replay", "Diffing and advanced search", "cURL + Postman export"],
      team: ["50 endpoints", "50,000 events/day", "90 days retention", "5 MB max payload", "Expanded forwarding rules", "Manual replay + automatic retries", "Diffing and advanced search"],
    }),
    comparison: [
      { feature: "Endpoints", free: "1", pro: "10", team: "50" },
      { feature: "Events/day", free: "100", pro: "10,000", team: "50,000" },
      { feature: "Retention", free: "7 days", pro: "30 days", team: "90 days" },
      { feature: "Payload size", free: "256 KB", pro: "1 MB", team: "5 MB" },
      { feature: "Signature validation", free: "No", pro: "Yes", team: "Yes" },
      { feature: "Forwarding", free: "No", pro: "3 rules", team: "Expanded" },
      { feature: "Replay", free: "No", pro: "Manual", team: "Manual + auto retry" },
    ],
    dashboardFeatures: ["Endpoint list", "Event table", "Payload viewer", "Headers viewer", "Replay", "Diff viewer", "Forwarding rules", "Signature state", "Usage quota"],
    faq: [
      { question: "Does replay preserve the original headers?", answer: "Yes. Replay keeps the original headers, body, endpoint context, status history, and timing metadata visible." },
      { question: "Can I filter failed webhooks by endpoint or status code?", answer: "Yes. Paid workflows support filtering by endpoint, provider, status code, event type, and replay state." },
      { question: "Do you store request bodies?", answer: "Webhook bodies are stored according to plan retention so incidents can be inspected and replayed later." },
      { question: "Can I mask sensitive fields?", answer: "Yes. Header masking is built in, and sensitive payload fields can be kept out of shared previews." },
      { question: "Can I replay one event without replaying the full batch?", answer: "Yes. Manual replay is designed around one event at a time, with batch retries reserved for controlled paid workflows." },
    ],
  },
  {
    slug: "feedbacklens",
    name: "FeedbackLens",
    shortName: "FeedbackLens",
    domain: "feedbacklens.devforgeapp.pro",
    url: "https://feedbacklens.devforgeapp.pro",
    dashboardPath: "/dashboard",
    accentColor: "#10B981",
    status: "beta",
    category: "Product intelligence",
    headline: "Turn messy feedback into roadmap signals you can defend.",
    description: "Turn pasted feedback, CSV imports, forwarded messages, and sales notes into themes, duplicates, urgency, and next actions your team can actually discuss.",
    founderNote: "Built because \"users are asking for this\" should come with receipts.",
    proofPoint: "Demo feedback is intentionally imperfect; production digests keep raw messages linked to every theme and duplicate cluster.",
    seoTitle: "FeedbackLens - Customer feedback analysis tool by DevForge",
    seoDescription: "Analyze pasted feedback and CSV imports with sentiment, spam detection, semantic deduplication, weekly digests, and exportable results.",
    keywords: ["customer feedback analysis", "product feedback tool", "sentiment analysis", "semantic deduplication", "weekly feedback digest"],
    problem: "Important bugs and churn signals get buried across support messages, CSV exports, sales notes, and product reviews.",
    solution: "Collect raw feedback, cluster themes, link duplicates, show confidence, surface ambiguity, and turn the loudest pattern into action.",
    audience: "Product managers, founders, support leads, developer advocates, and teams building from user feedback.",
    briefCards: [
      {
        label: "Raw messages",
        title: "\"csv import broke again w/ accents...\"",
        body: "Typos, sarcasm, half-context, and messy customer language stay visible.",
      },
      {
        label: "Confidence",
        title: "Human review needed when the model is unsure",
        body: "Low-confidence or ambiguous classifications are marked instead of pretending every label is perfect.",
      },
      {
        label: "Receipts",
        title: "Themes link back to every imported message and note",
        body: "Roadmap meetings get source evidence instead of a single generated summary.",
      },
    ],
    uniqueSection: {
      eyebrow: "Duplicate cluster",
      title: "Duplicate cluster breakdown",
      description: "Different people rarely describe the same bug the same way. FeedbackLens keeps the raw sources attached to the shared pattern.",
      blocks: [
        { label: "Cluster", body: "CSV import fails with accented headers" },
        { label: "Inputs", body: "CSV import: accented headers fail\nForwarded message: same import bug as ticket 21\nSales note: client file from Mexico breaks on upload\nSupport note: encoding issue with accented names" },
        { label: "Detected pattern", body: "Likely UTF-8 normalization issue during header mapping.\nSuggested action: create one bug ticket, link duplicates, prioritize before next import release." },
      ],
      badges: ["4 reports", "2 duplicates", "1 urgent customer", "Human review visible"],
    },
    featureSectionTitle: "From noisy inbox to roadmap evidence",
    featureSectionDescription: "The workflow preserves raw feedback while clustering repeated themes, showing confidence, and exposing what still needs review.",
    useCaseSectionTitle: "When feedback sounds loud but needs proof",
    useCaseSectionDescription: "FeedbackLens is for teams that need to turn scattered messages into defensible roadmap evidence without losing the original wording.",
    pricingSectionTitle: "What each feedback tier actually unlocks",
    pricingSectionDescription: "Free handles small feedback batches, Pro adds higher limits and digests, and Team keeps longer history across higher feedback volume.",
    comparisonSectionTitle: "Feedback limits by source volume",
    faqSectionTitle: "Before you trust a feedback cluster",
    relatedSectionTitle: "Pair feedback evidence with these tools",
    features: ["Theme clustering", "Duplicate detection", "Urgency scoring", "Digest generation", "Human review", "CSV import and export"],
    useCases: [
      "Support teams drowning in repeated bug reports",
      "Founders turning sales calls into product evidence",
      "Product managers preparing roadmap meetings",
      "Developers grouping imported bug reports before a sprint",
      "Agencies collecting client requests across inboxes",
    ],
    demoTitle: "Messy feedback triage demo",
    demoDescription: "Review imperfect messages from pasted notes, CSV imports, forwarded email, and sales notes with confidence, duplicates, human-review flags, and a digest people can discuss.",
    plans: withLimits(feedbackLensPlans(), {
      free: ["100 feedback items/month", "Manual paste and CSV import", "30 days retention", "Sentiment analysis", "Spam detection"],
      pro: ["5,000 feedback items/month", "Bulk CSV and API import", "180 days retention", "Semantic deduplication", "Weekly digest", "Attachment processing"],
      team: ["25,000 feedback items/month", "Higher import volume", "365 days retention", "All Pro features included"],
    }),
    comparison: [
      { feature: "Feedback/month", free: "100", pro: "5,000", team: "25,000" },
      { feature: "CSV import", free: "Yes", pro: "Bulk", team: "Bulk" },
      { feature: "API import", free: "No", pro: "Yes", team: "Yes" },
      { feature: "Retention", free: "30 days", pro: "180 days", team: "365 days" },
      { feature: "Semantic dedupe", free: "No", pro: "Yes", team: "Yes" },
      { feature: "Weekly digest", free: "No", pro: "Email", team: "Email" },
    ],
    dashboardFeatures: ["Feedback inbox", "Manual and CSV import", "Sentiment overview", "Topic clusters", "Duplicate groups", "Spam labels", "Reply drafts", "Weekly digest", "Usage quota"],
    faq: [
      { question: "Can I review or correct classifications?", answer: "Yes. FeedbackLens keeps low-confidence items visible so a human can correct themes, urgency, and duplicate links." },
      { question: "Does FeedbackLens show confidence scores?", answer: "Yes. Confidence is shown in the triage view so uncertain feedback does not look more precise than it is." },
      { question: "Can it detect duplicates across different imports?", answer: "Yes. Pro and Team can link repeated complaints across pasted notes, CSV batches, forwarded messages, and API imports." },
      { question: "Can I export the analyzed feedback?", answer: "Yes. The dashboard exports analyzed feedback as CSV, JSON, or XLSX for use in the tools your team already has." },
      { question: "What happens when feedback is ambiguous?", answer: "Ambiguous feedback is marked for review instead of being buried inside a confident-looking summary." },
    ],
  },
  {
    slug: "pricetrackr",
    name: "PriceTrackr",
    shortName: "PriceTrackr",
    domain: "pricetrackr.devforgeapp.pro",
    url: "https://pricetrackr.devforgeapp.pro",
    dashboardPath: "/dashboard",
    accentColor: "#EF4444",
    status: "live",
    category: "Commerce intelligence",
    headline: "Catch competitor price drops before they eat your margin.",
    description: "Track prices, stock changes, discount patterns, and alert-worthy movements across competitor pages without living inside spreadsheets.",
    founderNote: "Built for teams that check competitor prices often enough to hate doing it manually.",
    proofPoint: "Demo data shown. Production checks depend on your tracked URLs, refresh limits, selectors, and alert thresholds.",
    seoTitle: "PriceTrackr - Price monitoring tool by DevForge",
    seoDescription: "Monitor product URLs, price drops, stock changes, history charts, custom selectors, and email or webhook alerts for ecommerce teams.",
    keywords: ["price monitoring tool", "price tracker", "competitor price monitoring", "product URL tracker", "price history chart"],
    problem: "Manual competitor checks are slow, inconsistent, and miss price drops while stock and margins are moving.",
    solution: "Track URLs, price history, stock state, thresholds, selectors, and decision notes from one watchlist.",
    audience: "Ecommerce operators, agencies, founders, deal trackers, and market researchers.",
    briefCards: [
      {
        label: "Price movement",
        title: "AcmeTools $49 -> $39 in one check",
        body: "Watch old price, current price, percent change, source URL, stock, and last checked timestamp together.",
      },
      {
        label: "Margin context",
        title: "Do not auto-match when stock is low",
        body: "A price drop is not always a command. Add margin floor and stock context before reacting.",
      },
      {
        label: "Alert evidence",
        title: "Threshold crossed at 2 min ago",
        body: "Production alerts include the tracked URL, selector state, currency, and change history.",
      },
    ],
    uniqueSection: {
      eyebrow: "Movement timeline",
      title: "Competitor price movement timeline",
      description: "The important part is not the line going down. It is the sequence of changes and the decision your team should make.",
      blocks: [
        { label: "Monday", body: "Competitor A: $99 -> $89\nSignal: discount started" },
        { label: "Wednesday", body: "Competitor A: $89 -> $79\nSignal: second drop in 72h" },
        { label: "Friday", body: "Competitor A: $79, stock low\nSuggested action: review campaign, do not auto-match yet. Stock is low and margin risk is high." },
      ],
      badges: ["Your price: $99", "Competitor: $79", "Margin floor: $74", "Recommended: Watch"],
    },
    featureSectionTitle: "From price change to pricing decision",
    featureSectionDescription: "PriceTrackr connects price, stock, source URL, history, threshold, and decision notes so a drop becomes a choice, not panic.",
    useCaseSectionTitle: "Markets where one price move matters",
    useCaseSectionDescription: "Use it when competitor pages, stock shifts, and discounts can affect margins before someone checks the spreadsheet.",
    pricingSectionTitle: "What each tracking tier actually unlocks",
    pricingSectionDescription: "Free checks a few URLs slowly, Pro adds hourly checks and webhook alerts, and Team supports high-volume, frequent monitoring.",
    comparisonSectionTitle: "Tracking limits by refresh pressure",
    faqSectionTitle: "Before you trust a price alert",
    relatedSectionTitle: "Works well with these operations tools",
    features: ["Tracked URLs", "Stock shifts", "Change history", "Alert rules", "Decision notes", "Custom selector preview"],
    useCases: [
      "SaaS teams tracking competitor plan changes",
      "Ecommerce teams watching seasonal discounts",
      "Agencies monitoring client competitors",
      "Founders validating pricing experiments",
      "Operators checking stock-driven price drops",
    ],
    demoTitle: "Price drop watchlist demo",
    demoDescription: "Browse simulated competitors with source URLs, old/current prices, stock, last checked timestamps, alert signals, and margin context.",
    plans: withLimits(sharedPlans("PriceTrackr"), {
      free: ["5 active URL trackers", "Every 24 hours", "30 days price history", "Delayed email alerts", "SVG charts", "Basic User-Agent rotation"],
      pro: ["100 active URL trackers", "Every 1 hour", "180 days price history", "Instant email alerts", "Webhook alerts", "Advanced User-Agent and proxy rotation", "Custom selectors"],
      team: ["500 active URL trackers", "Every 10 minutes", "365 days price history", "Instant alerts", "Premium proxy rotation", "Custom selectors"],
    }),
    comparison: [
      { feature: "Active trackers", free: "5", pro: "100", team: "500" },
      { feature: "Frequency", free: "24 hours", pro: "1 hour", team: "10 minutes" },
      { feature: "History", free: "30 days", pro: "180 days", team: "365 days" },
      { feature: "Email alerts", free: "Delayed", pro: "Instant", team: "Instant" },
      { feature: "Webhook alerts", free: "No", pro: "Yes", team: "Yes" },
      { feature: "Proxy rotation", free: "No", pro: "Advanced", team: "Premium" },
      { feature: "Custom selectors", free: "No", pro: "Yes", team: "Yes" },
    ],
    dashboardFeatures: ["Tracker list", "Add tracker flow", "History chart", "Last checked status", "Error pause state", "Alert settings", "Webhook settings", "Custom selectors", "Usage quota"],
    faq: [
      { question: "How often are prices checked?", answer: "Free runs every 24 hours, Pro every hour, and Team every 10 minutes." },
      { question: "Can I track pages that require JavaScript?", answer: "Some pages need custom selectors or advanced extraction. The selector preview helps catch pages that require extra setup." },
      { question: "Can I set alert thresholds by percentage?", answer: "Yes. Pro and Team workflows can trigger alerts when movement crosses configured percentage or price thresholds." },
      { question: "Can I track stock changes as well as price?", answer: "Yes. Stock state is tracked next to price so teams can avoid reacting to discounts caused by low inventory." },
      { question: "Do you support multiple currencies?", answer: "Tracked values can include currency context. Teams should keep comparisons grouped by currency for clean decisioning." },
    ],
  },
  {
    slug: "invoicefollow",
    name: "InvoiceFollow",
    shortName: "InvoiceFollow",
    domain: "invoicefollow.devforgeapp.pro",
    url: "https://invoicefollow.devforgeapp.pro",
    dashboardPath: "/dashboard",
    accentColor: "#6366F1",
    status: "beta",
    category: "Cash operations",
    headline: "Send polite invoice follow-ups before unpaid work gets awkward.",
    description: "Schedule reminders, track invoice status, review messages before they send, and record payment progress without chasing every client by hand.",
    founderNote: "Built because unpaid invoices should not live rent-free in your head.",
    proofPoint: "Manual approval is available before firm reminders, and reminders can pause when a client replies or disputes an invoice.",
    seoTitle: "InvoiceFollow - Automated invoice reminders by DevForge",
    seoDescription: "Invoice follow up software for overdue invoices, reminder schedules, reply classification, partial payments, manual approvals, and weekly financial digests.",
    keywords: ["invoice follow up software", "automated invoice reminders", "invoice collection emails", "partial payment tracking", "invoice approval workflow"],
    problem: "Late payments cost time, follow-up gets emotional, and replies, disputes, partial payments, or confirmations land in too many places.",
    solution: "Import invoices, preview reminders, require approval for firm follow-ups, pause on replies, and record payment state.",
    audience: "Freelancers, agencies, consultants, founders, and small teams that need disciplined cash collection without awkward manual chasing.",
    briefCards: [
      {
        label: "Reminder preview",
        title: "Subject, tone, payment link, approval state",
        body: "Review the exact email before it leaves your workspace.",
      },
      {
        label: "Collection brakes",
        title: "Pause on reply, dispute, or partial payment",
        body: "Invoice automation should stop when a human conversation starts.",
      },
      {
        label: "Cash context",
        title: "Viewed, due soon, overdue, partial paid, disputed",
        body: "The status board shows awkward money states without pretending everything is binary.",
      },
    ],
    uniqueSection: {
      eyebrow: "Reminder sequence",
      title: "Reminder email sequence",
      description: "Collections need tone and brakes. The sequence starts polite, asks for approval when it becomes firm, and stops before automation gets weird.",
      blocks: [
        { label: "Day 0", body: "Invoice sent\nSubject: Invoice #INV-2041 for March development work\nTone: neutral\nStatus: sent" },
        { label: "Day 3", body: "Friendly reminder\nSubject: Quick reminder about invoice #INV-2041\nTone: polite\nRequires approval: no" },
        { label: "Day 7", body: "Firm follow-up\nSubject: Follow-up on overdue invoice #INV-2041\nTone: firm but professional\nRequires approval: yes" },
        { label: "Day 14", body: "Manual review\nNo automatic email. Ask the owner to review before sending." },
      ],
      badges: ["Manual approval", "Pause when client replies", "Partial payments", "Disputed invoices"],
    },
    featureSectionTitle: "From sent invoice to settled payment",
    featureSectionDescription: "InvoiceFollow keeps reminders, replies, approval gates, partial payments, and payment links visible before automation sends anything sensitive.",
    useCaseSectionTitle: "Follow-ups that need tact, not autopilot",
    useCaseSectionDescription: "Use it for invoices that need a reminder workflow but still require human judgment around tone, disputes, and partial balances.",
    pricingSectionTitle: "What each invoice tier actually unlocks",
    pricingSectionDescription: "Free covers a few active invoices, Pro adds higher limits and workflow tools, and Team adds seats, volume, and longer retention.",
    comparisonSectionTitle: "Invoice limits by collection volume",
    faqSectionTitle: "Before you automate a reminder",
    relatedSectionTitle: "Pair cash follow-up with these tools",
    features: ["Reminder schedules", "Message preview", "Client replies", "Partial payments", "Approval workflow", "Bulk import"],
    useCases: [
      "Freelance developers billing monthly retainers",
      "Design studios waiting on final project payments",
      "Agencies collecting deposits before kickoff",
      "Consultants handling partial payments",
      "Small teams that need reminders but not aggressive collections",
    ],
    demoTitle: "Receivables recovery demo",
    demoDescription: "Walk through invoices with viewed, due soon, overdue, partial paid, disputed, and needs-review states plus a realistic email preview.",
    plans: withLimits(sharedPlans("InvoiceFollow", true), {
      free: ["5 active invoices", "25 collection emails/month", "10 NLP reply analyses/month", "1 workspace user", "30 days retention"],
      pro: ["50 active invoices", "500 collection emails/month", "200 NLP reply analyses/month", "90 days retention", "Weekly digest", "API access", "Bulk import", "Custom templates"],
      team: ["200 active invoices", "2,000 collection emails/month", "1,000 NLP reply analyses/month", "5 workspace users", "365 days retention", "Weekly digest", "API access", "Bulk import", "Custom templates"],
    }),
    comparison: [
      { feature: "Active invoices", free: "5", pro: "50", team: "200" },
      { feature: "Emails/month", free: "25", pro: "500", team: "2,000" },
      { feature: "NLP analyses/month", free: "10", pro: "200", team: "1,000" },
      { feature: "Workspace users", free: "1", pro: "1", team: "5" },
      { feature: "Retention", free: "30 days", pro: "90 days", team: "365 days" },
      { feature: "Bulk import/API", free: "Limited/no", pro: "Yes", team: "Yes" },
    ],
    dashboardFeatures: ["Invoice list", "Status board", "Add/import flow", "Customer detail", "Reminder schedule", "Email history", "Reply classification", "Partial payments", "Manual approvals", "Weekly digest", "Usage quota"],
    faq: [
      { question: "Can I approve reminders before they are sent?", answer: "Yes. Firm reminders can require manual approval before sending, and sensitive invoices can stay out of automation." },
      { question: "Can reminders pause when a client replies?", answer: "Yes. Client replies, disputes, and payment confirmations can pause the next scheduled reminder for manual review." },
      { question: "Can I customize the tone of each email?", answer: "Yes. Reminder previews show subject, tone, payment link, and approval state before messages go out." },
      { question: "Does InvoiceFollow support partial payments?", answer: "Yes. Partial paid status and remaining-balance notes are part of the recovery workflow." },
      { question: "Can I mark an invoice as disputed?", answer: "Yes. Disputed invoices can pause reminders and stay visible in the status board." },
      { question: "How can I add existing invoices?", answer: "Add them with the tracking form or import a validated CSV, then review the reminder schedule before anything is sent." },
    ],
  },
];

export const DEVFORGE_PRODUCTS: DevForgeProduct[] = ALL_PRODUCTS.filter(p => p.slug !== "filecleaner");

export const DEVFORGE_SUITE = {
  name: "DevForge",
  domain: "devforgeapp.pro",
  url: "https://devforgeapp.pro",
  headline: "Four small tools for the ugly work behind clean software.",
  description: "Replay failed webhooks, track competitor prices, organize feedback, and chase invoices without building four internal tools from scratch.",
  audience: "Built for small teams that want practical tools without enterprise theater.",
  benefits: [
    "DevForge is a compact product suite for the operational chores developers usually postpone.",
    "Each tool solves one painful workflow: broken webhooks, price changes, noisy feedback, or unpaid invoices.",
    "Same account, same billing logic, same dark little workshop.",
  ],
};

export function getProduct(slug: ProductSlug): DevForgeProduct {
  const product = ALL_PRODUCTS.find((item) => item.slug === slug);
  if (!product) {
    throw new Error(`Unknown DevForge product: ${slug}`);
  }
  return product;
}

export function getProductByDomain(domain: string): DevForgeProduct | undefined {
  return ALL_PRODUCTS.find((product) => product.domain === domain);
}
