import asyncio
from app.services.task_queue import dequeue_task
from app.services import task_store
from app.models.task import TaskStatus
import logging
import httpx
from app.api.endpoints.async_tasks import publish_task_event

logger = logging.getLogger("task_worker")

async def send_webhook_notification(task, max_retries=3):
    if not task.webhook_url:
        return
    payload = {
        "taskId": str(task.id),
        "status": task.status,
        "result": task.result,
        "error": task.error,
        "retries": task.retries,
        "max_retries": task.max_retries
    }
    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(task.webhook_url, json=payload)
                if resp.status_code < 400:
                    logger.info(f"Webhook sent for task {task.id} (attempt {attempt})")
                    return
                else:
                    logger.warning(f"Webhook for task {task.id} failed with status {resp.status_code}")
        except Exception as e:
            logger.error(f"Webhook attempt {attempt} for task {task.id} failed: {e}")
        await asyncio.sleep(2 ** attempt)  # Exponential backoff
    logger.error(f"All webhook attempts failed for task {task.id}")

async def process_task(task_id: str):
    task = await task_store.get_task(task_id)
    if not task:
        logger.error(f"Task {task_id} not found.")
        return
    try:
        # Mark as running
        task.status = TaskStatus.RUNNING
        await task_store.update_task(task)
        publish_task_event({"taskId": str(task.id), "status": task.status})
        # Simulate processing (replace with real logic)
        async def do_work():
            # For demonstration, fail if retries < 2
            if task.retries < 2:
                raise Exception("Simulated failure for retry logic")
            await asyncio.sleep(1)
            # Mark as success
            task.status = TaskStatus.SUCCESS
            task.result = {"message": "Task completed successfully"}
            await task_store.update_task(task)
            publish_task_event({"taskId": str(task.id), "status": task.status})
            await send_webhook_notification(task)
            logger.info(f"Task {task_id} completed successfully.")
        try:
            await asyncio.wait_for(do_work(), timeout=task.timeout_seconds)
        except asyncio.TimeoutError:
            raise Exception(f"Task timed out after {task.timeout_seconds} seconds")
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        task.retries += 1
        if task.retries < task.max_retries:
            await task_store.update_task(task)
            publish_task_event({"taskId": str(task.id), "status": task.status})
            await asyncio.sleep(1)
            await process_task(task_id)
        else:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            await task_store.update_task(task)
            publish_task_event({"taskId": str(task.id), "status": task.status})
            await send_webhook_notification(task)
            logger.error(f"Task {task_id} failed after max retries.")

async def start_worker(app):
    async def worker_loop():
        while True:
            task_id = await dequeue_task()
            if task_id:
                await process_task(task_id)
            else:
                await asyncio.sleep(1)
    app.add_event_handler("startup", lambda: asyncio.create_task(worker_loop())) 