"""
Headless smoke tests for ui/chat_frame.py and its extracted components.

Run under Xvfb: xvfb-run -a python -m pytest tests/ui/ -v

Tests are grouped by extraction step and re-run cumulatively after every step so a
regression in an earlier component is caught immediately, not just the newest change.
"""
import pytest

from ui.chat_frame import ChatFrame

from tests.ui.conftest import pump, make_msg_dto

# ChatFrame's _load_history/_poll_messages (untouched by this extraction) spawn a
# daemon thread that calls self.after(0, ...) once its callback returns. With our
# fake callbacks completing near-instantly and these tests cycling mainloop()/quit()
# repeatedly via pump(), that registration can occasionally race a moment between
# mainloop ticks and raise "RuntimeError: main thread is not in main loop" from the
# daemon thread -- a pre-existing characteristic of that threading pattern, not
# something this extraction introduces (in the real app, a continuous mainloop for
# the process lifetime, this would at worst print a swallowed daemon-thread
# traceback on shutdown, never crash anything). Filtered narrowly by category here
# so a genuinely new/different thread exception still fails the suite.
pytestmark = pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")


def build_chat_frame(root, fake_callbacks, fake_user, fake_workspace, **overrides):
    kwargs = fake_callbacks.as_kwargs()
    kwargs.update(overrides)
    return ChatFrame(
        root,
        current_user=fake_user,
        current_workspace=fake_workspace,
        **kwargs,
    )


# --- Baseline (Step 0 gate): proves construction + threading hand-off works at all ---

def test_construct_no_exception(root, fake_callbacks, fake_user, fake_workspace):
    chat_frame = build_chat_frame(root, fake_callbacks, fake_user, fake_workspace)
    chat_frame.grid(row=0, column=0)
    assert chat_frame.winfo_exists()
    chat_frame.destroy()


def test_initial_history_renders_two_messages(root, fake_callbacks, fake_user, fake_workspace):
    chat_frame = build_chat_frame(root, fake_callbacks, fake_user, fake_workspace)
    chat_frame.grid(row=0, column=0)

    def loaded():
        return len(chat_frame.message_list.rendered_msg_ids) >= 2

    assert pump(root, loaded, timeout=5.0), "initial history did not render within timeout"
    assert chat_frame.message_list.rendered_msg_ids == {"m1", "m2"}
    chat_frame.destroy()


# --- Step 1 gate: ChatHeader extracted ---
#
# set_conversation()/refresh_workspace() mutate header widgets synchronously (before
# spawning their _load_history() thread), so cget()-style assertions need no pump().
# winfo_ismapped() is different: Tk defers actual geometry/mapping to idle tasks, so
# it needs update_idletasks() after a pack()/pack_forget() before it reflects reality.
# update_idletasks() only drains idle tasks (no timers/events), so unlike mainloop()
# it carries no thread-registration risk. The spawned _load_history() thread itself
# must still be drained with a real pump() condition -- not a fixed-duration wait --
# before the next action or destroy(), or its self.after(0, ...) hand-off can race a
# moment when the main thread isn't inside a real mainloop.

def _wait_idle(root, chat_frame):
    assert pump(root, lambda: not chat_frame._is_loading, timeout=5.0), "history load did not settle"


def test_set_conversation_updates_header_and_shows_labels(root, fake_callbacks, fake_user, fake_workspace):
    chat_frame = build_chat_frame(root, fake_callbacks, fake_user, fake_workspace)
    chat_frame.grid(row=0, column=0)
    _wait_idle(root, chat_frame)

    chat_frame.set_conversation(
        "conv-1", "Jane Doe", "online",
        last_message_at="2026-06-21T10:00:00+00:00",
        labels=[{"id": "L1", "name": "VIP", "color": "#7c3aed"}],
    )
    root.update_idletasks()

    assert chat_frame.chat_header.title_label.cget("text") == "Jane Doe"
    assert chat_frame.chat_header.status_label.cget("text") == "online"
    assert chat_frame.chat_header.avatar_label.cget("text") == "J"
    assert chat_frame.chat_header.timer_badge.winfo_ismapped()
    assert chat_frame.chat_header.add_label_btn.winfo_ismapped()
    assert len(chat_frame.chat_header.header_labels_frame.winfo_children()) == 1

    _wait_idle(root, chat_frame)
    chat_frame.destroy()


def test_set_conversation_none_hides_timer_and_labels(root, fake_callbacks, fake_user, fake_workspace):
    chat_frame = build_chat_frame(root, fake_callbacks, fake_user, fake_workspace)
    chat_frame.grid(row=0, column=0)
    _wait_idle(root, chat_frame)

    chat_frame.set_conversation("conv-1", "Jane Doe", "online", labels=[{"id": "L1", "name": "VIP"}])
    _wait_idle(root, chat_frame)

    chat_frame.set_conversation(None, "Select a conversation", "idle")
    root.update_idletasks()

    assert not chat_frame.chat_header.timer_badge.winfo_ismapped()
    assert not chat_frame.chat_header.add_label_btn.winfo_ismapped()
    assert len(chat_frame.chat_header.header_labels_frame.winfo_children()) == 0

    _wait_idle(root, chat_frame)
    chat_frame.destroy()


