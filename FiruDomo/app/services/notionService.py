import logging
import os

import requests


logger = logging.getLogger("firudomo.notion")
SESSION = requests.Session()

NOTION_API_KEY = os.getenv("NOTION_API_KEY") or os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID") or os.getenv("DATABASE_ID")

NOTION_TITLE_PROPERTY = os.getenv("NOTION_TITLE_PROPERTY", "Name")
NOTION_STATUS_PROPERTY = os.getenv("NOTION_STATUS_PROPERTY", "Estado")
NOTION_STATUS_TYPE = os.getenv("NOTION_STATUS_TYPE", "status").strip().lower()

DEFAULT_NEW_STATUS = os.getenv("NOTION_DEFAULT_NEW_STATUS", "pendiente")
DEFAULT_DONE_STATUS = os.getenv("NOTION_DONE_STATUS", "hecho")

STATUS_MAP = {
	"por definir": "Por definir",
	"todo": "To Do",
	"to do": "To Do",
	"en curso": "En curso",
	"bloqueada": "Bloqueada",
	"bloqueadas": "Bloqueada",
	"completada": "Completada",
	"completadas": "Completada",
	"pendiente": "pendiente",
	"hecho": "hecho",
}

_DATABASE_SCHEMA_CACHE = None


def _headers():
	return {
		"Authorization": f"Bearer {NOTION_API_KEY}",
		"Notion-Version": "2022-06-28",
		"Content-Type": "application/json",
	}


def _log_http_error(operation, response):
	body = (response.text or "").strip().replace("\n", " ")
	if len(body) > 1000:
		body = body[:1000] + "..."
	logger.error(
		"Notion %s falló | status=%s | body=%s",
		operation,
		response.status_code,
		body,
	)


def _is_invalid_status_option(response):
	if response.status_code != 400:
		return False
	body = (response.text or "").lower()
	return "invalid status option" in body


def _candidate_status_values(primary_value, fallback_values):
	values = [primary_value] + list(fallback_values)
	seen = set()
	ordered = []
	for value in values:
		if not value:
			continue
		normalized = value.strip().lower()
		if normalized in seen:
			continue
		seen.add(normalized)
		ordered.append(value)
	return ordered


def _get_database_schema():
	global _DATABASE_SCHEMA_CACHE
	if _DATABASE_SCHEMA_CACHE is not None:
		return _DATABASE_SCHEMA_CACHE

	if not _is_configured():
		return {}

	url = f"https://api.notion.com/v1/databases/{DATABASE_ID}"
	try:
		response = SESSION.get(url, headers=_headers(), timeout=20)
		if not response.ok:
			_log_http_error("get_database_schema", response)
			return {}
		_DATABASE_SCHEMA_CACHE = response.json().get("properties", {})
		return _DATABASE_SCHEMA_CACHE
	except requests.RequestException as exc:
		logger.error("Error consultando schema de Notion: %s", exc)
		return {}


def _resolve_title_property_name():
	schema = _get_database_schema()
	if not schema:
		return NOTION_TITLE_PROPERTY

	if NOTION_TITLE_PROPERTY in schema and schema[NOTION_TITLE_PROPERTY].get("type") == "title":
		return NOTION_TITLE_PROPERTY

	for prop_name, prop_data in schema.items():
		if prop_data.get("type") == "title":
			logger.info("Se usa propiedad de titulo detectada en Notion: %s", prop_name)
			return prop_name

	return NOTION_TITLE_PROPERTY


def _is_configured():
	if not NOTION_API_KEY or not DATABASE_ID:
		logger.error("Faltan variables de entorno para Notion (NOTION_API_KEY/NOTION_TOKEN o NOTION_DATABASE_ID/DATABASE_ID)")
		return False
	return True


def _status_payload(status_name):
	status_type = "select" if NOTION_STATUS_TYPE == "select" else "status"
	return {status_type: {"name": status_name}}


def _extract_task_names(results):
	tareas = []
	for result in results:
		properties = result.get("properties", {})
		title_prop = next((value for value in properties.values() if value.get("type") == "title"), None)
		if not title_prop:
			continue
		title = title_prop.get("title", [])
		name = "".join(part.get("plain_text", "") for part in title).strip()
		if name:
			tareas.append(name)
	return tareas


