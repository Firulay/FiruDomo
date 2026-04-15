import asyncio
import logging
import os
from datetime import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.services.notionService import get_tasks_by_status
from app.utils.chat_registry import load_chat_ids

logger = logging.getLogger("firudomo.reminders")


def _load_timezone():
    timezone_name = os.getenv("REMINDER_TIMEZONE", "Europe/Madrid")
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        logger.warning("Zona horaria invalida '%s'. Se usa UTC.", timezone_name)
        return ZoneInfo("UTC")


def _build_reminder_message(todo, en_curso, bloqueadas):
    todo_msg = "\n".join(f"- {item}" for item in todo) if todo else "- Sin tareas"
    curso_msg = "\n".join(f"- {item}" for item in en_curso) if en_curso else "- Sin tareas"
    bloqueadas_msg = "\n".join(f"- {item}" for item in bloqueadas) if bloqueadas else "- Sin tareas"

    return (
        "Recordatorio de tareas\n\n"
        f"To Do:\n{todo_msg}\n\n"
        f"En curso:\n{curso_msg}\n\n"
        f"Bloqueadas:\n{bloqueadas_msg}"
    )


def _load_target_chats():
    chat_ids = load_chat_ids()
    configured_chat = os.getenv("TELEGRAM_CHAT_ID")

    if configured_chat:
        try:
            chat_ids.add(int(configured_chat))
        except ValueError:
            logger.warning("TELEGRAM_CHAT_ID no es valido: %s", configured_chat)

    return chat_ids


async def send_daily_reminder(context):
    chat_ids = _load_target_chats()
    if not chat_ids:
        logger.info("No hay chats registrados para recordatorios")
        return

    message = await get_daily_reminder_text()
    for chat_id in sorted(chat_ids):
        try:
            await context.bot.send_message(chat_id=chat_id, text=message)
            logger.info("Recordatorio enviado a chat %s", chat_id)
        except Exception as exc:
            logger.error("No se pudo enviar recordatorio a chat %s: %s", chat_id, exc)


async def get_daily_reminder_text():
    todo, en_curso, bloqueadas = await asyncio.gather(
        asyncio.to_thread(get_tasks_by_status, "To Do"),
        asyncio.to_thread(get_tasks_by_status, "En curso"),
        asyncio.to_thread(get_tasks_by_status, "Bloqueada"),
    )

    return _build_reminder_message(todo, en_curso, bloqueadas)


def schedule_daily_reminders(application):
    if not application.job_queue:
        logger.warning("JobQueue no disponible. Instala APScheduler para recordatorios.")
        return

    tz = _load_timezone()
    schedule = [
        ("daily-reminder-0700", time(hour=7, minute=0, tzinfo=tz)),
        ("daily-reminder-1230", time(hour=12, minute=30, tzinfo=tz)),
        ("daily-reminder-1800", time(hour=18, minute=0, tzinfo=tz)),
    ]

    for name, when in schedule:
        application.job_queue.run_daily(send_daily_reminder, time=when, name=name)
        logger.info("Recordatorio programado: %s (%s)", name, when)