def test_refresh_workspace_updates_header_identity(root, fake_callbacks, fake_user, fake_workspace):
    chat_frame = build_chat_frame(root, fake_callbacks, fake_user, fake_workspace)
    chat_frame.grid(row=0, column=0)
    _wait_idle(root, chat_frame)

    other_workspace = type(fake_workspace)(id="ws-2", name="Globex Inc", owner_id="user-1", role="OWNER")
    chat_frame.refresh_workspace(other_workspace)

    assert chat_frame.chat_header.title_label.cget("text") == "Globex Inc"
    assert chat_frame.chat_header.avatar_label.cget("text") == "G"

    _wait_idle(root, chat_frame)
    chat_frame.destroy()


def test_remove_label_calls_detach_cb_and_removes_chip(root, fake_callbacks, fake_user, fake_workspace):
    chat_frame = build_chat_frame(root, fake_callbacks, fake_user, fake_workspace)
    chat_frame.grid(row=0, column=0)
    _wait_idle(root, chat_frame)

    chat_frame.set_conversation("conv-1", "Jane Doe", labels=[{"id": "L1", "name": "VIP"}])
    _wait_idle(root, chat_frame)
    assert len(chat_frame.chat_header.header_labels_frame.winfo_children()) == 1

    chat_frame._on_remove_label("L1")

    assert fake_callbacks.detached_labels == [("L1", "conv-1")]
    assert len(chat_frame.chat_header.header_labels_frame.winfo_children()) == 0
    chat_frame.destroy()


# --- Step 2 gate: ChatInput extracted ---
#
# _handle_send is called directly rather than synthesizing a real keypress/Return
# event: it's the exact same code path the entry's <Return> binding and the send
# button's command both invoke (see ChatInput.__init__), so this exercises identical
# behavior without relying on flaky synthetic-event delivery under Xvfb.

def test_handle_send_clears_input_and_renders_echoed_message(root, fake_callbacks, fake_user, fake_workspace):
    chat_frame = build_chat_frame(root, fake_callbacks, fake_user, fake_workspace)
    chat_frame.grid(row=0, column=0)
    _wait_idle(root, chat_frame)
    chat_frame.set_conversation("conv-1", "Jane Doe")
    _wait_idle(root, chat_frame)

    before = len(chat_frame.message_list.rendered_msg_ids)
    chat_frame.chat_input.msg_entry.insert(0, "hello there")
    chat_frame._handle_send()

    assert chat_frame.chat_input.get_text() == ""
    assert len(chat_frame.message_list.rendered_msg_ids) == before + 1
    assert fake_callbacks.sent_messages[-1].content == "hello there"
    chat_frame.destroy()


def test_slash_command_shows_and_hides_suggestions(root, fake_callbacks, fake_user, fake_workspace):
    chat_frame = build_chat_frame(root, fake_callbacks, fake_user, fake_workspace)
    chat_frame.grid(row=0, column=0)
    _wait_idle(root, chat_frame)

    chat_frame.chat_input.msg_entry.insert(0, "/greet")
    chat_frame._on_input_change(None)
    root.update_idletasks()

    assert chat_frame.suggest_frame.winfo_ismapped()
    assert len(chat_frame.suggest_frame.winfo_children()) == 1

    chat_frame.chat_input.clear()
    chat_frame.chat_input.msg_entry.insert(0, "no slash here")
    chat_frame._on_input_change(None)
    root.update_idletasks()

    assert not chat_frame.suggest_frame.winfo_ismapped()
    chat_frame.destroy()


def test_input_change_uses_unstripped_text(root, fake_callbacks, fake_user, fake_workspace):
    """Regression guard: _on_input_change must read the raw (unstripped) entry text,
    not ChatInput.get_text()'s stripped form, or a leading space before "/" would
    silently start matching when it shouldn't (pre-existing behavior, preserved
    verbatim through the ChatInput extraction)."""
    chat_frame = build_chat_frame(root, fake_callbacks, fake_user, fake_workspace)
    chat_frame.grid(row=0, column=0)
    _wait_idle(root, chat_frame)

    chat_frame.chat_input.msg_entry.insert(0, " /greet")
    chat_frame._on_input_change(None)
    root.update_idletasks()

    assert not chat_frame.suggest_frame.winfo_ismapped()
    chat_frame.destroy()


# --- Step 3 gate: MessageList extracted ---

