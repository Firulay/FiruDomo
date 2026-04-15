import logging
import os
import sys
import asyncio
from pathlib import Path

from dotenv import load_dotenv
from telegram import BotCommand, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# =========================
# CONFIG
# =========================
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    print("❌ ERROR: TELEGRAM_TOKEN no encontrado en .env")
    print(f"   Directorio actual: {os.getcwd()}")
    print(f"   Archivos: {os.listdir('.')}")
    sys.exit(1)

# =========================
# LOGGING
# =========================
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("firudomo")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("telegram.ext.Application").setLevel(logging.INFO)
logging.getLogger("telegram.ext.Updater").setLevel(logging.INFO)

from app.handlers.commands import add_task, check_command, done_task, list_tasks, start
from app.handlers.commands import help_command
from app.services.notionService import get_tasks_by_status
from app.services.reminder_service import schedule_daily_reminders
from app.utils.logging_helpers import log_received_command


# =========================
# COMANDOS
# =========================

@log_received_command
async def por_definir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = await asyncio.to_thread(get_tasks_by_status, "Por definir")
    msg = "\n".join(f"• {t}" for t in tasks) if tasks else "No hay tareas"
    await update.message.reply_text(f"🟡 Por definir:\n{msg}")


@log_received_command
async def todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = await asyncio.to_thread(get_tasks_by_status, "To Do")
    msg = "\n".join(f"• {t}" for t in tasks) if tasks else "No hay tareas"
    await update.message.reply_text(f"🔵 To Do:\n{msg}")


@log_received_command
async def en_curso(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = await asyncio.to_thread(get_tasks_by_status, "En curso")
    msg = "\n".join(f"• {t}" for t in tasks) if tasks else "No hay tareas"
    await update.message.reply_text(f"🧠 En curso:\n{msg}")


@log_received_command
async def bloqueadas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = await asyncio.to_thread(get_tasks_by_status, "Bloqueada")
    msg = "\n".join(f"• {t}" for t in tasks) if tasks else "No hay tareas"
    await update.message.reply_text(f"⛔ Bloqueadas:\n{msg}")


@log_received_command
async def completadas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = await asyncio.to_thread(get_tasks_by_status, "Completada")
    msg = "\n".join(f"• {t}" for t in tasks) if tasks else "No hay tareas"
    await update.message.reply_text(f"✅ Completadas:\n{msg}")


# =========================
# ERROR HANDLER
# =========================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Error no controlado", exc_info=context.error)


# =========================
# MAIN
# =========================
def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("Falta TELEGRAM_TOKEN en variables de entorno")

    async def post_init(application):
        await application.bot.set_my_commands(
            [
                BotCommand("start", "Inicia el bot"),
                BotCommand("help", "Muestra la ayuda"),
                BotCommand("check", "Lanza el recordatorio ahora"),
                BotCommand("add", "Añade una tarea"),
                BotCommand("list", "Lista todas las tareas"),
                BotCommand("done", "Marca una tarea como hecha"),
                BotCommand("pordefinir", "Tareas por definir"),
                BotCommand("todo", "Tareas To Do"),
                BotCommand("curso", "Tareas en curso"),
                BotCommand("bloqueadas", "Tareas bloqueadas"),
                BotCommand("completadas", "Tareas completadas"),
            ]
        )

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("check", check_command))
    app.add_handler(CommandHandler("add", add_task))
    app.add_handler(CommandHandler("list", list_tasks))
    app.add_handler(CommandHandler("done", done_task))

    app.add_handler(CommandHandler("pordefinir", por_definir))
    app.add_handler(CommandHandler("todo", todo))
    app.add_handler(CommandHandler("curso", en_curso))
    app.add_handler(CommandHandler("bloqueadas", bloqueadas))
    app.add_handler(CommandHandler("completadas", completadas))

    app.add_error_handler(error_handler)
    schedule_daily_reminders(app)

    logger.info("Bot iniciado y escuchando comandos")
    logger.info("Token cargado desde %s", BASE_DIR / ".env")
    app.run_polling()


if __name__ == "__main__":
    main()