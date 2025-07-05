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
RESTART_FLAG_FILE = os.path.join(BOT_DIR, 'restart_flag.txt')

# --- Globalna zmienna do przechowywania kanału administracyjnego ---
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
    # UWAGA: Upewnij się, że 'master' to poprawna nazwa gałęzi.
    # Jeśli na GitHubie masz 'main', zmień 'master' na 'main' tutaj.
    success, stdout, stderr = run_shell_command('git pull origin master', cwd=current_dir) 

    if success:
        if "Already up to date." not in stdout and "fast-forward" in stdout:
            print("Pomyślnie pobrano najnowsze zmiany z GitHuba. Restartuję bota...")
            if channel:
                try:
                    await channel.send("Wykryto i pobrano nowe zmiany z GitHuba. Restartuję bota, aby zastosować aktualizacje!")
                except discord.errors.Forbidden:
                    print("Błąd: Bot nie ma uprawnień do wysyłania wiadomości na kanale podczas aktualizacji.")
                except Exception as e:
                    print(f"Nieoczekiwany błąd podczas wysyłania wiadomości o aktualizacji: {e}")

            # Zainstaluj/zaktualizuj biblioteki po pobraniu zmian
            if os.path.exists(os.path.join(current_dir, 'requirements.txt')):
                print("Instaluję/aktualizuję biblioteki z requirements.txt...")
                lib_success, lib_stdout, lib_stderr = run_shell_command('pip install -r requirements.txt', cwd=current_dir)
                if lib_success:
                    print("Biblioteki zainstalowane/zaktualizowane pomyślnie.")
                else:
                    print(f"Nie udało się zainstalować/zaktualizować bibliotek:\n{lib_stderr}")
                    if channel:
                        try:
                            await channel.send(f"Błąd podczas instalacji bibliotek: ```{lib_stderr}```")
                        except discord.errors.Forbidden:
                            pass # Already logged above
                        except Exception as e:
                            print(f"Nieoczekiwany błąd podczas wysyłania wiadomości o błędzie instalacji bibliotek: {e}")

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
            try:
                if "Your local changes would be overwritten" in stderr:
                    await channel.send(f"Błąd aktualizacji GitHuba: ```{stderr}```\nProszę zatwierdzić/schować lokalne zmiany.")
                elif "Authentication failed" in stderr:
                    await channel.send(f"Błąd autoryzacji GitHuba: ```{stderr}```\nSprawdź swój Personal Access Token.")
                else:
                    await channel.send(f"Nieznany błąd podczas aktualizacji z GitHuba: ```{stderr}```")
            except discord.errors.Forbidden:
                print("Błąd: Bot nie ma uprawnień do wysyłania wiadomości na kanale o błędzie aktualizacji.")
            except Exception as e:
                print(f"Nieoczekiwany błąd podczas wysyłania wiadomości o błędzie Git: {e}")

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

    if not admin_notification_channel:
        for guild in bot.guilds:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    admin_notification_channel = channel
                    print(f"Ustawiono domyślny kanał administracyjny na: {channel.name} ({guild.name})")
                    break
            if admin_notification_channel:
                break
        if not admin_notification_channel:
            print("Ostrzeżenie: Nie znaleziono kanału tekstowego, na który bot może wysyłać wiadomości powiadomień.")

    print("Wykonuję początkowe sprawdzenie aktualizacji przy starcie bota...")
    await perform_update_and_restart(admin_notification_channel) 
    print("Początkowe sprawdzenie aktualizacji zakończone. Uruchamiam cykliczne sprawdzanie.")

    check_for_updates_loop.start()
    check_flags_loop.start()


@tasks.loop(minutes=30) 
async def check_for_updates_loop():
    await perform_update_and_restart(admin_notification_channel)
    print("Cykliczne sprawdzanie aktualizacji zakończone. Czekam na następne.")

@tasks.loop(seconds=5) 
async def check_flags_loop():
    global admin_notification_channel

    if os.path.exists(STOP_FLAG_FILE):
        print(f"Wykryto flagę zatrzymania: {STOP_FLAG_FILE}")
        if admin_notification_channel:
            embed = discord.Embed(
                title="Zatrzymywanie Bota",
                description="Bot zostanie zatrzymany przez panel webowy!", 
                color=discord.Color.red()
            )
            try: 
                await admin_notification_channel.send(embed=embed) 
            except discord.errors.Forbidden:
                print("Błąd: Bot nie ma uprawnień do wysyłania wiadomości na kanale admin_notification_channel.")
            except Exception as e:
                print(f"Nieoczekiwany błąd podczas wysyłania wiadomości o zatrzymaniu: {e}")
        else:
            print("Brak ustawionego kanału admin_notification_channel do wysłania wiadomości o zatrzymaniu. Wiadomość Discord nie zostanie wysłana.")

        if os.path.exists(STOP_FLAG_FILE): 
            try:
                os.remove(STOP_FLAG_FILE)
                print(f"Usunięto flagę zatrzymania: {STOP_FLAG_FILE}")
            except Exception as e:
                print(f"Błąd podczas usuwania stop_flag.txt: {e}")

        await bot.close()
        print("Bot został zatrzymany przez panel webowy.")

    if os.path.exists(RESTART_FLAG_FILE):
        print(f"Wykryto flagę restartu: {RESTART_FLAG_FILE}")
        if admin_notification_channel:
            embed = discord.Embed(
                title="Restartowanie Bota",
                description="Bot zostanie zrestartowany przez panel webowy!", 
                color=discord.Color.orange()
            )
            try:
                await admin_notification_channel.send(embed=embed)
            except discord.errors.Forbidden:
                print("Błąd: Bot nie ma uprawnień do wysyłania wiadomości na kanale admin_notification_channel.")
            except Exception as e:
                print(f"Nieoczekiwany błąd podczas wysyłania wiadomości o restarcie: {e}")
        else:
            print("Brak ustawionego kanału admin_notification_channel do wysłania wiadomości o restarcie. Wiadomość Discord nie zostanie wysłana.")

        if os.path.exists(RESTART_FLAG_FILE): 
            try:
                os.remove(RESTART_FLAG_FILE)
                print(f"Usunięto flagę restartu: {RESTART_FLAG_FILE}")
            except Exception as e:
                print(f"Błąd podczas usuwania restart_flag.txt: {e}")

        os.execv(sys.executable, ['python'] + sys.argv) 

@bot.event
async def on_message(message):
    global admin_notification_channel
    if message.author == bot.user:
        return

    if message.author.guild_permissions.administrator:
        if admin_notification_channel != message.channel: 
            admin_notification_channel = message.channel
            print(f"Kanał administracyjny zaktualizowany na: {message.channel.name} ({message.guild.name})")

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
            if message.content in ['!restart', '!!stop']: 
                await message.channel.send(f'{message.author.mention}, nie masz uprawnień do użycia tej komendy.')
                print(f'Użytkownik {message.author} próbował użyć komendy admina bez uprawnień.')

bot.run(TOKEN)