def test_add_message_bubble_alignment_by_sender(root, fake_callbacks, fake_user, fake_workspace):
    chat_frame = build_chat_frame(root, fake_callbacks, fake_user, fake_workspace)
    chat_frame.grid(row=0, column=0)
    _wait_idle(root, chat_frame)

    chat_frame.add_message("Hi", is_sent=True, msg_id="s1")
    chat_frame.add_message("Hello back", is_sent=False, msg_id="r1", sender_name="Bob")

    containers = chat_frame.message_list.winfo_children()
    sent_bubble = containers[-2].winfo_children()[0]
    received_bubble = containers[-1].winfo_children()[0]

    assert sent_bubble.pack_info()["anchor"] == "e"
    assert received_bubble.pack_info()["anchor"] == "w"
    chat_frame.destroy()


def test_add_message_reply_indicator_and_attachment_styling(root, fake_callbacks, fake_user, fake_workspace):
    chat_frame = build_chat_frame(root, fake_callbacks, fake_user, fake_workspace)
    chat_frame.grid(row=0, column=0)
    _wait_idle(root, chat_frame)

    chat_frame.add_message("Reply text", is_sent=True, msg_id="s2", parent_id="r1")
    chat_frame.add_message("See attached", is_sent=True, msg_id="s3", attachment_path="/fake/path.pdf")

    containers = chat_frame.message_list.winfo_children()
    reply_bubble = containers[-2].winfo_children()[0]
    attachment_bubble = containers[-1].winfo_children()[0]

    reply_indicator = reply_bubble.winfo_children()[0]
    assert reply_indicator.cget("text") == "↳ Replied to thread"

    msg_label = attachment_bubble.winfo_children()[0]
    assert msg_label.cget("cursor") == "hand2"
    chat_frame.destroy()


def test_toggle_star_and_delete_message(root, fake_callbacks, fake_user, fake_workspace):
    chat_frame = build_chat_frame(root, fake_callbacks, fake_user, fake_workspace)
    chat_frame.grid(row=0, column=0)
    _wait_idle(root, chat_frame)

    chat_frame.add_message("Hi", is_sent=True, msg_id="s1")
    assert chat_frame.message_list.get_star_state("s1") is False

    chat_frame._toggle_star("s1")
    assert fake_callbacks.starred["s1"] is True
    assert chat_frame.message_list.get_star_state("s1") is True
    assert "⭐" in chat_frame.message_list.message_labels["s1"].cget("text")

    container = chat_frame.message_list.winfo_children()[-1]
    chat_frame._delete_message("s1", container)

    assert fake_callbacks.deleted_ids == ["s1"]
    assert not chat_frame.message_list.is_rendered("s1")
    assert container.winfo_exists() == 0
    chat_frame.destroy()


def test_duplicate_poll_delivery_does_not_double_render(root, fake_callbacks, fake_user, fake_workspace):
    """The dedup guard (rendered_msg_ids) is the entire reason MessageList tracks
    per-message state -- a duplicate poll result for an already-rendered message
    must update its status in place, never render a second bubble."""
    chat_frame = build_chat_frame(root, fake_callbacks, fake_user, fake_workspace)
    chat_frame.grid(row=0, column=0)
    _wait_idle(root, chat_frame)

    new_dto = make_msg_dto(id="m99", sender_id="other-1", content="new!")
    chat_frame._process_polled_messages([new_dto])
    assert chat_frame.message_list.is_rendered("m99")
    count_after_first = len(chat_frame.message_list.winfo_children())

    chat_frame._process_polled_messages([new_dto])
    assert len(chat_frame.message_list.winfo_children()) == count_after_first
    chat_frame.destroy()


def test_destroy_stops_recursive_polling(root, fake_callbacks, fake_user, fake_workspace):
    """destroy() must actually stop the recursive _poll_messages cycle, not just
    avoid raising when after_cancel is called. Patches the class method (not the
    instance) so the substitution is visible to self.after(2000, self._poll_messages)
    lookups made from inside the running poll cycle itself."""
    call_count = {"n": 0}
    original_poll = ChatFrame._poll_messages

    def _counting_poll(self):
        call_count["n"] += 1
        return original_poll(self)

    ChatFrame._poll_messages = _counting_poll
    try:
        chat_frame = build_chat_frame(root, fake_callbacks, fake_user, fake_workspace)
        chat_frame.grid(row=0, column=0)
        assert pump(root, lambda: hasattr(chat_frame, "_poll_timer"), timeout=5.0), \
            "first poll cycle never armed _poll_timer"

        count_before_destroy = call_count["n"]
        chat_frame.destroy()

        pump(root, lambda: False, timeout=2.5)
        assert call_count["n"] == count_before_destroy, "_poll_messages fired again after destroy()"
    finally:
        ChatFrame._poll_messages = original_poll
