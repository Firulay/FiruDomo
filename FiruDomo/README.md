# FiruDomo Bot

Bot de Telegram para gestionar tareas en Notion.

## Requisitos

- Python 3.11+
- Entorno virtual (`.venv`)

## Variables de entorno

Crea un archivo `.env` en la raiz del proyecto:

```env
TELEGRAM_TOKEN=tu_token_telegram
NOTION_TOKEN=tu_token_notion
NOTION_DATABASE_ID=tu_database_id
# Opcional: chat fijo para recordatorios
TELEGRAM_CHAT_ID=123456789
# Opcional: zona horaria para recordatorios
REMINDER_TIMEZONE=Europe/Madrid
```

## Instalacion

```bat
cd /d "C:\Users\carlo\Documents\FiruDomo"
.venv\Scripts\python.exe -m pip install -r requeriments.txt
```

## Ejecucion

```bat
cd /d "C:\Users\carlo\Documents\FiruDomo"
.venv\Scripts\python.exe main.py
```

## Comandos

- `/start`
- `/help`
- `/check`
- `/add <tarea>`
- `/list`
- `/done <numero o texto>`
- `/pordefinir`
- `/todo`
- `/curso`
- `/bloqueadas`
- `/completadas`

## Recordatorios diarios

Se programan automaticamente a las:

- 07:00
- 12:30
- 18:00

Incluyen tareas de `To Do`, `En curso` y `Bloqueada`.

El bot guarda chats que usan comandos en `data/reminder_chats.json` y envia ahi los recordatorios.

