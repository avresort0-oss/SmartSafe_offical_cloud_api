# SmartSafe Hybrid Meta Cloud API Future Plan (12 Weeks)

## Summary
Goal: existing desktop CRM app-ke break না করে production-ready, multi-workspace Meta Cloud API layer build করা।  
Priority: Reliability + Security first, তারপর SaaS-grade API এবং automation options।  
Target: Hybrid architecture (desktop client + separate cloud API service), Multi-workspace SaaS readiness.

## Current State Snapshot
1. System এখন desktop-first, local SQLite + background workers ভিত্তিক।
2. Sync layer এখন simulated cloud behavior ব্যবহার করে, real remote cloud persistence না।
3. Webhook ingest text-only focused; media/status event handling নেই।
4. Account selectionে কিছু জায়গায় “first active account/workspace” fallback আছে, multi-tenant safety risk।
5. Settings-এ global WA token fields আছে, কিন্তু account-scoped credential flow-এর সাথে পুরোপুরি aligned না।
6. Core reliability tests আছে, কিন্তু API/webhook/security coverage এখনো limited।

## Scope (In)
1. Separate FastAPI cloud service introduce করা (`/v1` API, webhook ingestion, outbound messaging orchestration)।
2. Workspace-scoped tenant isolation, API key auth, audit logging, idempotency।
3. Meta webhook + outbound lifecycle full tracking (queued/sent/delivered/read/failed)।
4. Existing desktop app-ke API client mode-এ ধাপে ধাপে migrate করা (big-bang rewrite না)।

## Scope (Out)
1. Mobile app build।
2. AI chatbot/NLP production rollout in first 12 weeks।
3. Billing engine full implementation (billing-ready schema only).

## Architecture Decisions (Locked)
1. API framework: FastAPI + SQLAlchemy + Alembic।
2. Cloud DB: PostgreSQL 16 (desktop SQLite থাকবে local mode-এর জন্য)।
3. Async pipeline: Redis 7 + Celery worker + dedicated dead-letter queue।
4. Auth model: `X-API-Key` (workspace-scoped), per-key permissions।
5. API versioning: `/v1/...` fixed prefix।
6. Event idempotency: `webhook_event_id` + `external_message_id` unique constraints।
7. Observability: structured JSON logs + request_id + Prometheus metrics।
8. Security baseline: webhook signature verification, secret rotation, no hardcoded fallback numbers।

## Public API / Interface Additions
1. `POST /v1/webhooks/meta/{phone_number_id}`  
Request: raw Meta payload + signature header.  
Response: `202 accepted` with event_id.
2. `POST /v1/messages/send`  
Fields: `workspace_id`, `meta_account_id`, `to`, `type(text|template|media)`, `content`, `template`, `media_url`.  
Response: queued job id + initial status.
3. `POST /v1/messages/bulk`  
Fields: same as send + recipient list + campaign metadata.  
Response: campaign_id + accepted/rejected counts.
4. `GET /v1/messages/{message_id}/status`  
Returns lifecycle status timeline.
5. `GET /v1/accounts/{account_id}/health`  
Returns `api_status`, `quality_rating`, `last_synced_at`, limits/warnings.
6. `GET /v1/templates?workspace_id=&meta_account_id=`  
Template list with status/category/language/components.
7. `POST /v1/auto-reply/rules` / `GET` / `PATCH` / `DELETE`  
Workspace + optional account scoped rule management.
8. `GET /v1/analytics/overview?workspace_id=&from=&to=`  
Sent/failed/read rate, active conversations, new contacts.

## Data Model Changes
1. `webhook_events`: provider_event_id, phone_number_id, payload_hash, processed_at, status, error.
2. `outbound_messages`: workspace_id, meta_account_id, channel, payload, status, provider_message_id.
3. `delivery_events`: message_id, event_type(sent|delivered|read|failed), reason_code, timestamp.
4. `api_keys`: workspace_id, key_hash, permissions, is_active, expires_at.
5. `audit_logs`: actor, workspace_id, action, resource_type, resource_id, metadata.
6. `rate_limit_counters`: workspace_id, window_start, request_count.
7. Existing model cleanup: single SQLAlchemy Base unify করা; duplicate worker manager path remove করা।

## 12-Week Execution Plan
1. Week 1-2: Foundation Hardening  
Deliverables: unified model base, migration discipline, env/secret cleanup, hardcoded fallback removal, explicit workspace/account routing.
2. Week 3-4: Webhook Reliability  
Deliverables: signed webhook validation, idempotent processing, retry + DLQ, text+media+status event parsing.
3. Week 5-6: Outbound API + Queue  
Deliverables: send/bulk endpoints, Celery workers, message lifecycle state machine, provider error mapping.
4. Week 7-8: Tenant Security + Audit  
Deliverables: API keys, role permissions, audit logs, quota and rate-limit middleware.
5. Week 9-10: Analytics + Template APIs  
Deliverables: template sync endpoint, account health refresh API, delivery analytics endpoints.
6. Week 11-12: Desktop Hybrid Integration  
Deliverables: desktop app read/write through cloud API toggle, fallback local mode, rollout checklist + rollback path.

## Future Feature Options (After Core Plan)
1. Contract renewal reminders + automated WhatsApp template nudges.
2. SLA breach alerts by conversation inactivity thresholds.
3. Campaign scheduler with timezone-safe send windows.
4. Contact scoring and pipeline automation triggers.
5. AI-assisted reply suggestions (human-in-loop only).
6. Partner webhook subscriptions (event forwarding).

## Test Cases and Scenarios
1. Webhook signature invalid -> 401 and no DB write.
2. Same webhook payload replay -> exactly-once behavior.
3. Media + text + status callbacks parse and store correctly.
4. Bulk send with mixed valid/invalid recipients -> deterministic accepted/rejected output.
5. Provider temporary failure -> retry then DLQ after max attempts.
6. Provider permanent failure -> failed status with reason code.
7. Workspace A API key দিয়ে Workspace B data access blocked.
8. Message lifecycle transitions are monotonic and auditable.
9. High-volume load: sustained webhook ingest without duplicate rows.
10. Desktop hybrid mode switch local↔cloud without data loss.
11. Migration up/down smoke test on clean and existing DB snapshots.
12. CI gate: unit + integration + contract tests + lint + migration check.

## Acceptance Criteria
1. 0 duplicate inbound message writes under replay tests.
2. 99%+ webhook processing success under normal load.
3. Full outbound traceability from request to delivery/read.
4. Tenant isolation validated by automated security tests.
5. Desktop app critical flows কাজ করে cloud mode-এ regression ছাড়া।

## Assumptions and Defaults
1. Architecture direction: Hybrid.
2. Priority: Reliability + Security first.
3. Deployment target: Multi-workspace SaaS foundation.
4. Existing desktop workflows kept functional during migration.
5. Production runtime target remains Python 3.10 in this phase.
