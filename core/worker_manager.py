import logging
from services.offline_sync_worker import OfflineSyncWorker
from integrations.mock_wa_webhook_worker import MockWAWebhookWorker
from integrations.whatsapp_integration import WhatsAppIntegration
from services.mock_message_worker import MockMessageWorker
from services.webhook_receiver_worker import WebhookReceiverWorker

logger = logging.getLogger(__name__)

class WorkerManager:
    """
    Manages the lifecycle of all background daemon threads.
    Accepts dependencies to inject them into workers.
    """
    def __init__(self, whatsapp_integration: WhatsAppIntegration, sync_interval: int = 10, mock_enabled: bool = True, webhook_verify_token: str = ""):
        # Instantiate workers and inject their dependencies
        self.offline_sync_worker = OfflineSyncWorker(interval_seconds=sync_interval)
        self.mock_wa_webhook_worker = MockWAWebhookWorker(
            interval_seconds=25,
            whatsapp_integration=whatsapp_integration
        )
        self.mock_message_worker = MockMessageWorker()
        
        self.real_webhook_worker = WebhookReceiverWorker(whatsapp_integration=whatsapp_integration, port=8080, verify_token=webhook_verify_token)
        
        self.workers = [
            self.offline_sync_worker,
            self.real_webhook_worker
        ]
        if mock_enabled:
            self.workers.append(self.mock_wa_webhook_worker)
            self.workers.append(self.mock_message_worker)
            
        logger.info("WorkerManager initialized.")

    def start_all(self):
        """Starts all registered background workers."""
        logger.info("Starting all background workers...")
        for worker in self.workers:
            worker.start()
        logger.info("All background workers started.")

    def stop_all(self):
        """Stops all registered background workers gracefully."""
        logger.info("Stopping all background workers...")
        for worker in self.workers:
            worker.stop()
        logger.info("All background workers stopped.")