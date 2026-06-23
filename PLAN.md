# SmartSafe v28 - Meta API Dashboard Enhancement Plan

## Workspace CRM + Contracts Pack (v1) - Implementation Status (2026-03-31)

### Completed in codebase
1. Core schema and model foundation added:
   - `contacts`, `conversations`, `labels`, `conversation_labels`, `contact_labels`, `contracts`
   - `messages` + `cloud_messages` extended with `conversation_id`, `contact_id`, `direction`, `channel`, `external_message_id`
2. Migration + backfill script added:
   - `alembic/versions/20260331_01_workspace_crm_and_contracts.py`
   - legacy external WhatsApp users/messages mapped to contacts + conversations
3. Repository/service layers implemented:
   - Contact, Conversation, Label, Contract repositories + services
   - conversation list filters: search, status, assignee, label (conversation + contact), unread only
4. Webhook/mock ingest updated to conversation-aware flow:
   - contact upsert
   - conversation upsert/open
   - inbound message writes with idempotent `external_message_id`
5. UI workflow implemented:
   - `InboxFrame` (chat list + conversation chat pane + assignment/status actions)
   - CRM `AddressBookFrame` (create/update contact, lifecycle, owner, notes, labels)
   - `ContractsFrame` (create contract, local doc attach/open, status transitions)
   - Sidebar entries wired: `Inbox`, `Contacts`, `Contracts`
6. Controller/main wiring completed:
   - new handlers for inbox/conversation/contacts/contracts
   - conversation-aware message callbacks
   - workspace switch now routes to Inbox V2 when enabled
7. Feature flags implemented in Settings:
   - `ENABLE_INBOX_V2`
   - `ENABLE_CONTACTS_CRM`
   - `ENABLE_CONTRACTS`
8. Prerequisite analytics mismatch fixed:
   - dashboard safely handles CRM metrics DTO fields
9. Tests in place and passing:
   - bulk recipient normalization unit tests
   - incremental polling integration scaffold/tests

### Next recommended updates
1. Add role-based policy hardening in UI layer (disable controls visually for non-admin actions).
2. Add conversation label attach/detach controls directly in Inbox.
3. Add contract reminder surfaces (upcoming renewal badge + dashboard widget).
4. Add integration test: webhook payload -> contact/conversation/message lifecycle (full end-to-end worker path).
5. Add migration execution command in deployment script (`alembic upgrade head`) + one-click backfill runbook.

## 0. Stabilization Update (2026-03-31)

### Fixed in this pass
- Fixed a hard runtime crash in `ui/chat_frame.py` caused by broken indentation in `_poll_messages`.
- Fixed duplicate message rendering in chat history/poll flow (messages were being added twice).
- Fixed broken UI import paths:
  - `ui/dashboard_frame.py` now imports `AccountHealthCard` from `ui.account_health_card`.
  - `ui/account_health_card.py` now imports `Tooltip` from `ui.tooltip`.
  - `ui/template_viewer_frame.py` now imports `TemplateCard` from `ui.template_card`.
- Verified source health with `py_compile` across all project `.py` files (excluding virtual env folders).
- Verified critical app imports (`main`, UI modules, controller/services) load successfully.

### Open technical debt
- Duplicate legacy UI files exist at project root (`account_health_card.py`, `template_card.py`, `tooltip.py`) and under `ui/`, which can cause future drift.
- Chat polling still fetches the full recent message list each cycle; it should become incremental (`since` cursor) for scale.
- No automated test suite currently guards these flows.

## 0.1 Future Update Roadmap (Recommended)

### Phase 1: Reliability Baseline (1-2 weeks)
- Add `tests/` with smoke tests for controller callbacks and core service flows.
- Add import/syntax CI step (`py_compile` + selected module import smoke test).
- Add strict input validation for bulk recipient phone numbers (E.164 style check and duplicate filtering).

### Phase 2: Architecture Cleanup (1 week)
- Consolidate duplicated root-level UI files into the `ui/` package only.
- Normalize imports to package-relative style inside `ui/` modules.
- Introduce a small `ui/components/` package only if shared widgets are truly reused.

### Phase 3: Chat Performance and Correctness (1-2 weeks)
- Change message loading API to support `since_timestamp` (or `since_id`) incremental polling.
- Add pagination/lazy history loading for large workspaces.
- Add message de-duplication guard in service layer (defensive, not only UI-level).

### Phase 4: Operations and Product Hardening (2 weeks)
- Improve worker observability: structured logs, worker heartbeat, and visible worker status in Settings.
- Add robust retry/backoff and clearer user-facing error states for Meta API failures.
- Add exportable operational report (daily success/failure counts for bulk send and sync).

## 1. Objective

To evolve the current placeholder "Dashboard" view into a comprehensive **System Health & Analytics Dashboard**. This dashboard will provide administrators with a real-time overview of all connected Meta WhatsApp Business Accounts, their health status, and key performance metrics for the selected workspace.

## 2. Current State Analysis

The existing `DashboardFrame` (`ui/dashboard_frame.py`) serves as a static welcome screen. Its capabilities are limited to:
- Displaying a welcome graphic and generic text.
- Performing a one-time, global check of the Meta API connection status (`whatsapp_service.check_status`).
- It receives `WorkspaceAnalyticsDTO` but does not visualize the data.
- The "View System Health" button (`_toggle_analytics`) is a non-functional stub.

