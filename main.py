import customtkinter as ctk
from dotenv import load_dotenv
load_dotenv()  # Load environment variables FIRST

from typing import Any, Callable, Dict, List, Optional, Tuple
from services import UserResponseDTO, WorkspaceDTO, WorkspaceAnalyticsDTO, MetaAccountDTO, ContactDTO, ContractDTO
from state.app_state_manager import app_state_manager
from ui import ACCENT_COLOR

BG_COLOR = "#121b22"


class SmartSafeApp(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=BG_COLOR)
        self.controller = None # Will be initialized deferred
        self.title("SmartSafe v28 - Enterprise Edition")
        self.geometry("1366x768")
        self.minsize(1024, 768)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.auth_view = None
        self.main_app_frame = None
        self.sidebar_frame = None
        self.chat_frame = None
        self.inbox_frame = None
        self.dashboard_frame = None
        self.settings_frame = None
        self.address_book_frame = None
        self.contracts_frame = None
        self.kanban_frame = None
        self.audit_log_frame = None
        self.kanban_frame = None
        self.audit_log_frame = None
        self.accounts_tab = None
        self.bulk_message_tab = None
        self.template_viewer_frame = None
        self.lead_analytics_frame = None
        self.quick_replies_frame = None
        self.auto_reply_frame = None

        self.bind("<Control-k>", lambda _e: self._show_quick_switcher())
        self.bind("<Control-f>", lambda _e: self._handle_ctrl_f())
        self.bind("<Control-n>", lambda _e: self._handle_ctrl_n())

        # Start background initialization - deferred to keep startup responsive
        self.loading_label = ctk.CTkLabel(self, text="Loading SmartSafe...", font=ctk.CTkFont(size=24, weight="bold"), text_color=ACCENT_COLOR)
        self.loading_label.place(relx=0.5, rely=0.5, anchor="center")
        
        self.after(200, self._deferred_app_init)

    def _deferred_app_init(self):
        """Heavy initialization happens here after the window is drawn."""
        from core.app_controller import AppController
        self.controller = AppController(self)
        self.controller.initialize(callback=self._on_init_complete)
        self.update() # Force UI refresh

    def _on_init_complete(self):
        if self.loading_label:
            self.loading_label.destroy()
            self.loading_label = None
        self.controller.start_initial_view()

    def show_auth_view(self):
        if self.main_app_frame:
            self.main_app_frame.destroy()
            self.main_app_frame = None
            self._reset_frame_references()

        from ui import AuthView
        self.auth_view = AuthView(
            self,
            on_login_attempt=self.controller.handle_login,
            on_register_attempt=self.controller.handle_register,
        )
        self.auth_view.grid(row=0, column=0, sticky="nsew")

    def display_auth_error(self, message: str, is_login: bool):
        if not self.auth_view:
            if self.loading_label:
                self.loading_label.destroy()
                self.loading_label = None
            self.show_auth_view()
        
        if self.auth_view:
            self.auth_view.show_error(message, is_login=is_login)

    def show_main_application_view(self, user_dto: UserResponseDTO):
        if not self.controller:
             return
        
        if self.auth_view:
            self.auth_view.destroy()
            self.auth_view = None

        if self.main_app_frame:
            self.main_app_frame.destroy()
            self.main_app_frame = None
            self._reset_frame_references()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        self.main_app_frame = ctk.CTkFrame(self, fg_color=BG_COLOR)
        self.main_app_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.main_app_frame.grid_rowconfigure(0, weight=1)
        self.main_app_frame.grid_columnconfigure(0, weight=0)
        self.main_app_frame.grid_columnconfigure(1, weight=1)

        user_workspaces = self.controller.get_user_workspaces(user_dto.id)
        if not user_workspaces:
            # Fallback for new users with no workspace yet
            current_workspace = WorkspaceDTO(id="", name="No Workspace", owner_id=user_dto.id, role="ADMIN")
        else:
            current_workspace = user_workspaces[0]
            
        app_state_manager.set_current_workspace(current_workspace)
        self.current_user = user_dto
        self.current_workspace = current_workspace
        
        # Show a temporary loading state
        self.loading_label = ctk.CTkLabel(self.main_app_frame, text="Initializing SmartSafe...", font=ctk.CTkFont(size=24, weight="bold"), text_color=ACCENT_COLOR)
        self.loading_label.place(relx=0.5, rely=0.5, anchor="center")

        # Defer heavy UI creation to keep startup responsive
        self.after(100, lambda: self._deferred_ui_init(user_dto, current_workspace))

    def _deferred_ui_init(self, user_dto: UserResponseDTO, current_workspace: WorkspaceDTO):
        if hasattr(self, "loading_label") and self.loading_label:
            try:
                self.loading_label.destroy()
            except Exception:
                pass
            self.loading_label = None

        if not self.controller:
            return
        
        from core.app_controller import AppController
        flags = self.controller.get_feature_flags()
        user_workspaces = self.controller.get_user_workspaces(user_dto.id)

        # Regrid the existing main_app_frame to occupy only column 1, freeing column 0
        # for the sidebar while preserving its row and column expansion weights.
        self.main_app_frame.grid(row=0, column=1, columnspan=1, sticky="nsew")

        from ui.collapsible_sidebar import CollapsibleSidebar
        self.sidebar_frame = CollapsibleSidebar(
            self,
            current_user=user_dto,
            workspaces=user_workspaces,
            current_role=current_workspace.role if current_workspace else 'ADMIN',
            on_logout=self.destroy,
            on_workspace_select=self.controller.handle_workspace_select,
            on_dashboard_select=self.controller.handle_dashboard_select,
            on_kanban_select=self.controller.handle_kanban_select,
            on_audit_log_select=self.controller.handle_audit_log_select,
            on_settings_select=self.controller.handle_settings_select,
            on_global_search=self.controller.handle_global_search,
            on_inbox_select=self.controller.handle_inbox_select,
            on_contacts_select=self.controller.handle_contacts_select,
            on_contracts_select=self.controller.handle_contracts_select,
            on_members_select=self.controller.handle_members_select,
            on_accounts_select=self.controller.handle_accounts_select,
            on_bulk_message_select=self.controller.handle_bulk_message_select,
            on_lead_analytics_select=self.controller.handle_lead_analytics_select,
            on_quick_replies_select=self.controller.handle_quick_replies_select,
            on_auto_reply_select=self.controller.handle_auto_reply_select,
            enable_inbox_v2=flags.get(AppController.FLAG_ENABLE_INBOX_V2, True),
            enable_contacts_crm=flags.get(AppController.FLAG_ENABLE_CONTACTS_CRM, True),
            enable_contracts=flags.get(AppController.FLAG_ENABLE_CONTRACTS, True),
        )
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        if self.controller:
            self.controller.handle_workspace_select(current_workspace)

    def _reset_frame_references(self):
        """Helper to clear all frame local references."""
        self.sidebar_frame = None
        self.chat_frame = None
        self.inbox_frame = None
        self.dashboard_frame = None
        self.settings_frame = None
        self.address_book_frame = None
        self.contracts_frame = None
        self.accounts_tab = None
        self.bulk_message_tab = None
        self.template_viewer_frame = None
        self.lead_analytics_frame = None
        self.quick_replies_frame = None
        self.auto_reply_frame = None

    def _hide_all_main_content_frames(self):
        frames = [
            self.chat_frame,
            self.inbox_frame,
            self.dashboard_frame,
            self.settings_frame,
            self.address_book_frame,
            self.contracts_frame,
            self.kanban_frame,
            self.audit_log_frame,
            self.accounts_tab,
            self.bulk_message_tab,
            self.template_viewer_frame,
            self.lead_analytics_frame,
            self.quick_replies_frame,
            self.auto_reply_frame,
        ]
        for frame in frames:
            if frame:
                try:
                    frame.grid_forget()
                except Exception:
                    pass

    def update_chat_view(self, workspace: WorkspaceDTO, load_messages_cb, send_message_cb, delete_message_cb, toggle_star_cb, load_quick_replies_cb=None):
        self._hide_all_main_content_frames()
        if not self.chat_frame:
             from ui.chat_frame import ChatFrame
             self.chat_frame = ChatFrame(
                self.main_app_frame,
                current_user=self.current_user,
                current_workspace=self.current_workspace,
                load_messages_cb=load_messages_cb,
                send_message_cb=send_message_cb,
                delete_message_cb=delete_message_cb,
                toggle_star_cb=toggle_star_cb,
                load_quick_replies_cb=load_quick_replies_cb,
            )
        else:
            self.chat_frame.load_messages_cb = load_messages_cb
            self.chat_frame.send_message_cb = send_message_cb
            self.chat_frame.delete_message_cb = delete_message_cb
            self.chat_frame.toggle_star_cb = toggle_star_cb
            if load_quick_replies_cb:
                self.chat_frame.load_quick_replies_cb = load_quick_replies_cb
        
        if self.chat_frame:
            self.chat_frame.grid(row=0, column=1, sticky="nsew")
            self.chat_frame.refresh_workspace(workspace)
            if load_quick_replies_cb:
                self.chat_frame.refresh_quick_replies()

    def update_inbox_view(
        self,
        workspace: WorkspaceDTO,
        load_conversations_cb,
        load_messages_cb,
        send_message_cb,
        delete_message_cb,
        toggle_star_cb,
        load_quick_replies_cb,
        on_conversation_select_cb,
        on_assign_cb,
        on_update_status_cb,
        get_accounts_cb=None,
        load_labels_cb=None,
        attach_label_cb=None,
        detach_label_cb=None,
        create_contract_cb=None,
        archive_conversation_cb=None,
        unarchive_conversation_cb=None,
        pin_conversation_cb=None,
        unpin_conversation_cb=None,
        mute_conversation_cb=None,
        unmute_conversation_cb=None,
        delete_conversation_cb=None,
        load_contacts_cb=None,
        start_conversation_cb=None,
        get_contact_for_conversation_cb=None,
        load_starred_messages_cb=None,
        mark_read_conversation_cb=None,
    ):
        self._hide_all_main_content_frames()
        if not self.inbox_frame:
            from ui.inbox_frame import InboxFrame
            self.inbox_frame = InboxFrame(
                self.main_app_frame,
                current_user=self.current_user,
                current_workspace=self.current_workspace,
                load_conversations_cb=load_conversations_cb,
                load_messages_cb=load_messages_cb,
                send_message_cb=send_message_cb,
                delete_message_cb=delete_message_cb,
                toggle_star_cb=toggle_star_cb,
                load_quick_replies_cb=load_quick_replies_cb,
                on_conversation_select_cb=on_conversation_select_cb,
                on_assign_cb=on_assign_cb,
                on_update_status_cb=on_update_status_cb,
                get_accounts_cb=get_accounts_cb,
                load_labels_cb=load_labels_cb,
                attach_label_cb=attach_label_cb,
                detach_label_cb=detach_label_cb,
                create_contract_cb=create_contract_cb,
                archive_conversation_cb=archive_conversation_cb,
                unarchive_conversation_cb=unarchive_conversation_cb,
                pin_conversation_cb=pin_conversation_cb,
                unpin_conversation_cb=unpin_conversation_cb,
                mute_conversation_cb=mute_conversation_cb,
                unmute_conversation_cb=unmute_conversation_cb,
                delete_conversation_cb=delete_conversation_cb,
                load_contacts_cb=load_contacts_cb,
                start_conversation_cb=start_conversation_cb,
                get_contact_for_conversation_cb=get_contact_for_conversation_cb,
                load_starred_messages_cb=load_starred_messages_cb,
                mark_read_conversation_cb=mark_read_conversation_cb,
            )
        else:
            self.inbox_frame.load_conversations_cb = load_conversations_cb
            self.inbox_frame.load_messages_cb = load_messages_cb
            self.inbox_frame.send_message_cb = send_message_cb
            self.inbox_frame.delete_message_cb = delete_message_cb
            self.inbox_frame.toggle_star_cb = toggle_star_cb
            self.inbox_frame.load_quick_replies_cb = load_quick_replies_cb
            self.inbox_frame.on_conversation_select_cb = on_conversation_select_cb
            self.inbox_frame.on_assign_cb = on_assign_cb
            self.inbox_frame.on_update_status_cb = on_update_status_cb
            self.inbox_frame.get_accounts_cb = get_accounts_cb
            self.inbox_frame.load_labels_cb = load_labels_cb
            self.inbox_frame.attach_label_cb = attach_label_cb
            self.inbox_frame.detach_label_cb = detach_label_cb
            self.inbox_frame.create_contract_cb = create_contract_cb
            self.inbox_frame.archive_conversation_cb = archive_conversation_cb
            self.inbox_frame.unarchive_conversation_cb = unarchive_conversation_cb
            self.inbox_frame.pin_conversation_cb = pin_conversation_cb
            self.inbox_frame.unpin_conversation_cb = unpin_conversation_cb
            self.inbox_frame.mute_conversation_cb = mute_conversation_cb
            self.inbox_frame.unmute_conversation_cb = unmute_conversation_cb
            self.inbox_frame.delete_conversation_cb = delete_conversation_cb
            self.inbox_frame.load_contacts_cb = load_contacts_cb
            self.inbox_frame.start_conversation_cb = start_conversation_cb
            self.inbox_frame.get_contact_for_conversation_cb = get_contact_for_conversation_cb
            self.inbox_frame.load_starred_messages_cb = load_starred_messages_cb
            self.inbox_frame.mark_read_conversation_cb = mark_read_conversation_cb

        if self.inbox_frame:
            self.inbox_frame.grid(row=0, column=1, sticky="nsew")
            self.inbox_frame.refresh_workspace(workspace)

    def update_dashboard_view(self, stats: Optional[WorkspaceAnalyticsDTO], accounts: Optional[List[MetaAccountDTO]], workspace: WorkspaceDTO, loading: bool = False):
        self._hide_all_main_content_frames()
        if not self.dashboard_frame:
            from ui.dashboard_frame import DashboardFrame
            self.dashboard_frame = DashboardFrame(
                self.main_app_frame,
                refresh_account_cb=self.controller.handle_refresh_account_status,
                view_templates_cb=self.controller.handle_view_templates_select,
            )
        
        if self.dashboard_frame:
            if loading:
                self.dashboard_frame.show_loading()
            elif stats is not None and accounts is not None:
                self.dashboard_frame.refresh_data(stats, accounts, workspace)
            
            self.dashboard_frame.grid(row=0, column=1, sticky="nsew")

    def update_contacts_view(
        self,
        workspace: WorkspaceDTO,
        load_contacts_cb: Callable[[], List[Any]],
        create_contact_cb: Callable[[Dict[str, Any]], Any],
        update_contact_cb: Callable[[str, Dict[str, Any]], Any],
        load_labels_cb: Callable[[], List[Any]],
        create_label_cb: Callable[[str, str], Any],
        attach_label_cb: Callable[[str, str], bool],
        detach_label_cb: Callable[[str, str], bool],
    ):
        self._hide_all_main_content_frames()
        if not self.address_book_frame:
            from ui.address_book_frame import AddressBookFrame
            self.address_book_frame = AddressBookFrame(self.main_app_frame)

        self.address_book_frame.configure_callbacks(
            load_contacts_cb=load_contacts_cb,
            create_contact_cb=create_contact_cb,
            update_contact_cb=update_contact_cb,
            load_labels_cb=load_labels_cb,
            create_label_cb=create_label_cb,
            attach_label_cb=attach_label_cb,
            detach_label_cb=detach_label_cb,
        )
        self.address_book_frame.refresh_workspace(workspace)
        self.address_book_frame.grid(row=0, column=1, sticky="nsew")

    def update_contracts_view(
        self,
        workspace: WorkspaceDTO,
        load_contracts_cb: Callable[[], List[Any]],
        load_contacts_cb: Callable[[], List[Any]],
        create_contract_cb: Callable[[Dict[str, Any]], Any],
        update_contract_status_cb: Callable[[str, str], Any],
    ):
        self._hide_all_main_content_frames()
        if not self.contracts_frame:
            from ui.contracts_frame import ContractsFrame
            self.contracts_frame = ContractsFrame(self.main_app_frame)

        self.contracts_frame.configure_callbacks(
            load_contracts_cb=load_contracts_cb,
            load_contacts_cb=load_contacts_cb,
            create_contract_cb=create_contract_cb,
            update_contract_status_cb=update_contract_status_cb,
        )
        self.contracts_frame.refresh_workspace(workspace)
        self.contracts_frame.grid(row=0, column=1, sticky="nsew")

    def update_accounts_view(self, workspace_id: str, get_accounts_cb: Callable, add_account_cb: Callable, remove_account_cb: Callable, refresh_account_cb: Callable):
        self._hide_all_main_content_frames()
        if not self.accounts_tab:
            from ui.accounts_tab import AccountsTab
            self.accounts_tab = AccountsTab(
                self.main_app_frame,
                current_workspace_id=workspace_id,
                get_accounts_cb=get_accounts_cb,
                add_account_cb=add_account_cb,
                remove_account_cb=remove_account_cb,
                refresh_account_cb=refresh_account_cb,
            )
        else:
            self.accounts_tab.current_workspace_id = workspace_id
            self.accounts_tab.get_accounts_cb = get_accounts_cb
            self.accounts_tab.load_accounts()
        self.accounts_tab.grid(row=0, column=1, sticky="nsew")

    def update_bulk_message_view(self, get_accounts_cb: Callable, bulk_send_cb: Callable):
        self._hide_all_main_content_frames()
        if not self.bulk_message_tab:
            from ui.bulk_message_tab import BulkMessageTab
            self.bulk_message_tab = BulkMessageTab(
                self.main_app_frame, get_accounts_cb=get_accounts_cb, bulk_send_cb=bulk_send_cb
            )
        else:
            self.bulk_message_tab.get_accounts_cb = get_accounts_cb
            self.bulk_message_tab.bulk_send_cb = bulk_send_cb
            if hasattr(self.bulk_message_tab, "account_selector"):
                self.bulk_message_tab.account_selector.refresh_accounts(get_accounts_cb())
        self.bulk_message_tab.grid(row=0, column=1, sticky="nsew")

    def update_template_viewer_view(self, templates: List[Dict], account: MetaAccountDTO):
        self._hide_all_main_content_frames()
        if not self.template_viewer_frame:
            from ui.template_viewer_frame import TemplateViewerFrame
            self.template_viewer_frame = TemplateViewerFrame(
                self.main_app_frame,
                back_to_dashboard_cb=self.controller.handle_dashboard_select,
            )
        self.template_viewer_frame.refresh_data(templates, account)
        self.template_viewer_frame.grid(row=0, column=1, sticky="nsew")

    def update_lead_analytics_view(self, workspace: WorkspaceDTO, contacts: Optional[List[ContactDTO]], contracts: Optional[List[ContractDTO]], loading: bool = False):
        self._hide_all_main_content_frames()
        if not self.lead_analytics_frame:
            from ui.lead_analytics_frame import LeadAnalyticsFrame
            self.lead_analytics_frame = LeadAnalyticsFrame(self.main_app_frame)

        if loading:
            self.lead_analytics_frame.show_loading()
        elif contacts is not None and contracts is not None:
            self.lead_analytics_frame.refresh_data(workspace, contacts, contracts)
        self.lead_analytics_frame.grid(row=0, column=1, sticky="nsew")

    def update_quick_replies_view(self, load_quick_replies_cb: Callable[[], List[str]], save_quick_replies_cb: Callable[[List[str]], None]):
        self._hide_all_main_content_frames()
        if not self.quick_replies_frame:
            from ui.quick_replies_frame import QuickRepliesFrame
            self.quick_replies_frame = QuickRepliesFrame(
                self.main_app_frame,
                load_quick_replies_cb=load_quick_replies_cb,
                save_quick_replies_cb=save_quick_replies_cb
            )
        else:
            self.quick_replies_frame.load_quick_replies_cb = load_quick_replies_cb
            self.quick_replies_frame.save_quick_replies_cb = save_quick_replies_cb
        self.quick_replies_frame.refresh_data()
        self.quick_replies_frame.grid(row=0, column=1, sticky="nsew")

    def update_settings_view(
        self,
        on_save_wa_settings,
        load_wa_settings_cb,
        check_wa_status_cb,
        on_save_sync_settings,
        load_sync_settings_cb,
        on_save_mock_settings,
        load_mock_settings_cb,
        on_save_theme_cb,
        load_theme_cb,
        on_save_feature_flags_cb,
        load_feature_flags_cb,
    ):
        self._hide_all_main_content_frames()
        if not self.settings_frame:
            from ui.settings_frame import SettingsFrame
            self.settings_frame = SettingsFrame(
                self.main_app_frame,
                load_wa_settings_cb=load_wa_settings_cb,
                on_save_wa_settings=on_save_wa_settings,
                check_wa_status_cb=check_wa_status_cb,
                load_sync_settings_cb=load_sync_settings_cb,
                on_save_sync_settings=on_save_sync_settings,
                load_mock_settings_cb=load_mock_settings_cb,
                on_save_mock_settings=on_save_mock_settings,
                load_theme_cb=load_theme_cb,
                on_save_theme_cb=on_save_theme_cb,
                on_save_feature_flags_cb=on_save_feature_flags_cb,
                load_feature_flags_cb=load_feature_flags_cb,
            )
        else:
            self.settings_frame.on_save_wa_settings = on_save_wa_settings
            self.settings_frame.load_wa_settings_cb = load_wa_settings_cb
            self.settings_frame.check_wa_status_cb = check_wa_status_cb
            self.settings_frame.on_save_sync_settings = on_save_sync_settings
            self.settings_frame.load_sync_settings_cb = load_sync_settings_cb
            self.settings_frame.on_save_mock_settings = on_save_mock_settings
            self.settings_frame.load_mock_settings_cb = load_mock_settings_cb
            self.settings_frame.on_save_theme_cb = on_save_theme_cb
            self.settings_frame.load_theme_cb = load_theme_cb
            self.settings_frame.on_save_feature_flags_cb = on_save_feature_flags_cb
            self.settings_frame.load_feature_flags_cb = load_feature_flags_cb

        self.settings_frame.load_initial_settings()
        self.settings_frame.grid(row=0, column=1, sticky="nsew")

    def update_auto_reply_view(self, workspace: WorkspaceDTO):
        self._hide_all_main_content_frames()
        if not self.auto_reply_frame:
            from ui.auto_reply_frame import AutoReplyFrame
            self.auto_reply_frame = AutoReplyFrame(
                self.main_app_frame,
                current_workspace=workspace,
                controller=self.controller
            )
        else:
            self.auto_reply_frame.current_workspace = workspace
            self.auto_reply_frame.refresh_data()

        if self.auto_reply_frame:
            self.auto_reply_frame.grid(row=0, column=1, sticky="nsew")


    def update_kanban_view(self, fetch_contacts_cb, update_stage_cb):
        self._hide_all_main_content_frames()
        if not self.kanban_frame:
            from ui.kanban_frame import KanbanFrame
            self.kanban_frame = KanbanFrame(self.main_app_frame, fetch_contacts_cb=fetch_contacts_cb, update_stage_cb=update_stage_cb)
        else:
            self.kanban_frame.fetch_contacts_cb = fetch_contacts_cb
            self.kanban_frame.update_stage_cb = update_stage_cb
            
        if self.kanban_frame:
            self.kanban_frame.grid(row=0, column=1, sticky="nsew")
            self.kanban_frame.load_data()

    
    def update_audit_log_view(self, fetch_logs_cb):
        self._hide_all_main_content_frames()
        if not self.audit_log_frame:
            from ui.audit_log_frame import AuditLogFrame
            self.audit_log_frame = AuditLogFrame(self.main_app_frame, fetch_logs_cb=fetch_logs_cb)
        else:
            self.audit_log_frame.fetch_logs_cb = fetch_logs_cb
            
        if self.audit_log_frame:
            self.audit_log_frame.grid(row=0, column=1, sticky="nsew")
            self.audit_log_frame.load_data()

    def _show_quick_switcher(self):
        if not self.main_app_frame:
            return
        current_user = app_state_manager.get_current_user()
        if not current_user:
            return
        user_workspaces = self.controller.get_user_workspaces(current_user.id)
        from ui.quick_switcher import QuickSwitcher
        QuickSwitcher(self, user_workspaces, on_select=self.controller.handle_workspace_select)

    def _handle_ctrl_f(self):
        if not self.main_app_frame or not self.sidebar_frame:
            return
        self.sidebar_frame._handle_global_search_input()

    def _handle_ctrl_n(self):
        if not self.main_app_frame:
            return
        dialog = ctk.CTkInputDialog(text="Enter new workspace name:", title="New Workspace")
        name = dialog.get_input()
        if name:
            self.controller.handle_workspace_create(name)

    def destroy(self):
        if self.controller:
            self.controller.handle_logout()
        if self.main_app_frame:
            self.main_app_frame.destroy()
            self.main_app_frame = None
        super().destroy()


if __name__ == "__main__":
    app = SmartSafeApp()
    app.mainloop()
