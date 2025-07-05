# config.py
import os
from dotenv import load_dotenv

load_dotenv() # Ładuje zmienne środowiskowe z pliku .env

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# ID użytkowników, którzy będą mieli uprawnienia administratora bota
# W .env to powinno wyglądać np.: ADMIN_USER_IDS=123456789012345678,987654321098765432
ADMIN_USER_IDS = [int(x) for x in os.getenv("ADMIN_USER_IDS").split(',') if x.strip()]

# ID kanału Discord, na który bot ma wysyłać komunikaty o statusie
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

# Opcjonalne: ID serwera (guild ID) jeśli chcesz ograniczyć działanie bota do jednego serwera
# W .env to powinno wyglądać np.: TARGET_GUILD_ID=123456789012345678
TARGET_GUILD_ID = int(os.getenv("TARGET_GUILD_ID")) if os.getenv("TARGET_GUILD_ID") else None

# Konfiguracja IP i portu dla webpanelu (0.0.0.0 oznacza nasłuchiwanie na wszystkich interfejsach)
PANEL_IP = os.getenv("PANEL_IP", "0.0.0.0")
PANEL_PORT = int(os.getenv("PANEL_PORT", 5000))
