"""
Script de prueba SIMPLE para verificar si el token funciona
"""
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

logger.info(f"Token cargado: {TELEGRAM_TOKEN[:20]}..." if TELEGRAM_TOKEN else "❌ NO HAY TOKEN")

if not TELEGRAM_TOKEN:
    print("❌ ERROR: No hay token en .env")
    exit(1)

try:
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    logger.info("✅ Token válido, app creada correctamente")
except Exception as e:
    logger.error(f"❌ ERROR: {e}")
    exit(1)

print("\n✅ El token FUNCIONA\n")

