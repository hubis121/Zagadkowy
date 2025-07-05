import os
import discord
from dotenv import load_dotenv
import sys
import subprocess
import asyncio
from discord.ext import tasks

# --- Konfiguracja ścieżek i nazw sesji ---
BOT_DIR = os.path.expanduser('~/MojDiscordBot')
BOT_MAIN_SCRIPT = os.path.join(BOT_DIR, 'main.py')
SCREEN_SESSION_NAME = 'discord_bot'

# --- Pliki flag ---
STOP_FLAG_FILE = os.path.join(BOT_DIR, 'stop_flag.txt')
RESTART_FLAG_FILE = os.path.join(BOT_DIR, 'restart_flag.txt') # Nowa flaga dla restartu z panelu

# --- Globalna zmienna do przechowywania kanału administracyjnego ---
# Będziemy ją ustawiać dynamicznie, gdy bot otrzyma wiadomość od administratora
# Możesz też ustawić ID konkretnego kanału tutaj, jeśli wolisz:
# ADMIN_CHANNEL_ID = 123456789012345678 # Zastąp swoim ID kanału, jeśli chcesz
admin_notification_channel = None


# --- Funkcja pomocnicza do wykonywania komend systemowych ---
def run_shell_command(command, cwd=None):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd if cwd else BOT_DIR
        )
        return True, result.stdout.strip(), result.stderr.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stdout.strip(), e.stderr.strip()
    except Exception as e:
        return False, "", str(e)

# --- Funkcja do sprawdzania aktualizacji i restartu ---
async def perform_update_and_restart(channel=None):
    print("Sprawdzam aktualizacje kodu z GitHuba...")
    current_dir = os.getcwd()

    # Pobierz najnowsze zmiany z GitHuba
    success, stdout, stderr = run_shell_command('git pull origin master', cwd=current_dir)

    if success:
        if "Already up to date." not in stdout and "fast-forward" in stdout:
            print("Pomyślnie pobrano najnowsze zmiany z GitHuba. Restartuję bota...")
            if channel:
                await channel.send("Wykryto i pobrano nowe zmiany z GitHuba. Restartuję bota, aby zastosować aktualizacje!")

            # Zainstaluj/zaktualizuj biblioteki po pobraniu zmian
            if os.path.exists(os.path.join(current_dir, 'requirements.txt')):
                print("Instaluję/aktualizuję biblioteki z requirements.txt...")
                lib_success, lib_stdout, lib_stderr = run_shell_command('pip install -r requirements.txt', cwd=current_dir)
                if lib_success:
                    print("Biblioteki zainstalowane/zaktualizowane pomyślnie.")
                else:
                    print(f"Nie udało się zainstalować/zaktualizować bibliotek:\n{lib_stderr}")
                    if channel:
                        await channel.send(f"Błąd podczas instalacji bibliotek: ```{lib_stderr}```")

            # Usuń flagę restartu, jeśli istnieje, przed restartem
            if os.path.exists(RESTART_FLAG_FILE):
                os.remove(RESTART_FLAG_FILE)
                print(f"Usunięto flagę restartu: {RESTART_FLAG_FILE}")

            os.execv(sys.executable, ['python'] + sys.argv)
        else:
            print("Lokalne repozytorium jest aktualne. Nie ma nowych zmian do pobrania.")
            if "Already up to date." not in stdout and stdout:
                 print(f"  [Auto-Update Log] Git Output: {stdout}")
    else:
        print(f"Nie udało się pobrać zmian z GitHuba. Błąd:\nSTDOUT: {stdout}\nSTDERR: {stderr}")
        if channel:
            if "Your local changes would be overwritten" in stderr:
                 await channel.send(f"Błąd aktualizacji GitHuba: ```{stderr}```\nProszę zatwierdzić/schować lokalne zmiany.")
            elif "Authentication failed" in stderr:
                 await channel.send(f"Błąd autoryzacji GitHuba: ```{stderr}```\nSprawdź swój Personal Access Token.")
            else:
                 await channel.send(f"Nieznany błąd podczas aktualizacji z GitHuba: ```{stderr}```")

# --- Koniec funkcji sprawdzania aktualizacji ---


# Wczytaj zmienne środowiskowe z pliku .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Określ intencje bota
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Inicjalizuj klienta Discorda z określonymi intencjami
bot = discord.Client(intents=intents)

