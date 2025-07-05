# config.py
import os
from dotenv import load_dotenv

load_dotenv() # Ładuje zmienne środowiskowe z pliku .env

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
# Zastąp swoimi ID adminów Discorda, oddzielając je przecinkami w .env
# Przykład w .env: ADMIN_USER_IDS=123456789012345678,987654321098765432
ADMIN_USER_IDS = [int(x) for x in os.getenv("ADMIN_USER_IDS").split(',')]
# Zastąp ID kanału tekstowego Discorda, na którym bot ma wysyłać komunikaty
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
PANEL_IP = os.getenv("PANEL_IP", "0.0.0.0") # Domyślnie nasłuchuje na wszystkich interfejsach
PANEL_PORT = int(os.getenv("PANEL_PORT", 5000)) # Domyślny port dla webpanelu
