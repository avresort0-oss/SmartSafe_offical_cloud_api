from typing import List
from sqlalchemy.orm import Session
import logging

from core.repository import BaseRepository
from core.repositories.message_repository import MessageRepository
from core.models.message import Message
from core.models.cloud_message import CloudMessage # Cloud model for remote persistence
from core.database import SessionLocal # For cloud session (simulated)

logger = logging.getLogger(__name__)

class SyncService:
    """
    Orchestrates the offline-first data synchronization between local SQLite
    and the simulated SmartSafe Cloud API.
    """
    def __init__(self):
        pass

    def push_unsynced_messages(self) -> int:
        """
        Identifies and pushes unsynced messages from local to cloud.
        Returns the count of successfully synced messages.
        """
        with SessionLocal() as local_session, SessionLocal() as cloud_session:
            local_repo = MessageRepository(local_session)
            cloud_repo = BaseRepository(cloud_session, CloudMessage)

            unsynced_messages = local_repo.get_unsynced_messages()
            synced_count = 0
            synced_ids = []
            
            for msg in unsynced_messages:
                # Simulate sending to cloud (e.g., HTTP POST to a cloud API endpoint)
                try:
                    existing = cloud_session.query(CloudMessage).filter_by(id=msg.id).first()
                    if not existing:
                        cloud_msg = CloudMessage(
                            id=msg.id,
                            content=msg.content,
                            sender_id=msg.sender_id,
                            workspace_id=msg.workspace_id,
                            conversation_id=msg.conversation_id,
                            contact_id=msg.contact_id,
                            parent_id=msg.parent_id,
                            attachment_path=msg.attachment_path,
                            direction=msg.direction,
                            channel=msg.channel,
                            external_message_id=msg.external_message_id,
                            is_deleted=msg.is_deleted,
                        )
                        cloud_repo.add(cloud_msg) # Simulate cloud persistence
                    synced_ids.append(msg.id)
                    synced_count += 1
                except Exception as e:
                    logger.error(f"Failed to sync message {msg.id}: {e}")
            
            if synced_ids:
                local_repo.mark_as_synced(synced_ids)
            return synced_count

    def push_deletions(self) -> int:
        """Pushes soft-deleted messages to the cloud and hard-deletes them locally."""
        with SessionLocal() as local_session, SessionLocal() as cloud_session:
            local_repo = MessageRepository(local_session)
            cloud_repo = BaseRepository(cloud_session, CloudMessage)
            unsynced_deletions = local_repo.get_unsynced_deletions()
            deleted_ids = [msg.id for msg in unsynced_deletions]
            if deleted_ids:
                # Simulate cloud deletion confirmation (e.g., API call)
                for msg_id in deleted_ids:
                    cloud_repo.delete(msg_id)
                local_repo.hard_delete_synced_deletions(deleted_ids)
            return len(deleted_ids)