This implementation does not leverage the rich data available for each individual `MetaAccount` or provide actionable insights.

## 3. Proposed Features

The new dashboard will be a dynamic, data-driven interface composed of the following key components:

### 3.1. Account Health Overview

This will be the primary view, replacing the welcome screen. It will display a list or grid of "Account Health Cards" for every `MetaAccount` linked to the current workspace.

**Each Account Health Card will display:**
- **Display Name:** The user-friendly name for the account (e.g., "Sales Department Number").
- **Official Phone Number:** The `display_phone` from Meta.
- **Verified Name:** The `verified_name` associated with the business.
- **Quality Rating:** A color-coded indicator (`GREEN`, `YELLOW`, `RED`) for the `quality_rating`. This is critical for compliance and deliverability.
- **API Status:** The connection status of the number (e.g., `CONNECTED`, `DISCONNECTED`).
- **Last Sync:** A timestamp of when the health status was last refreshed (`last_synced_at`).

### 3.2. Interactive Account Actions

Each Account Health Card will feature interactive elements:
- **Refresh Button:** A button to trigger an on-demand status update for that specific account by calling `meta_account_service.refresh_account_status`.
- **View Templates Button:** A button that navigates to the "Message Templates" view (see 3.4).

### 3.3. Workspace Analytics Visualization

The dashboard will visualize the data from the `WorkspaceAnalyticsDTO` (which is already passed to the view).
- **Key Metrics Display:** Simple, clear widgets for:
    - Total Messages Sent
    - Total Messages Received
    - Active Conversations
    - New Contacts
- (Future) Charts and graphs to show message trends over time.

### 3.4. Message Template Viewer

A new section or tab accessible from the dashboard.
- **List All Templates:** Fetches and displays all message templates associated with the workspace's accounts using `meta_cloud_service.get_message_templates`.
- **Template Details:** For each template, it will show:
    - Name (`name`)
    - Status (`status`, e.g., `APPROVED`, `PENDING`, `REJECTED`)
    - Category (`category`)
    - Language (`language`)
    - Body Content Preview

## 4. Technical Implementation Plan

### Phase 1: UI Refactoring (`ui/dashboard_frame.py`)

1.  **Create `AccountHealthCard` Component:**
    - Create a new file, e.g., `ui/components/account_health_card.py`.
    - This `ctk.CTkFrame` subclass will take a `MetaAccountDTO` and display its information. It will include labels for all metrics and the "Refresh" button.
2.  **Overhaul `DashboardFrame` Layout:**
    - Remove the existing welcome widgets (`welcome_container`).
    - Add a `ctk.CTkScrollableFrame` to hold the list of `AccountHealthCard` widgets.
    - Add a header section to display the `WorkspaceAnalyticsDTO` metrics.
    - The `refresh_data` method will be rewritten to accept a list of `MetaAccountDTO`s and dynamically create/update the `AccountHealthCard` widgets inside the scrollable frame.

### Phase 2: Controller and Data Flow (`core/app_controller.py`)

1.  **Enhance `handle_dashboard_select`:**
    - This controller method is triggered when the user clicks "Dashboard" in the sidebar.
    - It already fetches `WorkspaceAnalyticsDTO`.
    - It needs to be modified to also call `self.meta_account_service.get_accounts(workspace.id)` to get all accounts for the workspace.
2.  **Update `update_dashboard_view` Call:**
    - The call to `self.view.update_dashboard_view` in `handle_dashboard_select` must be updated to pass both the analytics DTO and the list of account DTOs.
    - The method signature in `main.py` will need to be changed accordingly: `def update_dashboard_view(self, stats: WorkspaceAnalyticsDTO, accounts: List[MetaAccountDTO], workspace: WorkspaceDTO):`.
3.  **Implement Refresh Callback:**
    - Create a new controller method, e.g., `handle_refresh_account_status(account_id: str)`.
    - This method will call `self.meta_account_service.refresh_account_status(account_id)`.
    - It should return the updated `MetaAccountDTO` so the UI can be refreshed.
    - This callback will be passed down to the `DashboardFrame` and then to each `AccountHealthCard`.

### Phase 3: Template Viewer Implementation

1.  **Create `TemplateViewerFrame`:**
    - A new UI frame class, similar to `DashboardFrame`, to display templates in a table (using `CTkTable` or a custom grid).
2.  **Add Controller Logic:**
    - Create a new controller method `handle_view_templates_select`.
    - This method will call `self.meta_cloud_service.get_message_templates(...)` for the relevant WABA ID.
    - It will then call a new view method `self.view.update_template_viewer_view(...)` to display the data.
3.  **Integrate Navigation:**
    - The "View Templates" button on the `AccountHealthCard` will trigger the `handle_view_templates_select` controller method.

## 5. Affected Files

-   **`ui/dashboard_frame.py`**: Major rewrite.
-   **`main.py`**: Signature change for `update_dashboard_view`.
-   **`core/app_controller.py`**: Logic changes in `handle_dashboard_select` and addition of new handler methods for account refresh and template viewing.
-   **New File: `ui/components/account_health_card.py`**: To encapsulate the UI for a single Meta account.
-   **New File: `ui/template_viewer_frame.py`**: For the message template browser.
