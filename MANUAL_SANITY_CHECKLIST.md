# SmartSafe Manual Sanity Checklist

Use this checklist after major UI/backend changes to quickly validate core flows.

## Pre-check

1. Launch the app and log in with a valid user.
2. Select a workspace.
3. Ensure local DB backup exists (`smartsafe_local.db.bak`).

## 1) Settings Flow

1. Open Settings and confirm values load for WA token, phone ID, verify token, sync interval, mock toggle, and feature flags.
2. Change theme (`Dark` / `Light` / `System`) and verify UI updates immediately.
3. Save WhatsApp settings and verify button/status feedback appears.
4. Enter invalid sync interval (for example `0` or text) and confirm validation error appears.
5. Save mock toggle, leave settings, reopen settings, and confirm value persists.
6. Save feature flags and verify sidebar items hide/show correctly.
7. Restart app and confirm settings are still persisted.

## 2) Inbox Flow

1. Open Inbox and confirm conversation list loads without crash.
2. Test filters: search, status, unread-only, assignee, label, profile.
3. Select a conversation and confirm right-side chat panel loads.
4. Open an unread conversation and verify unread badge/count updates.
5. Test assign action and verify list refresh reflects new assignee.
6. Change status (`OPEN`, `PENDING`, `RESOLVED`, `CLOSED`) and verify badge/state updates.
7. Press refresh and verify no duplicate cards or stale list items appear.

## 3) Chat Flow

1. Select a conversation and verify message history loads.
2. Send normal text message and verify immediate render + persistence after reopen.
3. Reply to a message and verify thread indicator appears (`Replied to thread`).
4. Send from quick reply while reply mode is active and verify parent reply link is preserved.
5. Send an attachment and verify attachment click/open works.
6. Test star/unstar and delete, then refresh and verify state consistency.
7. Verify 24h session timer shows valid state (not stuck as `Unknown` for valid timestamps).

## 4) Bulk Send Flow

1. Open Bulk Send and confirm account selector loads accounts.
2. Paste mixed recipients (`+1555...`, `1555...`, `(44)-...`) and verify normalize + dedupe behavior.
3. Add invalid recipient lines and verify clear error message appears.
4. In Text mode, leave message empty and verify send is blocked.
5. In Template mode, leave template name empty and verify send is blocked.
6. Start campaign and verify send button/inputs disable and progress updates.
7. On completion, verify success/fail counts are shown correctly.

## Optional Smoke Re-run

1. Run `pytest -q`.
2. Run `python -m compileall -q core services integrations ui main.py tests`.
