# bot.py
import discord
from discord.ext import commands
import asyncio
import os
import sys
from config import DISCORD_BOT_TOKEN, ADMIN_USER_IDS, DISCORD_CHANNEL_ID

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

bot_status = "stopped"
countdown_time = 0

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
        print(f"Nie znaleziono kanału o ID: {DISCORD_CHANNEL_ID}")

@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user.name}")
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


@bot.command()
@commands.is_owner() # Tylko właściciel aplikacji Discord (ustawiony na dev portalu)
async def hello(ctx):
    await ctx.send("Cześć!")

@bot.command()
async def status(ctx):
    if ctx.author.id in ADMIN_USER_IDS:
        await ctx.send(f"Status bota: {bot_status.capitalize()}")
    else:
        await ctx.send("Brak uprawnień.")

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
        await bot.start(DISCORD_BOT_TOKEN)
        return "Bot uruchomiony pomyślnie."
    except discord.LoginFailure:
        return "Nieprawidłowy token bota. Sprawdź config.py i .env"
    except Exception as e:
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
    await bot.close()
    try:
        await bot.start(DISCORD_BOT_TOKEN)
        return "Bot zrestartowany pomyślnie."
    except discord.LoginFailure:
        return "Nieprawidłowy token bota. Sprawdź config.py i .env"
    except Exception as e:
        return f"Wystąpił błąd podczas restartowania bota: {e}"

if __name__ == '__main__':
    # Ten blok nie będzie uruchamiany, bo bot jest uruchamiany przez webpanel jako subprocess
    pass
