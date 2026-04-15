import logging
import asyncio

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger("firudomo.handlers")

from app.services.notionService import create_task, get_tasks, update_task
from app.services.reminder_service import get_daily_reminder_text
from app.utils.logging_helpers import log_received_command


def _extract_title(properties):
	title_prop = next((value for value in properties.values() if value.get("type") == "title"), None)
	if not title_prop:
		return "Sin titulo"
	title_parts = title_prop.get("title", [])
	return "".join(part.get("plain_text", "") for part in title_parts).strip() or "Sin titulo"


def _extract_status(properties):
	for value in properties.values():
		if value.get("type") == "status" and value.get("status"):
			return value["status"].get("name", "Sin estado")
		if value.get("type") == "select" and value.get("select"):
			return value["select"].get("name", "Sin estado")
	return "Sin estado"


def _normalize_tasks(raw_tasks):
	normalized = []
	for task in raw_tasks:
		properties = task.get("properties", {})
		normalized.append(
			{
				"id": task.get("id", ""),
				"title": _extract_title(properties),
				"status": _extract_status(properties),
			}
		)
	return normalized


@log_received_command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
	logger.info("Comando /start procesado")
	await update.message.reply_text("Bot de tareas activo 🚀")


@log_received_command
async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
	title = " ".join(context.args)

	if not title:
		await update.message.reply_text("Usa: /add Comprar pan")
		return

	result = await asyncio.to_thread(create_task, title)
	if not result or result.get("ok") is False:
		await update.message.reply_text("No se pudo crear la tarea en Notion. Revisa logs para detalle.")
		return

	await update.message.reply_text(f"Tarea añadida: {title}")


@log_received_command
async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
	data = await asyncio.to_thread(get_tasks)

	tasks = _normalize_tasks(data.get("results", []))

	if not tasks:
		await update.message.reply_text("No hay tareas")
		return

	message = ""

	for index, task in enumerate(tasks, start=1):
		message += f"{index}. {task['title']} - {task['status']}\n"

	await update.message.reply_text(message)


@log_received_command
async def done_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
	if not context.args:
		await update.message.reply_text("Usa: /done <numero o texto>")
		return

	task_query = " ".join(context.args).strip()

	data = await asyncio.to_thread(get_tasks)
	tasks = _normalize_tasks(data.get("results", []))

	if not tasks:
		await update.message.reply_text("No hay tareas para marcar")
		return

	selected = None
	if task_query.isdigit():
		index = int(task_query) - 1
		if 0 <= index < len(tasks):
			selected = tasks[index]
		else:
			await update.message.reply_text("Numero fuera de rango. Usa /list para ver el orden.")
			return
	else:
		matches = [task for task in tasks if task_query.lower() in task["title"].lower()]
		if not matches:
			await update.message.reply_text("No encontre tareas con ese texto. Usa /list y luego /done <numero>.")
			return
		if len(matches) > 1:
			options = "\n".join(f"- {task['title']}" for task in matches[:5])
			await update.message.reply_text(
				"Hay varias tareas que coinciden. Usa /done <numero> tras /list.\n\n" + options
			)
			return
		selected = matches[0]

	result = await asyncio.to_thread(update_task, selected["id"])
	if result and result.get("ok") is False:
		await update.message.reply_text("No se pudo actualizar la tarea en Notion. Revisa logs.")
		return

	await update.message.reply_text(f"Tarea marcada como hecha ✅: {selected['title']}")


@log_received_command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
	await update.message.reply_text(
		"Comandos disponibles:\n\n"
		"/start - Inicia el bot\n"
		"/help - Muestra esta ayuda\n"
		"/check - Lanza el recordatorio ahora\n"
		"/add <tarea> - Añade una tarea\n"
		"/list - Lista todas las tareas\n"
		"/done <numero o texto> - Marca una tarea como hecha\n"
		"/pordefinir - Tareas por definir\n"
		"/todo - Tareas To Do\n"
		"/curso - Tareas en curso\n"
		"/bloqueadas - Tareas bloqueadas\n"
		"/completadas - Tareas completadas"
	)


@log_received_command
async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
	message = await get_daily_reminder_text()
	await update.message.reply_text(message)


