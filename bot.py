# bot.py
import discord
from discord.ext import commands
import asyncio
import os
import sys
from config import DISCORD_BOT_TOKEN, ADMIN_USER_IDS, DISCORD_CHANNEL_ID, TARGET_GUILD_ID

intents = discord.Intents.default()
intents.message_content = True
intents.members = True # Włącz to w Discord Developer Portal!

bot = commands.Bot(command_prefix="!", intents=intents)

bot_status = "stopped"
countdown_time = 0

# Funkcja do wysyłania wiadomości na kanał Discorda
async def send_status_message(status_type):
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    if channel:
        if status_type == "start":
            await channel.send("🚀 Bot Discord został pomyślnie uruchomiony!")
        elif status_type == "stop":
            await channel.send("🛑 Bot Discord został zatrzymany.")
        elif status_type == "restart":
            await channel.send("🔄 Bot Discord restartuje...")
    else:
        print(f"Nie znaleziono kanału o ID: {DISCORD_CHANNEL_ID}. Nie można wysłać wiadomości statusowej.")

@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user.name} (ID: {bot.user.id})")
    print(f"Jestem na {len(bot.guilds)} serwerach.")
    global bot_status
    if bot_status == "starting":
        await send_status_message("start")
        bot_status = "running"
    elif bot_status == "restarting":
        await send_status_message("start")
        bot_status = "running"
    else:
        await send_status_message("start")
        bot_status = "running"

# Sprawdzenie, czy komenda jest wykonywana przez admina bota
def is_bot_admin():
    async def predicate(ctx):
        if ctx.author.id in ADMIN_USER_IDS:
            return True
        else:
            await ctx.send("Brak uprawnień. Tylko administratorzy bota mogą używać tej komendy.")
            return False
    return commands.check(predicate)

# Sprawdzenie, czy komenda jest wykonywana na docelowym serwerze (opcjonalne)
def is_target_guild():
    async def predicate(ctx):
        if TARGET_GUILD_ID is None or ctx.guild.id == TARGET_GUILD_ID:
            return True
        else:
            await ctx.send("Ta komenda może być używana tylko na docelowym serwerze.")
            return False
    return commands.check(predicate)


@bot.command()
@is_bot_admin() # Tylko admin bota może użyć tej komendy
@is_target_guild() # Tylko na docelowym serwerze (jeśli TARGET_GUILD_ID jest ustawione)
async def hello(ctx):
    await ctx.send(f"Cześć, {ctx.author.display_name}!")

@bot.command()
@is_bot_admin() # Tylko admin bota może użyć tej komendy
@is_target_guild() # Tylko na docelowym serwerze (jeśli TARGET_GUILD_ID jest ustawione)
async def status(ctx):
    await ctx.send(f"Status bota: {bot_status.capitalize()}")

# Funkcje do sterowania botem z zewnątrz (wywoływane przez webpanel)
async def start_bot_process():
    global bot_status, countdown_time
    if bot_status == "running":
        return "Bot już działa."

    bot_status = "starting"
    countdown_time = 5
    for i in range(countdown_time, 0, -1):
        print(f"Uruchamianie bota za {i} sekund...")
        await asyncio.sleep(1)

    print("Uruchamiam bota...")
    try:
        # Pamiętaj, aby token był prawidłowy i intents były włączone w Discord Developer Portal
        await bot.start(DISCORD_BOT_TOKEN)
        return "Bot uruchomiony pomyślnie."
    except discord.LoginFailure:
        print("BŁĄD: Nieprawidłowy token bota. Sprawdź plik .env!")
        bot_status = "stopped"
        return "Nieprawidłowy token bota. Sprawdź config.py i .env"
    except discord.Forbidden:
        print("BŁĄD: Bot nie ma odpowiednich uprawnień (intents) lub został zbanowany z serwera.")
        bot_status = "stopped"
        return "Bot nie ma odpowiednich uprawnień (intents) lub został zbanowany z serwera."
    except Exception as e:
        print(f"BŁĄD: Wystąpił błąd podczas uruchamiania bota: {e}")
        bot_status = "stopped"
        return f"Wystąpił błąd podczas uruchamiania bota: {e}"

async def stop_bot_process():
    global bot_status, countdown_time
    if bot_status == "stopped":
        return "Bot już jest zatrzymany."

    bot_status = "stopping"
    countdown_time = 5
    for i in range(countdown_time, 0, -1):
        print(f"Zatrzymywanie bota za {i} sekund...")
        await asyncio.sleep(1)

    print("Zatrzymuję bota...")
    await send_status_message("stop")
    await bot.close()
    bot_status = "stopped"
    return "Bot zatrzymany pomyślnie."

async def restart_bot_process():
    global bot_status, countdown_time
    if bot_status in ["starting", "stopping", "restarting"]:
        return "Bot jest w trakcie operacji, poczekaj."

    bot_status = "restarting"
    countdown_time = 5
    for i in range(countdown_time, 0, -1):
        print(f"Restart bota za {i} sekund...")
        await asyncio.sleep(1)

    print("Restartuję bota...")
    await send_status_message("restart")
    await bot.close() # Zamknij istniejące połączenie
    try:
        await bot.start(DISCORD_BOT_TOKEN) # Uruchom ponownie
        return "Bot zrestartowany pomyślnie."
    except discord.LoginFailure:
        print("BŁĄD: Nieprawidłowy token bota podczas restartu. Sprawdź plik .env!")
        bot_status = "stopped"
        return "Nieprawidłowy token bota. Sprawdź config.py i .env"
    except discord.Forbidden:
        print("BŁĄD: Bot nie ma odpowiednich uprawnień (intents) lub został zbanowany z serwera podczas restartu.")
        bot_status = "stopped"
        return "Bot nie ma odpowiednich uprawnień (intents) lub został zbanowany z serwera."
    except Exception as e:
        print(f"BŁĄD: Wystąpił błąd podczas restartowania bota: {e}")
        bot_status = "stopped"
        return f"Wystąpił błąd podczas restartowania bota: {e}"

if __name__ == '__main__':
    # Ten blok nie będzie uruchamiany, bo bot jest uruchamiany przez webpanel jako subprocess
    pass
