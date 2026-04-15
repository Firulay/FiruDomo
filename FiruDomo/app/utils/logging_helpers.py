import logging
from functools import wraps

from app.utils.chat_registry import register_chat_id

logger = logging.getLogger("firudomo.commands")


def log_received_command(func):
	@wraps(func)
	async def wrapper(update, context, *args, **kwargs):
		message = getattr(update, "message", None)
		text = getattr(message, "text", "") or ""
		user = getattr(getattr(update, "effective_user", None), "username", None)
		user_id = getattr(getattr(update, "effective_user", None), "id", None)
		chat_id = getattr(getattr(update, "effective_chat", None), "id", None)

		logger.info(
			"Comando recibido: %s | user=%s(%s) | chat=%s",
			text,
			user or "sin_usuario",
			user_id or "sin_id",
			chat_id or "sin_chat",
		)
		if chat_id is not None:
			register_chat_id(chat_id)
		return await func(update, context, *args, **kwargs)

	return wrapper

