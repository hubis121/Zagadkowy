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


# --- Funkcja pomocnicza do formatowania liczby (zaokrąglanie do k, m) ---
def format_number_k_m(num):
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}m"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}k"
    else:
        return str(num)

# Wczytaj zmienne środowiskowe z pliku .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# --- KONFIGURACJA DLA ZMIANY NAZWY KANAŁU (POBRANE Z .env) ---
try:
    GUILD_ID = int(os.getenv('GUILD_ID'))
    TARGET_VOICE_CHANNEL_ID = int(os.getenv('TARGET_VOICE_CHANNEL_ID'))
except (ValueError, TypeError) as e:
    print(f"Błąd konwersji ID z .env na liczbę całkowitą: {e}")
    print("Upewnij się, że GUILD_ID i TARGET_VOICE_CHANNEL_ID w pliku .env są poprawnymi liczbami.")
    sys.exit(1) # Zakończ program, jeśli ID są niepoprawne

# Dodatkowe sprawdzenia, czy ID i token zostały wczytane poprawnie
if not TOKEN:
    print("Błąd: Zmienna środowiskowa DISCORD_TOKEN nie jest ustawiona w .env")
    sys.exit(1)
if not GUILD_ID:
    print("Błąd: Zmienna środowiskowa GUILD_ID nie jest ustawiona w .env")
    sys.exit(1)
if not TARGET_VOICE_CHANNEL_ID:
    print("Błąd: Zmienna środowiskowa TARGET_VOICE_CHANNEL_ID nie jest ustawiona w .env")
    sys.exit(1)
# --- KONIEC KONFIGURACJI ---


# Określ intencje bota
intents = discord.Intents.default()
intents.message_content = True # Pozostawiamy, bo są komendy tekstowe
intents.members = True       # KLUCZOWE: Do zliczania wszystkich członków (nie botów)

# Inicjalizuj klienta Discorda z określonymi intencjami
bot = discord.Client(intents=intents)

@bot.event
async def on_ready():
    global admin_notification_channel
    print(f'{bot.user} zalogował się!')
    print(f'Bot jest gotowy i działa na {len(bot.guilds)} serwerach.')

    if not admin_notification_channel:
        # Szukamy kanału administracyjnego na docelowym serwerze (GUILD_ID)
        target_guild = bot.get_guild(GUILD_ID)
        if target_guild:
            preferred_channel_names = ["bot-log", "logs", "admin", "general"]
            found_channel = None

            for name in preferred_channel_names:
                channel = discord.utils.get(target_guild.text_channels, name=name)
                if channel and channel.permissions_for(target_guild.me).send_messages:
                    found_channel = channel
                    break
            
            if not found_channel: # Jeśli nie znaleziono preferowanego, bierzemy pierwszy tekstowy
                for channel in target_guild.text_channels:
                    if channel.permissions_for(target_guild.me).send_messages:
                        found_channel = channel
                        break
            
            if found_channel:
                admin_notification_channel = found_channel
                print(f"Ustawiono domyślny kanał administracyjny na: {admin_notification_channel.name} ({target_guild.name})")
            else:
                print(f"Ostrzeżenie: Nie znaleziono kanału tekstowego, na który bot może wysyłać wiadomości powiadomień na serwerze o ID {GUILD_ID}.")
        else:
            print(f"Ostrzeżenie: Bot nie jest na serwerze o ID {GUILD_ID}. Nie można ustawić kanału administracyjnego.")


    print("Wykonuję początkowe sprawdzenie aktualizacji przy starcie bota...")
    print("Początkowe sprawdzenie aktualizacji zakończone (lub pominięte). Uruchamiam cykliczne sprawdzanie.")

    check_for_updates_loop.start()
    check_flags_loop.start()
    update_voice_channel_name.start() # Rozpocznij pętlę aktualizującą nazwę kanału

