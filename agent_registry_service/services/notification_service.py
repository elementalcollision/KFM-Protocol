import logging
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from tenacity.before_sleep import before_sleep_log

logger = logging.getLogger(__name__)

class NotificationService:
    """Handles sending webhook notifications with retry logic."""
    
    def __init__(self, timeout: int = 10, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = httpx.AsyncClient(timeout=self.timeout)
        logger.info(f"Initialized NotificationService (timeout={timeout}s, max_retries={max_retries})")

    @retry(
        stop=stop_after_attempt(4), # Corresponds to max_retries=3 (initial + 3 retries)
        wait=wait_exponential(multiplier=1, min=1, max=10), # Wait 1s, 2s, 4s
        retry=retry_if_exception_type((httpx.RequestError, httpx.Timeout, httpx.HTTPStatusError)), # Retry on connection errors, timeouts, 5xx
        before_sleep=before_sleep_log(logger, logging.WARNING), # Log before retrying
        reraise=True # Reraise the exception if all retries fail
    )
    async def send_webhook_notification(self, url: str, payload: dict):
        """Sends a payload to a webhook URL with retry."""
        logger.info(f"Sending webhook notification to {url}")
        logger.debug(f"Webhook payload: {payload}")
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status() # Raise for 4xx/5xx responses after retries
            logger.info(f"Webhook notification successful for {url} (Status: {response.status_code})")
        except httpx.RequestError as exc:
            logger.error(f"Webhook connection error for {url}: {exc}")
            raise # Reraise for tenacity
        except httpx.HTTPStatusError as exc:
            logger.error(f"Webhook HTTP error for {url}: Status {exc.response.status_code}, Response: {exc.response.text}")
            if 400 <= exc.response.status_code < 500:
                # Don't retry client errors (4xx) - treat as failure
                raise # Reraise to stop retries
            raise # Reraise server errors (5xx) for tenacity
        except Exception as exc:
             logger.error(f"Unexpected error sending webhook to {url}: {exc}", exc_info=True)
             raise # Reraise for tenacity

# Example usage (dependency injection pattern)
# notification_service = NotificationService()
# def get_notification_service():
#    return notification_service 