def create_task(title):
	if not _is_configured():
		return {"ok": False, "error": "Notion no configurado"}

	title_property = _resolve_title_property_name()
	url = "https://api.notion.com/v1/pages"
	data = {
		"parent": {"database_id": DATABASE_ID},
		"properties": {
			title_property: {
				"title": [{"text": {"content": title}}],
			},
		},
	}
	status_candidates = _candidate_status_values(DEFAULT_NEW_STATUS, ["Por definir", "To Do", "pendiente"])

	try:
		for status_value in status_candidates:
			payload = dict(data)
			payload["properties"] = dict(data["properties"])
			payload["properties"][NOTION_STATUS_PROPERTY] = _status_payload(status_value)

			response = SESSION.post(url, json=payload, headers=_headers(), timeout=20)
			if response.ok:
				return response.json()

			if _is_invalid_status_option(response):
				logger.warning("Estado '%s' no valido en Notion para create_task, se prueba otro", status_value)
				continue

			_log_http_error("create_task", response)
			return {"ok": False, "status_code": response.status_code, "error": response.text}

		# Ultimo fallback: crear sin estado para evitar bloquear /add
		response = SESSION.post(url, json=data, headers=_headers(), timeout=20)
		if response.ok:
			logger.warning("Tarea creada sin estado porque no se encontro una opcion valida")
			return response.json()

		_log_http_error("create_task", response)
		return {"ok": False, "status_code": response.status_code, "error": response.text}
	except requests.RequestException as exc:
		logger.error("Error creando tarea en Notion: %s", exc)
		return {"ok": False, "error": str(exc)}


def get_tasks():
	if not _is_configured():
		return {"ok": False, "error": "Notion no configurado", "results": []}

	url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
	try:
		response = SESSION.post(url, headers=_headers(), timeout=20)
		if not response.ok:
			_log_http_error("get_tasks", response)
			return {"ok": False, "status_code": response.status_code, "error": response.text, "results": []}
		return response.json()
	except requests.RequestException as exc:
		logger.error("Error consultando tareas en Notion: %s", exc)
		return {"ok": False, "error": str(exc), "results": []}


def update_task(page_id):
	if not _is_configured():
		return {"ok": False, "error": "Notion no configurado"}

	url = f"https://api.notion.com/v1/pages/{page_id}"
	status_candidates = _candidate_status_values(DEFAULT_DONE_STATUS, ["Completada", "Done", "hecho"])

	try:
		for status_value in status_candidates:
			data = {
				"properties": {
					NOTION_STATUS_PROPERTY: _status_payload(status_value),
				}
			}
			response = SESSION.patch(url, json=data, headers=_headers(), timeout=20)
			if response.ok:
				return response.json()

			if _is_invalid_status_option(response):
				logger.warning("Estado '%s' no valido en Notion para update_task, se prueba otro", status_value)
				continue

			_log_http_error("update_task", response)
			return {"ok": False, "status_code": response.status_code, "error": response.text}

		return {"ok": False, "error": "No se encontro un estado de completado valido en Notion"}
	except requests.RequestException as exc:
		logger.error("Error actualizando tarea en Notion: %s", exc)
		return {"ok": False, "error": str(exc)}


def get_tasks_by_status(status):
	if not _is_configured():
		return []

	normalized = status.strip().lower()
	notion_status = STATUS_MAP.get(normalized, status)
	url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

	filters_to_try = [NOTION_STATUS_TYPE]
	if NOTION_STATUS_TYPE == "status":
		filters_to_try.append("select")
	elif NOTION_STATUS_TYPE == "select":
		filters_to_try.append("status")

	for filter_type in filters_to_try:
		data = {
			"filter": {
				"property": NOTION_STATUS_PROPERTY,
				filter_type: {
					"equals": notion_status,
				},
			}
		}
		try:
			response = SESSION.post(url, headers=_headers(), json=data, timeout=20)
		except requests.RequestException as exc:
			logger.error("Error Notion en filtro de estado: %s", exc)
			return []

		if response.status_code == 200:
			payload = response.json()
			return _extract_task_names(payload.get("results", []))

		_log_http_error(f"get_tasks_by_status[{filter_type}]", response)

	return []