# --- Pętla do aktualizacji nazwy kanału głosowego ---
@tasks.loop(minutes=5) # Możesz zmienić częstotliwość (np. seconds=30, minutes=1)
async def update_voice_channel_name():
    print("Próbuję zaktualizować nazwę kanału głosowego...")
    try:
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            print(f"Błąd: Nie znaleziono serwera o ID {GUILD_ID}. Sprawdź, czy bot jest na tym serwerze.")
            if admin_notification_channel:
                try:
                    await admin_notification_channel.send(f"**Błąd konfiguracji!** Bot nie może znaleźć serwera o ID `{GUILD_ID}`. Upewnij się, że bot jest na tym serwerze i ID jest poprawne w pliku `.env`.")
                except Exception as e:
                    print(f"Nieoczekiwany błąd podczas wysyłania wiadomości o błędzie braku serwera: {e}")
            return

        voice_channel = guild.get_channel(TARGET_VOICE_CHANNEL_ID)
        if not voice_channel:
            print(f"Błąd: Nie znaleziono kanału głosowego o ID {TARGET_VOICE_CHANNEL_ID} na serwerze {guild.name}.")
            if admin_notification_channel:
                try:
                    await admin_notification_channel.send(f"**Błąd konfiguracji!** Bot nie może znaleźć kanału głosowego o ID `{TARGET_VOICE_CHANNEL_ID}` na serwerze `{guild.name}`. Upewnij się, że ID jest poprawne w pliku `.env`.")
                except Exception as e:
                    print(f"Nieoczekiwany błąd podczas wysyłania wiadomości o błędzie braku kanału: {e}")
            return
        
        if not isinstance(voice_channel, discord.VoiceChannel):
            print(f"Błąd: Kanał o ID {TARGET_VOICE_CHANNEL_ID} nie jest kanałem głosowym.")
            if admin_notification_channel:
                try:
                    await admin_notification_channel.send(f"**Błąd konfiguracji!** Kanał o ID `{TARGET_VOICE_CHANNEL_ID}` na serwerze `{guild.name}` nie jest kanałem głosowym. Bot może zmieniać tylko nazwy kanałów głosowych.")
                except Exception as e:
                    print(f"Nieoczekiwany błąd podczas wysyłania wiadomości o błędzie typu kanału: {e}")
            return

        # Sprawdź uprawnienia bota do zarządzania kanałem
        if not voice_channel.permissions_for(guild.me).manage_channels:
            print(f"Błąd: Bot nie ma uprawnień 'Zarządzanie kanałami' na kanale głosowym '{voice_channel.name}'.")
            if admin_notification_channel:
                try:
                    await admin_notification_channel.send(
                        f"**Błąd uprawnień!** Bot nie ma uprawnień 'Zarządzanie kanałami' na kanale głosowym "
                        f"`{voice_channel.name}` (ID: `{voice_channel.id}`). Nie mogę aktualizować jego nazwy. "
                        "Upewnij się, że bot ma tę rolę i uprawnienie w ustawieniach kanału."
                    )
                except discord.errors.Forbidden:
                    print("Błąd: Bot nie może wysłać wiadomości na kanale administracyjnym o błędzie uprawnień (brak uprawnień do wysyłania na tym kanale).")
                except Exception as e:
                    print(f"Nieoczekiwany błąd podczas wysyłania wiadomości o błędzie uprawnień: {e}")
            return

        # --- Logika zliczania wszystkich członków (nie botów) ---
        total_members_not_bots = 0
        await guild.chunk() 
        
        for member in guild.members:
            if not member.bot: # Liczymy tylko użytkowników, którzy nie są botami
                total_members_not_bots += 1
        
        # --- Użycie nowej funkcji do formatowania liczby ---
        formatted_member_count = format_number_k_m(total_members_not_bots)
        new_channel_name = f"Widzowie: {formatted_member_count}" 
        # --- Koniec zmiany logiki zliczania ---
        
        if voice_channel.name != new_channel_name:
            await voice_channel.edit(name=new_channel_name)
            print(f"Zmieniono nazwę kanału '{voice_channel.name}' na '{new_channel_name}'.")
        else:
            print(f"Nazwa kanału '{new_channel_name}' jest już aktualna.")

    except discord.Forbidden:
        print(f"Błąd uprawnień Discorda (Forbidden) podczas próby zmiany nazwy kanału. Sprawdź uprawnienia bota.")
        if admin_notification_channel:
            try:
                await admin_notification_channel.send(
                    "**Krytyczny Błąd Uprawnień!** Bot nie może zmienić nazwy kanału głosowego. "
                    "Upewnij się, że ma uprawnienie 'Zarządzanie kanałami' w ustawieniach kanału i serwera."
                )
            except discord.errors.Forbidden:
                print("Błąd: Bot nie może wysłać wiadomości na kanale administracyjnym o krytycznym błędzie uprawnień (brak uprawnień do wysyłania na tym kanale).")
            except Exception as e:
                print(f"Nieoczekiwany błąd podczas wysyłania wiadomości o krytycznym błędzie uprawnień: {e}")
    except discord.HTTPException as e:
        print(f"Błąd HTTP Discorda podczas zmiany nazwy kanału: {e} (Status: {e.status})")
        if e.status == 429:
            print("Zbyt wiele żądań (Rate Limit) - spowolnij odświeżanie nazwy kanału. Spróbuję ponownie za chwilę.")
        # Możesz dodać logikę do spowolnienia, jeśli często dostajesz 429
    except Exception as e:
        print(f"Nieoczekiwany błąd podczas aktualizacji nazwy kanału: {e}")


@tasks.loop(minutes=30) 
async def check_for_updates_loop():
    # Dodano sprawdzenie, czy bot jest gotowy przed próbą aktualizacji, aby uniknąć błędów
    if bot.is_ready():
        await perform_update_and_restart(admin_notification_channel)
        print("Cykliczne sprawdzanie aktualizacji zakończone. Czekam na następne.")
    else:
        print("Bot nie jest gotowy, pomijam cykliczne sprawdzanie aktualizacji.")

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

    # Jeśli użytkownik jest administratorem, ustawiamy jego kanał jako kanał administracyjny dla powiadomień
    if message.author.guild_permissions.administrator:
        # Sprawdzamy, czy kanał administracyjny jest już ustawiony
        # lub czy aktualny kanał wiadomości jest kanałem tekstowym i bot ma na nim uprawnienia do wysyłania
        if message.channel != admin_notification_channel and isinstance(message.channel, discord.TextChannel) and message.channel.permissions_for(message.guild.me).send_messages:
            admin_notification_channel = message.channel
            print(f"Kanał administracyjny zaktualizowany na: {message.channel.name} ({message.guild.name})")

    # Obsługa komend !restart i !stop
    if message.content.startswith('!'):
        if message.author.guild_permissions.administrator:
            if message.content == '!restart':
                print('Restartowanie bota - rozpoczęcie odliczania...')
                embed = discord.Embed(
                    title="Restartowanie Bota",
                   embed.description = f"Bot zostanie zrestartowany za **{i}** sekund..."
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

                await bot.close() # Bot zostanie zamknięty
        else:
            if message.content in ['!restart', '!stop']: 
                await message.channel.send(f'{message.author.mention}, nie masz uprawnień do użycia tej komendy.')
                print(f'Użytkownik {message.author} próbował użyć komendy admina bez uprawnień.')

bot.run(TOKEN)
