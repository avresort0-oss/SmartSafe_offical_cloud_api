import logging
import threading
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from core.api_client import ApiClient
from core.database import SessionLocal, init_db
from core.worker_manager import WorkerManager
from integrations.whatsapp_integration import WhatsAppIntegration
from services.contact_service import ContactCreateDTO, ContactService
from services.contract_service import ContractCreateDTO, ContractService
from services.conversation_service import ConversationService
from services.label_service import LabelService
from services.message_service import MessageCreateDTO, MessageResponseDTO, MessageService
from services.meta_account_service import MetaAccountService
from services.meta_cloud_service import MetaCloudService
from services.settings_service import SettingsService
from services.sync_service import SyncService
from services.auto_reply_service import AutoReplyService
from services.user_service import UserCreateDTO, UserService
from services.workspace_service import WorkspaceDTO, WorkspaceService
from state.app_state_manager import app_state_manager

if TYPE_CHECKING:
    from main import SmartSafeApp


logger = logging.getLogger(__name__)


class AppController:
    FLAG_ENABLE_INBOX_V2 = "ENABLE_INBOX_V2"
    FLAG_ENABLE_CONTACTS_CRM = "ENABLE_CONTACTS_CRM"
    FLAG_ENABLE_CONTRACTS = "ENABLE_CONTRACTS"

    def __init__(self, app_ui: "SmartSafeApp"):
        self.app_ui = app_ui
        self.db_session = None
        self.settings_service = None
        self.user_service = None
        self.workspace_service = None
        self.contact_service = None
        self.conversation_service = None
        self.label_service = None
        self.contract_service = None
        self.sync_service = None
        self.auto_reply_service = None
        self.meta_cloud_service = None
        self.meta_account_service = None
        self.whatsapp_integration = None
        self.message_service = None
        self.worker_manager = None
        self.api_client = None

    def initialize(self, callback: Optional[Callable] = None):
        """Asynchronously initialize database, services, and integrations."""
        def _task():
            try:
                logger.info("Starting background initialization...")
                init_db()
                self.db_session = SessionLocal()
                self.settings_service = SettingsService(self.db_session)
                self.user_service = UserService(self.db_session)
                self.workspace_service = WorkspaceService(self.db_session)
                self.contact_service = ContactService(self.db_session)
                self.conversation_service = ConversationService(self.db_session)
                self.label_service = LabelService(self.db_session)
                self.contract_service = ContractService(self.db_session)
                self.sync_service = SyncService()
                self.auto_reply_service = AutoReplyService()

                self.meta_cloud_service = MetaCloudService()
                self.meta_account_service = MetaAccountService(self.db_session, self.meta_cloud_service)

                saved_theme = self.settings_service.get_setting("APP_THEME", "Dark")
                # UI updates MUST happen on the main thread via .after()
                self.app_ui.after(0, lambda: self._apply_initial_theme(saved_theme))
                self._ensure_feature_flag_defaults()

                self._initialize_integrations()
                self.worker_manager = self._build_worker_manager()
                self.api_client = ApiClient()
                
                logger.info("AppController initialization complete.")
                if callback:
                    self.app_ui.after(50, callback) # Slight delay to let theme settle
            except Exception as e:
                logger.error(f"Initialization failed: {e}", exc_info=True)
                error_msg = f"Critical System Error: {str(e)}"
                self.app_ui.after(0, lambda: self.app_ui.display_auth_error(error_msg, is_login=False))

        threading.Thread(target=_task, daemon=True).start()

    def _run_async(self, func: Callable, *args, callback: Optional[Callable] = None, **kwargs):
        """Standardized helper to run blocking tasks in a background thread."""
        def _wrapper():
            try:
                result = func(*args, **kwargs)
                if callback:
                    self.app_ui.after(0, lambda: callback(result))
            except Exception as e:
                logger.error(f"Async execution error in {func.__name__}: {e}", exc_info=True)
                # Optionally notify UI of background error
                self.app_ui.after(0, lambda error=e: self.app_ui.display_auth_error(f"Background Error: {str(error)}", is_login=False))

        threading.Thread(target=_wrapper, daemon=True).start()

    def _apply_initial_theme(self, theme: str):
        """Safely applies the initial theme on the main thread."""
        import customtkinter as ctk
        ctk.set_appearance_mode(theme)
        logger.info(f"Initial theme '{theme}' applied safely to Main Thread.")

    def _initialize_integrations(self):
        self.whatsapp_integration = WhatsAppIntegration(db_session=self.db_session)
        self.message_service = MessageService(self.whatsapp_integration)
        logger.info("WhatsApp integration initialized/re-initialized.")

    def _build_worker_manager(self) -> WorkerManager:
        sync_interval = int(self.settings_service.get_setting("SYNC_INTERVAL", "10"))
        mock_enabled = self.settings_service.get_setting("MOCK_ENABLED", "1") == "1"
        webhook_verify_token = self.settings_service.get_setting(
            "META_WEBHOOK_VERIFY_TOKEN", ""
        )
        return WorkerManager(
            whatsapp_integration=self.whatsapp_integration,
            sync_interval=sync_interval,
            mock_enabled=mock_enabled,
            webhook_verify_token=webhook_verify_token,
        )

    def _ensure_feature_flag_defaults(self):
        defaults = {
            self.FLAG_ENABLE_INBOX_V2: "1",
            self.FLAG_ENABLE_CONTACTS_CRM: "1",
            self.FLAG_ENABLE_CONTRACTS: "1",
        }
        for key, value in defaults.items():
            if self.settings_service.get_setting(key) is None:
                self.settings_service.set_setting(key, value)

    def _is_feature_enabled(self, key: str, default: bool = True) -> bool:
        default_raw = "1" if default else "0"
        return self.settings_service.get_setting(key, default_raw) == "1"

    def get_feature_flags(self) -> Dict[str, bool]:
        return {
            self.FLAG_ENABLE_INBOX_V2: self._is_feature_enabled(self.FLAG_ENABLE_INBOX_V2, True),
            self.FLAG_ENABLE_CONTACTS_CRM: self._is_feature_enabled(self.FLAG_ENABLE_CONTACTS_CRM, True),
            self.FLAG_ENABLE_CONTRACTS: self._is_feature_enabled(self.FLAG_ENABLE_CONTRACTS, True),
        }

    def start_initial_view(self):
        self.app_ui.show_auth_view()

    def handle_login(self, username, password):
        logger.info(f"Login attempt for user: {username}")
        
        def _worker():
            return self.user_service.authenticate_user(username, password)

        def _callback(user_dto):
            if user_dto:
                logger.info(f"Login successful for user: {username} (ID: {user_dto.id})")
                app_state_manager.set_current_user(user_dto)
                self._start_background_workers()
                self.app_ui.show_main_application_view(user_dto)
            else:
                logger.warning(f"Login failed for user: {username}")
                self.app_ui.display_auth_error("Invalid username or password.", is_login=True)

        self._run_async(_worker, callback=_callback)

    def handle_register(self, username, email, password):
        logger.info(f"Registration attempt for: {username} ({email})")
        dto = UserCreateDTO(username=username, email=email, password=password)
        
        def _worker():
            return self.user_service.register_user(dto)

        def _callback(user_dto):
            logger.info(f"Registration successful for: {username}")
            app_state_manager.set_current_user(user_dto)
            self._start_background_workers()
            self.app_ui.show_main_application_view(user_dto)

        self._run_async(_worker, callback=_callback)

    def handle_logout(self):
        app_state_manager.logout()
        self._stop_background_workers()
        self.app_ui.show_auth_view()

    def _start_background_workers(self):
        self.worker_manager.start_all()

    def _stop_background_workers(self):
        self.worker_manager.stop_all()

    def get_user_workspaces(self, user_id: str) -> List[WorkspaceDTO]:
        user_workspaces = self.workspace_service.get_user_workspaces(user_id)
        if not user_workspaces:
            username = "WorkspaceUser"
            current_user = app_state_manager.get_current_user()
            if current_user and current_user.id == user_id:
                username = current_user.username
            else:
                db_user = self.user_service.get_user_by_id(user_id)
                if db_user:
                    username = db_user.username
            user_workspaces = [self.workspace_service.create_default_workspace(user_id, username)]
        return user_workspaces

    def handle_workspace_create(self, name: str):
        user = app_state_manager.get_current_user()
        if not user:
            return

        def _worker():
            from core.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
            ws = Workspace(name=name, owner_id=user.id)
            self.workspace_service.repository.add(ws)
            member = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=WorkspaceRole.ADMIN)
            self.workspace_service.repository.add_member(member)
            return self.get_user_workspaces(user.id), ws.id

        def _callback(result):
            workspaces, new_ws_id = result
            if self.app_ui.sidebar_frame:
                self.app_ui.sidebar_frame.workspaces = workspaces
                self.app_ui.sidebar_frame._build_main_nav()

            new_ws_dto = next((w for w in workspaces if w.id == new_ws_id), None)
            if new_ws_dto:
                self.handle_workspace_select(new_ws_dto)

        self._run_async(_worker, callback=_callback)

    def _ensure_api_key(self, workspace_id: str):
        from services.auth_service import AuthService
        setting_key = f"API_KEY_{workspace_id}"
        raw_key = self.settings_service.get_setting(setting_key)
        
        if not raw_key:
            logger.info("Generating new API Key for hybrid cloud mode...")
            raw_key, api_key_model = AuthService.generate_api_key(workspace_id, "Hybrid Client Key")
            self.db_session.add(api_key_model)
            self.db_session.commit()
            self.settings_service.set_setting(setting_key, raw_key)
            
        self.api_client.set_api_key(raw_key)

    def handle_workspace_select(self, workspace: WorkspaceDTO):
        logger.info(f"Selecting workspace: {workspace.name} (ID: {workspace.id})")
        app_state_manager.set_current_workspace(workspace)
        
        if os.getenv("USE_CLOUD_API", "False").lower() == "true":
            self._ensure_api_key(workspace.id)
            
        if self._is_feature_enabled(self.FLAG_ENABLE_INBOX_V2, True):
            self.handle_inbox_select()
        else:
            self.app_ui.update_chat_view(
                workspace,
                self.get_load_messages_cb(conversation_scoped=False),
                self.get_send_message_cb(),
                self.get_delete_message_cb(),
                self.get_toggle_star_cb(),
            )

    
    
    def handle_audit_log_select(self):
        def _fetch():
            from core.database import SessionLocal
            with SessionLocal() as db:
                from core.models.audit_log import AuditLog
                logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
                db.expunge_all()
                return logs
                
        self.app_ui.update_audit_log_view(fetch_logs_cb=_fetch)

    def handle_kanban_select(self):
        ws = app_state_manager.get_current_workspace()
        if not ws:
            return
            
        def _fetch():
            from core.database import SessionLocal
            with SessionLocal() as db:
                from core.models.contact import Contact
                contacts = db.query(Contact).filter(Contact.workspace_id == ws.id).all()
                db.expunge_all()
                return contacts
                
        def _update_stage(contact_id, new_stage):
            from core.database import SessionLocal
            try:
                with SessionLocal() as db:
                    from core.models.contact import Contact
                    contact = db.query(Contact).filter(Contact.id == contact_id, Contact.workspace_id == ws.id).first()
                    if contact:
                        contact.lifecycle_stage = new_stage
                        db.commit()
                        return True
            except Exception as e:
                import logging
                logging.error(f"Failed to update stage: {e}")
            return False
            
        self.app_ui.update_kanban_view(fetch_contacts_cb=_fetch, update_stage_cb=_update_stage)

    def handle_dashboard_select(self):
        ws = app_state_manager.get_current_workspace()
        if not ws:
            return

        # Show loading state first
        self.app_ui.update_dashboard_view(None, None, ws, loading=True)

        def _fetch_data():
            stats = self.workspace_service.get_workspace_analytics(ws.id)
            accounts = self.meta_account_service.get_accounts(ws.id)
            return stats, accounts

        def _update_ui(result):
            stats, accounts = result
            self.app_ui.update_dashboard_view(stats, accounts, ws, loading=False)

        self._run_async(_fetch_data, callback=_update_ui)

    def handle_settings_select(self):
        self.app_ui.update_settings_view(
            on_save_wa_settings=self.handle_save_wa_settings,
            load_wa_settings_cb=self.get_load_wa_settings_cb(),
            check_wa_status_cb=self.get_check_wa_status_cb(),
            on_save_sync_settings=self.handle_save_sync_settings,
            load_sync_settings_cb=self.get_load_sync_settings_cb(),
            on_save_mock_settings=self.handle_save_mock_settings,
            load_mock_settings_cb=self.get_load_mock_settings_cb(),
            on_save_theme_cb=self.handle_save_theme,
            load_theme_cb=self.get_load_theme_cb(),
            on_save_feature_flags_cb=self.handle_save_feature_flags,
            load_feature_flags_cb=self.get_load_feature_flags_cb(),
        )

    def handle_global_search(self, query: str):
        results = self.message_service.search_messages(query)
        mock_ws = WorkspaceDTO(id="search", name=f"Search Results: '{query}'", owner_id="system", role="System")
        self.app_ui.update_chat_view(
            mock_ws,
            lambda _conversation_id=None, _since_timestamp=None: results,
            self.get_send_message_cb(),
            self.get_delete_message_cb(),
            self.get_toggle_star_cb(),
        )

    def handle_members_select(self):
        # Members view is deprecated by Contact CRM for this release.
        self.handle_contacts_select()

    def handle_inbox_select(self):
        ws = app_state_manager.get_current_workspace()
        if not ws:
            return

        # Show the view immediately with current state, then refresh conversations in background
        self.app_ui.update_inbox_view(
            workspace=ws,
            load_conversations_cb=self.get_load_conversations_cb(),
            load_messages_cb=self.get_load_messages_cb(conversation_scoped=True),
            send_message_cb=self.get_send_message_cb(),
            delete_message_cb=self.get_delete_message_cb(),
            toggle_star_cb=self.get_toggle_star_cb(),
            load_quick_replies_cb=self.get_load_quick_replies_cb(),
            on_conversation_select_cb=self.handle_conversation_select,
            on_assign_cb=self.handle_assign_conversation,
            on_update_status_cb=self.handle_update_conversation_status,
            get_accounts_cb=self.get_accounts_cb(),
            load_labels_cb=self.get_load_labels_cb(),
            attach_label_cb=self.get_attach_conversation_label_cb(),
            detach_label_cb=self.get_detach_conversation_label_cb(),
            create_contract_cb=self.get_create_contract_cb(),
        )

    def handle_conversation_select(self, conversation_id: str):
        if not conversation_id:
            return None
        self.conversation_service.mark_read(conversation_id)
        return self.conversation_service.get_conversation(conversation_id)

    def _current_workspace_is_admin(self) -> bool:
        ws = app_state_manager.get_current_workspace()
        return bool(ws and ws.role and ws.role.lower() == "admin")

    def _ensure_conversation_permission(self, conversation_id: str, target_assignee: Optional[str] = None):
        conversation = self.conversation_service.get_conversation(conversation_id)
        if not conversation:
            raise ValueError("Conversation not found.")
        if self._current_workspace_is_admin():
            return conversation

        user = app_state_manager.get_current_user()
        if not user:
            raise PermissionError("Authentication required.")
        if conversation.assigned_user_id and conversation.assigned_user_id != user.id:
            raise PermissionError("Members can only manage their own assigned conversations.")
        if target_assignee and target_assignee != user.id:
            raise PermissionError("Members can only assign conversations to themselves.")
        return conversation

    def handle_assign_conversation(self, conversation_id: str, user_id: Optional[str], callback: Optional[Callable] = None):
        def _worker():
            self._ensure_conversation_permission(conversation_id, user_id)
            return self.conversation_service.assign_conversation(conversation_id, user_id)
        
        self._run_async(_worker, callback=callback)

    def handle_update_conversation_status(self, conversation_id: str, status: str, callback: Optional[Callable] = None):
        def _worker():
            self._ensure_conversation_permission(conversation_id)
            return self.conversation_service.update_status(conversation_id, status)
        
        self._run_async(_worker, callback=callback)

    def handle_contacts_select(self):
        ws = app_state_manager.get_current_workspace()
        if not ws or not self._is_feature_enabled(self.FLAG_ENABLE_CONTACTS_CRM, True):
            return

        def _fetch_data():
            # Initial load of contacts and labels can be heavy
            contacts = self.contact_service.list_contacts(ws.id)
            labels = self.label_service.list_labels(ws.id)
            return contacts, labels

        def _update_ui(result):
            # Pass data directly if the view supports it, or just trigger refresh
            self.app_ui.update_contacts_view(
                workspace=ws,
                load_contacts_cb=self.get_load_contacts_cb(),
                create_contact_cb=self.get_create_contact_cb(),
                update_contact_cb=self.get_update_contact_cb(),
                load_labels_cb=self.get_load_labels_cb(),
                create_label_cb=self.get_create_label_cb(),
                attach_label_cb=self.get_attach_contact_label_cb(),
                detach_label_cb=self.get_detach_contact_label_cb(),
            )

        self._run_async(_fetch_data, callback=_update_ui)

    def handle_contracts_select(self):
        ws = app_state_manager.get_current_workspace()
        if not ws:
            return
        if not self._is_feature_enabled(self.FLAG_ENABLE_CONTRACTS, True):
            return
        self.app_ui.update_contracts_view(
            workspace=ws,
            load_contracts_cb=self.get_load_contracts_cb(),
            load_contacts_cb=self.get_load_contacts_cb(),
            create_contract_cb=self.get_create_contract_cb(),
            update_contract_status_cb=self.get_update_contract_status_cb(),
        )

    def handle_accounts_select(self):
        ws = app_state_manager.get_current_workspace()
        if ws:
            self.app_ui.update_accounts_view(
                workspace_id=ws.id,
                get_accounts_cb=self.get_accounts_cb(),
                add_account_cb=self.meta_account_service.add_account,
                remove_account_cb=self.meta_account_service.remove_account,
                refresh_account_cb=self.meta_account_service.refresh_account_status,
            )

    def handle_bulk_message_select(self):
        def _bulk_send(recipients: List[str], message_body: str, sender_id: str, account_id: str = None):
            if os.getenv("USE_CLOUD_API", "False").lower() == "true":
                logger.info("Routing bulk_send through Cloud API...")
                payload = {
                    "recipients": recipients,
                    "content": message_body,
                    "sender_id": sender_id,
                    "meta_account_id": account_id
                }
                return self.api_client.post("/messages/bulk", payload)
            else:
                return self.meta_account_service.bulk_send(recipients, message_body, sender_id, account_id)

        self.app_ui.update_bulk_message_view(
            get_accounts_cb=self.get_accounts_cb(),
            bulk_send_cb=_bulk_send,
        )

    def handle_lead_analytics_select(self):
        ws = app_state_manager.get_current_workspace()
        if not ws:
            return

        # Show loading state
        self.app_ui.update_lead_analytics_view(ws, None, None, loading=True)

        def _fetch_data():
            contacts = self.contact_service.list_contacts(ws.id)
            contracts = self.contract_service.list_contracts(ws.id)
            return contacts, contracts

        def _update_ui(result):
            contacts, contracts = result
            self.app_ui.update_lead_analytics_view(ws, contacts, contracts, loading=False)

        self._run_async(_fetch_data, callback=_update_ui)

    def handle_quick_replies_select(self):
        self.app_ui.update_quick_replies_view(
            load_quick_replies_cb=self.get_load_quick_replies_cb(),
            save_quick_replies_cb=self.get_save_quick_replies_cb()
        )

    def handle_auto_reply_select(self):
        ws = app_state_manager.get_current_workspace()
        if ws:
            self.app_ui.update_auto_reply_view(ws)

    def handle_refresh_account_status(self, account_id: str):
        logger.info("User triggered background refresh for account_id: %s", account_id)

        def _worker():
            try:
                self.meta_account_service.refresh_account_status(account_id)
            except Exception as e:
                logger.error("Failed to refresh account status: %s", e)
            finally:
                self.app_ui.after(0, self.handle_dashboard_select)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def handle_view_templates_select(self, account_id: str):
        logger.info("User triggered view templates for account_id: %s", account_id)
        
        def _worker():
            from core.database import SessionLocal
            from core.repositories.meta_account_repository import MetaAccountRepository
            try:
                with SessionLocal() as session:
                    repo = MetaAccountRepository(session)
                    account_model = repo.get_by_id(account_id)
                    
                    if not account_model or not account_model.waba_id:
                        logger.warning("Could not find account or waba_id for account_id: %s", account_id)
                        return
                    
                    wa_token = account_model.access_token
                    waba = account_model.waba_id
                    account_dto = self.meta_account_service._to_dto(account_model)
                
                if os.getenv("USE_CLOUD_API", "False").lower() == "true":
                    logger.info("Fetching templates through Cloud API...")
                    response = self.api_client.get(f"/templates?waba_id={waba}&access_token={wa_token}")
                    templates = response.get("templates", [])
                    error = None
                else:
                    templates, error = self.meta_cloud_service.get_message_templates(waba, wa_token)
                
                if error:
                    logger.error("Failed to fetch templates: %s", error)
                    templates = []
                
                self.app_ui.after(0, lambda: self.app_ui.update_template_viewer_view(templates or [], account_dto))
            except Exception as e:
                logger.error("Error fetching templates: %s", e)
                
        threading.Thread(target=_worker, daemon=True).start()

    def handle_save_wa_settings(self, token: str, phone_id: str, verify_token: str):
        self.settings_service.set_setting("WA_TOKEN", token)
        self.settings_service.set_setting("WA_PHONE_ID", phone_id)
        self.settings_service.set_setting("META_WEBHOOK_VERIFY_TOKEN", verify_token)
        self._initialize_integrations()
        self._reload_workers()
        logger.info("WhatsApp settings saved and services re-initialized.")

    def handle_save_sync_settings(self, interval: str):
        self.settings_service.set_setting("SYNC_INTERVAL", interval)
        self._reload_workers()
        logger.info("Sync settings saved. Interval updated to %ss.", interval)

    def handle_save_mock_settings(self, enabled: bool):
        self.settings_service.set_setting("MOCK_ENABLED", "1" if enabled else "0")
        self._reload_workers()
        logger.info("Mock settings saved. Enabled: %s", enabled)

    def handle_save_feature_flags(self, enable_inbox_v2: bool, enable_contacts_crm: bool, enable_contracts: bool):
        self.settings_service.set_setting(self.FLAG_ENABLE_INBOX_V2, "1" if enable_inbox_v2 else "0")
        self.settings_service.set_setting(self.FLAG_ENABLE_CONTACTS_CRM, "1" if enable_contacts_crm else "0")
        self.settings_service.set_setting(self.FLAG_ENABLE_CONTRACTS, "1" if enable_contracts else "0")
        if self.app_ui.sidebar_frame:
            flags = self.get_feature_flags()
            self.app_ui.sidebar_frame.update_feature_flags(
                flags[self.FLAG_ENABLE_INBOX_V2],
                flags[self.FLAG_ENABLE_CONTACTS_CRM],
                flags[self.FLAG_ENABLE_CONTRACTS],
            )
        ws = app_state_manager.get_current_workspace()
        if ws:
            self.handle_workspace_select(ws)

    def _reload_workers(self):
        self._stop_background_workers()
        self.worker_manager = self._build_worker_manager()
        self._start_background_workers()
        logger.info("Background workers reloaded with new configuration.")

    def handle_save_theme(self, theme: str):
        self.settings_service.set_setting("APP_THEME", theme)
        import customtkinter as ctk

        ctk.set_appearance_mode(theme)
        logger.info("Enterprise theme updated to %s.", theme)

    def handle_check_wa_status(self) -> (bool, str):
        if self.whatsapp_integration:
            return self.whatsapp_integration.check_status()
        return False, "Integration not initialized."

    def get_load_conversations_cb(self) -> Callable:
        def _load(
            search: str = "",
            status: Optional[str] = None,
            assigned_user_id: Optional[str] = None,
            label_query: Optional[str] = None,
            unread_only: bool = False,
            meta_account_id: Optional[str] = None,
        ):
            ws = app_state_manager.get_current_workspace()
            if not ws:
                return []
            return self.conversation_service.list_conversations(
                workspace_id=ws.id,
                search=search or "",
                status=status,
                assigned_user_id=assigned_user_id,
                label_query=label_query,
                unread_only=unread_only,
                meta_account_id=meta_account_id,
            )

        return _load

    def get_load_messages_cb(self, conversation_scoped: bool = False) -> Callable:
        def _load(conversation_id: Optional[str] = None, since_timestamp: Optional[str] = None):
            ws = app_state_manager.get_current_workspace()
            if not ws:
                return []
            if conversation_scoped and not conversation_id:
                return []
            return self.message_service.get_recent_messages(
                ws.id,
                since_timestamp=since_timestamp,
                conversation_id=conversation_id,
            )

        return _load

    def get_send_message_cb(self) -> Callable:
        def _send(
            conversation_id: Optional[str],
            content: str,
            sender_id: str,
            parent_id: Optional[str] = None,
            route_wa: bool = False,
            attachment_path: Optional[str] = None,
            callback: Optional[Callable] = None
        ):
            def _worker():
                ws = app_state_manager.get_current_workspace()
                if not ws:
                    return None

                contact_id: Optional[str] = None
                target_phone: Optional[str] = None
                if conversation_id:
                    conversation = self.conversation_service.get_conversation(conversation_id)
                    if conversation:
                        contact_id = conversation.contact_id
                        target_phone = conversation.contact_phone

                if os.getenv("USE_CLOUD_API", "False").lower() == "true":
                    logger.info("Routing send_message through Cloud API...")
                    if attachment_path and os.path.exists(attachment_path):
                        data = {
                            "target_phone": target_phone or "",
                            "content": content,
                            "sender_id": sender_id,
                            "contact_id": contact_id or "",
                            "route_to_whatsapp": str(route_wa) # Form expects string
                        }
                        response = self.api_client.post_multipart("/messages/send/media", data, attachment_path)
                    else:
                        payload = {
                            "target_phone": target_phone or "",
                            "content": content,
                            "sender_id": sender_id,
                            "contact_id": contact_id or "",
                            "route_to_whatsapp": route_wa
                        }
                        response = self.api_client.post("/messages/send", payload)
                    
                    # Convert response dict to DTO matching UI expectation
                    if response:
                        if conversation_id:
                            self.conversation_service.update_on_new_message(
                                conversation_id=conversation_id,
                                preview=content,
                                message_ts=datetime.now(timezone.utc),
                                inbound=False,
                            )
                        return MessageResponseDTO(**response)
                    return None

                channel = "WHATSAPP" if route_wa else "LOCAL"
                if route_wa and not target_phone:
                    raise ValueError("Cannot route to WhatsApp without a target phone number.")

                dto = MessageCreateDTO(
                    content=content,
                    sender_id=sender_id,
                    workspace_id=ws.id,
                    conversation_id=conversation_id,
                    contact_id=contact_id,
                    parent_id=parent_id,
                    direction="OUTBOUND",
                    channel=channel,
                    route_to_whatsapp=route_wa,
                    target_phone=target_phone,
                    attachment_path=attachment_path,
                )
                sent = self.message_service.send_message(dto)
                if conversation_id:
                    self.conversation_service.update_on_new_message(
                        conversation_id=conversation_id,
                        preview=content,
                        message_ts=datetime.now(timezone.utc),
                        inbound=False,
                    )
                return sent

            self._run_async(_worker, callback=callback)

        return _send

    def get_delete_message_cb(self) -> Callable:
        return self.message_service.delete_message

    def get_toggle_star_cb(self) -> Callable:
        return self.message_service.toggle_message_star

    def get_load_contacts_cb(self) -> Callable:
        def _load():
            ws = app_state_manager.get_current_workspace()
            if not ws:
                return []
            return self.contact_service.list_contacts(ws.id)

        return _load

    def get_create_contact_cb(self) -> Callable:
        def _create(payload: Dict[str, Any]):
            ws = app_state_manager.get_current_workspace()
            if not ws:
                raise ValueError("No workspace selected.")
            dto = ContactCreateDTO(
                workspace_id=ws.id,
                phone_e164=payload.get("phone_e164", ""),
                display_name=payload.get("display_name", ""),
                email=payload.get("email"),
                lifecycle_stage=payload.get("lifecycle_stage", "LEAD"),
                owner_user_id=payload.get("owner_user_id"),
                notes=payload.get("notes", ""),
                is_whatsapp_customer=True,
            )
            return self.contact_service.create_contact(dto)

        return _create

    def get_update_contact_cb(self) -> Callable:
        def _update(contact_id: str, payload: Dict[str, Any]):
            return self.contact_service.update_contact(contact_id, **payload)

        return _update

    def get_load_labels_cb(self) -> Callable:
        def _load():
            ws = app_state_manager.get_current_workspace()
            if not ws:
                return []
            return self.label_service.list_labels(ws.id)

        return _load

    def get_create_label_cb(self) -> Callable:
        def _create(name: str, color_hex: str = "#00a884"):
            if not self._current_workspace_is_admin():
                raise PermissionError("Only admins can create labels.")
            ws = app_state_manager.get_current_workspace()
            if not ws:
                raise ValueError("No workspace selected.")
            return self.label_service.create_label(ws.id, name, color_hex)

        return _create

    def get_attach_contact_label_cb(self) -> Callable:
        return self.label_service.attach_to_contact

    def get_detach_contact_label_cb(self) -> Callable:
        return self.label_service.detach_from_contact

    def get_attach_conversation_label_cb(self) -> Callable:
        return self.label_service.attach_to_conversation

    def get_detach_conversation_label_cb(self) -> Callable:
        return self.label_service.detach_from_conversation

    def get_load_contracts_cb(self) -> Callable:
        def _load():
            ws = app_state_manager.get_current_workspace()
            if not ws:
                return []
            return self.contract_service.list_contracts(ws.id)

        return _load

    def get_create_contract_cb(self) -> Callable:
        def _create(payload: Dict[str, Any]):
            ws = app_state_manager.get_current_workspace()
            user = app_state_manager.get_current_user()
            if not ws:
                raise ValueError("No workspace selected.")

            contact_id = payload.get("contact_id")
            conversation_id = payload.get("conversation_id")

            # Resolve contact_id from conversation if not directly provided
            if not contact_id and conversation_id:
                conv = self.conversation_service.get_conversation(conversation_id)
                if conv:
                    contact_id = conv.contact_id

            if not contact_id:
                raise ValueError("Could not determine contact for contract creation.")

            dto = ContractCreateDTO(
                workspace_id=ws.id,
                contact_id=contact_id,
                title=payload.get("title"),
                contract_number=payload.get("contract_number"),
                contract_type=payload.get("contract_type", "SERVICE"),
                document_path=payload.get("document_path"),
                owner_user_id=user.id if user else None,
            )
            return self.contract_service.create_contract(dto)

        return _create

    def get_update_contract_status_cb(self) -> Callable:
        def _update(contract_id: str, new_status: str):
            return self.contract_service.update_status(contract_id, new_status)

        return _update

    def get_load_wa_settings_cb(self) -> Callable:
        def _load():
            return {
                "WA_TOKEN": self.settings_service.get_setting("WA_TOKEN", ""),
                "WA_PHONE_ID": self.settings_service.get_setting("WA_PHONE_ID", ""),
                "META_WEBHOOK_VERIFY_TOKEN": self.settings_service.get_setting(
                    "META_WEBHOOK_VERIFY_TOKEN", ""
                ),
            }

        return _load

    def get_check_wa_status_cb(self) -> Callable:
        return self.handle_check_wa_status

    def get_load_sync_settings_cb(self) -> Callable:
        def _load():
            return {"SYNC_INTERVAL": self.settings_service.get_setting("SYNC_INTERVAL", "10")}

        return _load

    def get_load_mock_settings_cb(self) -> Callable:
        def _load():
            return {"MOCK_ENABLED": self.settings_service.get_setting("MOCK_ENABLED", "1") == "1"}

        return _load

    def get_load_theme_cb(self) -> callable:
        return lambda: self.settings_service.get_setting("APP_THEME", "Dark")

    def get_load_feature_flags_cb(self) -> Callable:
        return self.get_feature_flags

    def get_accounts_cb(self) -> Callable:
        def _get():
            ws = app_state_manager.get_current_workspace()
            if ws:
                return self.meta_account_service.get_accounts(ws.id)
            return []

        return _get

    def get_load_quick_replies_cb(self) -> Callable:
        def _load():
            val = self.settings_service.get_setting("QUICK_REPLIES", "[]")
            try:
                import json
                parsed = json.loads(val)
                res = []
                for item in parsed:
                    if isinstance(item, str):
                        res.append({"text": item, "attachment_path": None})
                    else:
                        res.append(item)
                return res
            except Exception:
                return []
        return _load

    def get_save_quick_replies_cb(self) -> Callable:
        def _save(replies: List[dict]):
            import json
            self.settings_service.set_setting("QUICK_REPLIES", json.dumps(replies))
        return _save

    def get_auto_reply_rules(self, workspace_id: str):
        return self.auto_reply_service.get_rules(workspace_id)

    def create_auto_reply_rule(self, workspace_id: str, trigger: str, response: str, trigger_type: str = "exact", attachment: Optional[str] = None):
        def _worker():
            return self.auto_reply_service.create_rule(workspace_id, trigger, response, trigger_type, attachment)
        
        self._run_async(_worker, callback=lambda _: self.app_ui.auto_reply_frame.refresh_data() if self.app_ui.auto_reply_frame else None)

    def delete_auto_reply_rule(self, rule_id: str):
        def _worker():
            return self.auto_reply_service.delete_rule(rule_id)
        
        self._run_async(_worker, callback=lambda _: self.app_ui.auto_reply_frame.refresh_data() if self.app_ui.auto_reply_frame else None)

    def toggle_auto_reply_rule(self, rule_id: str):
        def _worker():
            return self.auto_reply_service.toggle_rule(rule_id)
        
        self._run_async(_worker, callback=lambda _: self.app_ui.auto_reply_frame.refresh_data() if self.app_ui.auto_reply_frame else None)
