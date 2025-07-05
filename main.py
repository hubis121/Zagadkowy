import os
import discord
from dotenv import load_dotenv

# Wczytaj zmienne środowiskowe z pliku .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Określ intencje bota
# Intents.default() to dobry start, ale jeśli chcesz używać np. członków serwera, potrzebujesz Intents.members = True
# i aktywować to w Discord Developer Portal -> Bot -> Privileged Gateway Intents
intents = discord.Intents.default()
intents.message_content = True # Wymagane do czytania zawartości wiadomości

# Inicjalizuj klienta Discorda z określonymi intencjami
bot = discord.Client(intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} zalogował się!')
    print(f'Bot jest gotowy i działa na {len(bot.guilds)} serwerach.')

@bot.event
async def on_message(message):
    # Ignoruj wiadomości wysłane przez samego bota
    if message.author == bot.user:
        return

    # Jeśli wiadomość to "!hello", odpowiedz "Hello, world!"
    if message.content == '!hello':
        await message.channel.send('Hello, world!')
        print(f'Odpowiedziano na !hello w kanale: {message.channel.name}')

# Uruchom bota
bot.run(TOKEN)