@bot.event
async def on_ready():
    global admin_notification_channel
    print(f'{bot.user} zalogował się!')
    print(f'Bot jest gotowy i działa na {len(bot.guilds)} serwerach.')

    # Przy starcie, spróbuj ustawić kanał administracyjny na pierwszy kanał tekstowy,
    # do którego bot ma dostęp na pierwszym serwerze.
    # TO JEST TYLKO WSTĘPNE USTAWIENIE. Lepsze jest ustawienie przez ADMIN_CHANNEL_ID.
    if not admin_notification_channel: # Jeśli nie ustawiono przez ID, spróbuj znaleźć
        for guild in bot.guilds:
            for channel in guild.text_channels:
                # Sprawdź, czy bot ma uprawnienia do wysyłania wiadomości
                if channel.permissions_for(guild.me).send_messages:
                    admin_notification_channel = channel
                    print(f"Ustawiono domyślny kanał administracyjny na: {channel.name} ({guild.name})")
                    break
            if admin_notification_channel:
                break

    # Wykonaj początkowe sprawdzenie aktualizacji od razu po starcie bota
    print("Wykonuję początkowe sprawdzenie aktualizacji przy starcie bota...")
    await perform_update_and_restart(admin_notification_channel) 
    print("Początkowe sprawdzenie aktualizacji zakończone. Uruchamiam cykliczne sprawdzanie.")

    # Uruchom cykliczne sprawdzanie aktualizacji co 30 minut
    check_for_updates_loop.start()
    # Uruchom cykliczne sprawdzanie flag co 5 sekund
    check_flags_loop.start() # Rozpoczynanie pętli do sprawdzania flag


@tasks.loop(minutes=30) 
async def check_for_updates_loop():
    # Użyj kanału ustawionego globalnie
    await perform_update_and_restart(admin_notification_channel)
    print("Cykliczne sprawdzanie aktualizacji zakończone. Czekam na następne.")

@tasks.loop(seconds=5) # Sprawdzaj co 5 sekund
async def check_flags_loop():
    global admin_notification_channel

    # Sprawdzanie flagi STOP
    if os.path.exists(STOP_FLAG_FILE):
        print(f"Wykryto flagę zatrzymania: {STOP_FLAG_FILE}")
        if admin_notification_channel:
            embed = discord.Embed(
                title="Zatrzymywanie Bota",
                description="Bot zostanie zatrzymany przez panel webowy!", 
                color=discord.Color.red()
            )
            await admin_notification_channel.send(embed=embed)

        # Usuń flagę przed zamknięciem
        os.remove(STOP_FLAG_FILE)
        print("Usunięto flagę zatrzymania.")

        await bot.close()
        print("Bot został zatrzymany przez panel webowy.")
        # sys.exit() # Nie potrzeba sys.exit(), await bot.close() wystarczy.

    # Sprawdzanie flagi RESTART
    if os.path.exists(RESTART_FLAG_FILE):
        print(f"Wykryto flagę restartu: {RESTART_FLAG_FILE}")
        if admin_notification_channel:
            embed = discord.Embed(
                title="Restartowanie Bota",
                description="Bot zostanie zrestartowany przez panel webowy!", 
                color=discord.Color.orange()
            )
            await admin_notification_channel.send(embed=embed)

        # Usuń flagę przed restartem
        os.remove(RESTART_FLAG_FILE)
        print("Usunięto flagę restartu.")

        os.execv(sys.executable, ['python'] + sys.argv) # Restart bota

@bot.event
async def on_message(message):
    global admin_notification_channel
    # Ignoruj wiadomości wysłane przez samego bota
    if message.author == bot.user:
        return

    # Ustaw kanał administracyjny na kanał, z którego przyszła komenda admina
    # Jest to lepsze niż globalne szukanie.
    if message.author.guild_permissions.administrator:
        admin_notification_channel = message.channel

    # Komendy dla administratorów
    if message.content.startswith('!'):
        if message.author.guild_permissions.administrator:
            if message.content == '!restart':
                print('Restartowanie bota - rozpoczęcie odliczania...')
                embed = discord.Embed(
                    title="Restartowanie Bota",
                    description=f"Bot zostanie zrestartowany za **5** sekund...", 
                    color=discord.Color.orange()
                )
                countdown_message = await message.channel.send(embed=embed) 

                for i in range(4, 0, -1): 
                    embed.description = f"Bot zostanie zrestartowany za **{i}** sekund..."
                    await countdown_message.edit(embed=embed)
                    await asyncio.sleep(1)

                embed.description = "Restartuję bota teraz!"
                embed.color = discord.Color.green()
                await countdown_message.edit(embed=embed)
                await asyncio.sleep(1) 

                # Powiadomienie o zresetowaniu
                await message.channel.send("Bot został zresetowany!")

                os.execv(sys.executable, ['python'] + sys.argv)

            elif message.content == '!stop':
                print('Zatrzymywanie bota - rozpoczęcie odliczania...')
                embed = discord.Embed(
                    title="Zatrzymywanie Bota",
                    description=f"Bot zostanie zatrzymany za **5** sekund...", 
                    color=discord.Color.red()
                )
                countdown_message = await message.channel.send(embed=embed) 

                for i in range(4, 0, -1): 
                    embed.description = f"Bot zostanie zatrzymany za **{i}** sekund..."
                    await countdown_message.edit(embed=embed)
                    await asyncio.sleep(1)

                embed.description = "Zatrzymuję bota teraz!"
                embed.color = discord.Color.dark_red()
                await countdown_message.edit(embed=embed)

                await bot.close()
        else:
            # Jeśli użytkownik nie jest administratorem i próbuje użyć komendy admina
            if message.content in ['!restart', '!stop']: 
                await message.channel.send(f'{message.author.mention}, nie masz uprawnień do użycia tej komendy.')
                print(f'Użytkownik {message.author} próbował użyć komendy admina bez uprawnień.')

# Uruchom bota
bot.run(TOKEN)
