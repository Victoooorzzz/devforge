# SaaS Critical Hardening Tranche 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce the remaining local bug backlog without pretending to solve items that require external infrastructure or product-level redesign.

**Architecture:** Continue product-scoped work using Neon for distributed state, authenticated cron jobs for queues, Render for backend deployment and Vercel for frontends.

**Tech Stack:** Python, FastAPI, SQLModel, unittest.

---

### Task 1: InvoiceFollow Remaining Local Fixes

Targets:
- IF-11: input cap and non-greedy regex for reply intent.
- IF-14: unique constraint for `forward_address_token` and collision-safe generation helper.
- IF-17: parse European/international amount formats.
- IF-22: remove dummy persisted `Invoice` from templates preview.
- IF-24: paginate Stripe event listing.
- IF-28: add export page/limit guard to avoid all-memory export.
- IF-02/IF-06/IF-09/IF-25/IF-26/IF-27: implement only safe local guardrails if small; otherwise document residual infrastructure/migration.

### Task 2: FeedbackLens Remaining Local Fixes

Targets:
- FL-05: compound cluster terms before generic terms.
- FL-09/FL-26: reduce O(n^2) cluster/dedupe summary work with caps/prefilter.
- FL-10/FL-11: avoid repeated candidate loads in bulk import.
- FL-12/FL-24: add export/list cursor/page/limit guard.
- FL-13: disable heavyweight transformer globals by default unless explicitly requested.
- FL-17/FL-18/FL-21/FL-22/FL-27/FL-28/FL-30: implement small local guards where practical.

### Task 3: WebhookMonitor Remaining Local Fixes

Targets:
- WM-005: re-raise cancellation/system exits and narrow broad catches in hot paths where practical.
- WM-009/WM-025/WM-026: aggregation/streaming or bounded cleanup improvements.
- WM-010: JSON schema validator cache.
- WM-014: distinguish timeout/connect errors.
- WM-018/WM-019/WM-020/WM-021: local circuit breaker/rate/delivery state guardrails where practical.
- WM-029 through WM-052: implement compact local safety fixes for export formatting, schema_error bounds, robust URLs, diff serialization, blacklist logging, invalid configs, negative indexes, and cron rate guard.
