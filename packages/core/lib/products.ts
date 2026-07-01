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
  seoTitle: string;
  seoDescription: string;
  keywords: string[];
  problem: string;
  solution: string;
  audience: string;
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
    highlights: ["No credit card", "Manual + email sources", "Upgrade when usage grows"],
    limits: [],
  },
  {
    slug: "pro",
    name: "Pro",
    price: 19,
    priceLabel: "$19",
    description: "For founders and product teams turning feedback into action every week.",
    cta: "Start Pro",
    highlights: ["Higher source limits", "GitHub issue action", "Weekly digest"],
    limits: [],
  },
  {
    slug: "team",
    name: "Team",
    price: 79,
    priceLabel: "$79",
    description: "For teams managing higher feedback volume across more channels.",
    cta: "Start Team",
    highlights: ["Team-scale limits", "365-day history", "Expanded source coverage"],
    limits: [],
  },
];

function withLimits(plans: ProductPlan[], limits: Record<PlanSlug, string[]>): ProductPlan[] {
  return plans.map((plan) => ({ ...plan, limits: limits[plan.slug] }));
}

export const DEVFORGE_PRODUCTS: DevForgeProduct[] = [
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
    headline: "Clean CSV, Excel, JSON, images, and messy exports before they break your workflow.",
    description: "FileCleaner turns dirty spreadsheets and bulky files into clean, validated outputs with reports your team can trust.",
    seoTitle: "FileCleaner - CSV and Excel cleaning tool by DevForge",
    seoDescription: "Clean CSV, Excel, JSON, and image files with normalization, schema checks, anomaly detection, fuzzy duplicate detection, and export-ready reports.",
    keywords: ["data cleaning tool", "CSV cleaner", "Excel cleaning tool", "file cleanup", "schema validation"],
    problem: "Messy exports create duplicate rows, invalid emails, inconsistent phones, and silent analytics errors.",
    solution: "Run cleaning, normalization, fuzzy matching, schema validation, anomaly checks, and clean exports from one dashboard.",
    audience: "Data analysts, operators, agencies, founders, and support teams that receive messy customer or revenue files.",
    features: [
      "Preview dirty files before processing",
      "Normalize phone, country, currency, and date columns",
      "Find exact and fuzzy duplicates",
      "Validate schema rules and flag anomaly outliers",
      "Strip EXIF metadata and convert image/PDF utility files",
      "Export CSV, XLSX, or JSON with a cleaning report",
    ],
    useCases: ["Clean CRM exports", "Prepare billing imports", "Audit partner CSVs", "Remove metadata before sharing assets"],
    demoTitle: "Dirty customer file cleaning demo",
    demoDescription: "Run a simulated import and watch invalid emails, duplicate rows, phone formats, dates, fuzzy matches, and outliers get flagged.",
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
      { question: "Does FileCleaner store my files forever?", answer: "No. Retention follows your plan: 24 hours on Free, 48 hours on Pro, and 7 days on Team." },
      { question: "Can I export cleaned files?", answer: "Yes. CSV, XLSX, and JSON exports are available across plans." },
      { question: "What is locked on Free?", answer: "Fuzzy matching, anomaly detection, schema validation, larger utility files, and batch processing require Pro or Team." },
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
    headline: "Debug, replay, diff, validate, and forward webhooks without guessing.",
    description: "Webhook Monitor captures payloads, masks sensitive data, validates signatures, compares payloads, and retries failed deliveries.",
    seoTitle: "Webhook Monitor - Webhook debugging tool by DevForge",
    seoDescription: "Inspect, replay, diff, search, export, and validate webhooks with signature validation, forwarding rules, and automatic retry support.",
    keywords: ["webhook debugging tool", "webhook monitor", "webhook replay", "webhook diff", "signature validation"],
    problem: "Webhook failures disappear into logs, retries are hard to reproduce, and payload changes are painful to compare.",
    solution: "Create endpoints, inspect events, search JSON, replay payloads, validate signatures, and forward requests with retry controls.",
    audience: "Backend developers, API integrators, agencies, SaaS founders, and small teams shipping payment or automation flows.",
    features: ["Endpoint management", "Event table and JSON viewer", "Headers viewer", "Replay and retry", "Payload diffing", "Forwarding rules", "Signature validation", "Export cURL/Postman"],
    useCases: ["Debug Stripe/Polar events", "Replay failed Shopify hooks", "Compare payload versions", "Forward production hooks to staging"],
    demoTitle: "Webhook incident replay demo",
    demoDescription: "Inspect simulated webhook events, search payloads, view headers, replay a request, compare diffs, and see Free-plan locked features.",
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
      { question: "Can I use this with Stripe or Polar?", answer: "Yes. The monitor is provider-agnostic and includes signature validation patterns for common webhook providers." },
      { question: "Does Free include replay?", answer: "No. Free is for capture and basic inspection. Replay, diffing, forwarding, and advanced search start on Pro." },
      { question: "Are sensitive headers exposed?", answer: "Dashboard previews mask authorization, cookie, API key, token, secret, and signature-style headers." },
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
    headline: "Turn noisy customer feedback into themes, urgency, duplicates, and next actions.",
    description: "FeedbackLens ingests feedback from multiple sources, labels sentiment and spam, groups repeats, and drafts action-ready summaries.",
    seoTitle: "FeedbackLens - Customer feedback analysis tool by DevForge",
    seoDescription: "Analyze product feedback from email, GitHub, Canny, Reddit, and X/Twitter with sentiment, spam detection, semantic dedupe, weekly digests, and GitHub Issues.",
    keywords: ["customer feedback analysis", "product feedback tool", "sentiment analysis", "semantic deduplication", "weekly feedback digest"],
    problem: "Important bugs and churn signals get buried across support inboxes, GitHub, Reddit, Canny, and social channels.",
    solution: "Collect feedback, classify sentiment, detect spam, group duplicates, surface clusters, draft replies, and create GitHub issues.",
    audience: "Product managers, founders, support leads, developer advocates, and teams building from user feedback.",
    features: ["Manual and source ingestion", "Sentiment and urgency labels", "Spam detection", "Semantic deduplication", "Topic clusters", "GitHub Issue action", "Weekly digest", "Attachment processing"],
    useCases: ["Summarize support tickets", "Detect repeated bugs", "Prioritize roadmap themes", "Turn feedback into GitHub issues"],
    demoTitle: "Feedback triage inbox demo",
    demoDescription: "Review simulated feedback from Email, GitHub, Canny, Reddit, and X/Twitter with sentiment, spam, duplicate groups, clusters, and a weekly digest.",
    plans: withLimits(feedbackLensPlans(), {
      free: ["100 feedback items/month", "2 active sources", "Manual + email channels", "30 days retention", "Sentiment analysis", "Spam detection"],
      pro: ["5,000 feedback items/month", "10 active sources", "All channels", "180 days retention", "Semantic deduplication", "Email weekly digest", "GitHub Issues", "Attachment processing"],
      team: ["25,000 feedback items/month", "50 active sources", "All channels", "365 days retention", "All Pro features included"],
    }),
    comparison: [
      { feature: "Feedback/month", free: "100", pro: "5,000", team: "25,000" },
      { feature: "Active sources", free: "2", pro: "10", team: "50" },
      { feature: "Channels", free: "Manual + email", pro: "All", team: "All" },
      { feature: "Retention", free: "30 days", pro: "180 days", team: "365 days" },
      { feature: "Semantic dedupe", free: "No", pro: "Yes", team: "Yes" },
      { feature: "Weekly digest", free: "No", pro: "Email", team: "Email" },
      { feature: "GitHub Issues", free: "No", pro: "Yes", team: "Yes" },
    ],
    dashboardFeatures: ["Feedback inbox", "Source connectors", "Sentiment overview", "Topic clusters", "Duplicate groups", "Spam labels", "GitHub issue action", "Weekly digest", "Usage quota"],
    faq: [
      { question: "Which sources can I connect?", answer: "Free supports manual and email. Pro and Team unlock all channels: Email, GitHub, Canny, Reddit, and X/Twitter." },
      { question: "Is deduplication available on Free?", answer: "Free shows basic sentiment and spam labels. Semantic deduplication starts on Pro." },
      { question: "Can it create GitHub Issues?", answer: "Yes. Pro and Team can turn feedback clusters into GitHub Issues." },
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
    headline: "Track competitor prices, stock status, history, and alerts from one command center.",
    description: "PriceTrackr monitors product URLs, charts price history, detects stock changes, and alerts by email or webhook.",
    seoTitle: "PriceTrackr - Price monitoring tool by DevForge",
    seoDescription: "Monitor product URLs, price drops, stock changes, history charts, custom selectors, and email or webhook alerts for ecommerce teams.",
    keywords: ["price monitoring tool", "price tracker", "competitor price monitoring", "product URL tracker", "price history chart"],
    problem: "Manual competitor checks are slow, inconsistent, and miss price drops while your margins are moving.",
    solution: "Track URLs, store price history, detect drops and scrape errors, configure selectors, and send alert workflows.",
    audience: "Ecommerce operators, agencies, founders, deal trackers, and market researchers.",
    features: ["Tracker list", "Price and stock state", "History chart", "Email/webhook alerts", "Custom selector preview", "Scrape error pause state", "Public product pages", "Usage quota"],
    useCases: ["Monitor competitor SKUs", "Track marketplace deals", "Watch stock changes", "Trigger webhook alerts"],
    demoTitle: "Price drop watchlist demo",
    demoDescription: "Browse simulated URL trackers with current/previous price, change status, history chart, alert settings, custom selectors, and paused error states.",
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
      { question: "How often can trackers run?", answer: "Free runs every 24 hours, Pro every hour, and Team every 10 minutes." },
      { question: "Can alerts go to webhooks?", answer: "Webhook alerts start on Pro and are included in Team." },
      { question: "Can I tune selectors?", answer: "Yes. Custom selectors are available on Pro and Team for pages where automatic extraction needs help." },
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
    headline: "Automate invoice follow-up, reply triage, reminders, and payment reconciliation.",
    description: "InvoiceFollow automates invoice follow-up, reply triage, reminders, and payment reconciliation.",
    seoTitle: "InvoiceFollow - Automated invoice reminders by DevForge",
    seoDescription: "Invoice follow up software for overdue invoices, automated invoice reminders, Gmail sync, NLP reply classification, Stripe and PayPal reconciliation, and weekly financial digests.",
    keywords: ["invoice follow up software", "automated invoice reminders", "invoice collection emails", "payment reconciliation", "Gmail invoice sync"],
    problem: "Late payments cost time, follow-up gets emotional, and replies or payment confirmations land in too many places.",
    solution: "Import invoices, run reminder schedules, classify client replies, pause disputed records, and match Stripe or PayPal payments.",
    audience: "Freelancers, agencies, consultants, founders, and small teams that need disciplined cash collection without awkward manual chasing.",
    features: ["Invoice list and status board", "CSV/XLS import", "Reminder schedule", "Email history", "NLP reply classification", "Stripe/PayPal state", "Gmail sync", "Weekly financial digest", "Usage quota"],
    useCases: ["Follow up overdue invoices", "Classify payment promise emails", "Pause disputes", "Reconcile Stripe/PayPal payments"],
    demoTitle: "Receivables recovery demo",
    demoDescription: "Walk through invoices, overdue states, reminder timeline, email preview, reply classification badges, payment reconciliation, and weekly digest.",
    plans: withLimits(sharedPlans("InvoiceFollow", true), {
      free: ["5 active invoices", "25 collection emails/month", "10 NLP reply analyses/month", "1 workspace user", "30 days retention"],
      pro: ["50 active invoices", "500 collection emails/month", "200 NLP reply analyses/month", "2 payment connections", "Stripe", "Limited PayPal", "90 days retention", "Gmail sync", "Weekly digest", "API access", "Bulk import"],
      team: ["200 active invoices", "2,000 collection emails/month", "1,000 NLP reply analyses/month", "5 workspace users", "10 payment connections", "Stripe and PayPal", "365 days retention", "Gmail sync", "Weekly digest", "API access", "Bulk import"],
    }),
    comparison: [
      { feature: "Active invoices", free: "5", pro: "50", team: "200" },
      { feature: "Emails/month", free: "25", pro: "500", team: "2,000" },
      { feature: "NLP analyses/month", free: "10", pro: "200", team: "1,000" },
      { feature: "Workspace users", free: "1", pro: "1", team: "5" },
      { feature: "Payment connections", free: "No", pro: "2", team: "10" },
      { feature: "Retention", free: "30 days", pro: "90 days", team: "365 days" },
      { feature: "Bulk import/API", free: "Limited/no", pro: "Yes", team: "Yes" },
    ],
    dashboardFeatures: ["Invoice list", "Status board", "Add/import flow", "Customer detail", "Reminder schedule", "Email history", "Reply classification", "Stripe/PayPal state", "Gmail sync", "Weekly digest", "Usage quota"],
    faq: [
      { question: "Does InvoiceFollow create legal invoices?", answer: "No. It tracks existing invoices, reminder workflows, replies, and payment reconciliation." },
      { question: "Can it connect Gmail?", answer: "Gmail sync starts on Pro and is included in Team." },
      { question: "What happens when a client disputes an invoice?", answer: "NLP reply classification can flag disputes and pause reminders for manual review." },
    ],
  },
];

export const DEVFORGE_SUITE = {
  name: "DevForge",
  domain: "devforgeapp.pro",
  url: "https://devforgeapp.pro",
  headline: "DevForge: five micro-SaaS tools to automate the boring parts of building.",
  description: "Clean files, debug webhooks, analyze feedback, track prices, and follow invoices from one developer-first suite.",
  audience: "Built for developers, founders, freelancers, agencies and small teams.",
  benefits: [
    "One developer-first suite instead of five scattered workflows.",
    "Shared auth, billing, and operational patterns across every tool.",
    "Clear Free, Pro, and Team limits so teams can start small and scale.",
    "Practical dashboards focused on repeated work, not vanity metrics.",
  ],
};

export function getProduct(slug: ProductSlug): DevForgeProduct {
  const product = DEVFORGE_PRODUCTS.find((item) => item.slug === slug);
  if (!product) {
    throw new Error(`Unknown DevForge product: ${slug}`);
  }
  return product;
}

export function getProductByDomain(domain: string): DevForgeProduct | undefined {
  return DEVFORGE_PRODUCTS.find((product) => product.domain === domain);
}
