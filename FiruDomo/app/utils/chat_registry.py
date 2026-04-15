import json
import logging
from pathlib import Path

logger = logging.getLogger("firudomo.reminders")

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
REGISTRY_FILE = DATA_DIR / "reminder_chats.json"


def _load_registry():
    if not REGISTRY_FILE.exists():
        return []

    try:
        payload = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("No se pudo leer el registro de chats: %s", exc)
        return []

    if isinstance(payload, list):
        return payload
    return []


def load_chat_ids():
    return {int(item) for item in _load_registry()}


def register_chat_id(chat_id):
    try:
        chat_id_int = int(chat_id)
    except (TypeError, ValueError):
        return False

    chat_ids = load_chat_ids()
    if chat_id_int in chat_ids:
        return False

    chat_ids.add(chat_id_int)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(json.dumps(sorted(chat_ids), indent=2), encoding="utf-8")
    logger.info("Chat registrado para recordatorios: %s", chat_id_int)
    return True

