import os
import discord
from dotenv import load_dotenv
import sys
import subprocess
import asyncio
from discord.ext import tasks # Dodane do cyklicznych zadań

# --- Funkcja pomocnicza do wykonywania komend systemowych ---
def run_command_silent(command, cwd=None):
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            shell=True
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
    success, stdout, stderr = run_command_silent('git pull origin master', cwd=current_dir)

    if success:
        if "Already up to date." not in stdout and "fast-forward" in stdout:
            print("Pomyślnie pobrano najnowsze zmiany z GitHuba. Restartuję bota...")
            if channel:
                await channel.send("Wykryto i pobrano nowe zmiany z GitHuba. Restartuję bota, aby zastosować aktualizacje!")

            # Zainstaluj/zaktualizuj biblioteki po pobraniu zmian
            if os.path.exists(os.path.join(current_dir, 'requirements.txt')):
                print("Instaluję/aktualizuję biblioteki z requirements.txt...")
                lib_success, lib_stdout, lib_stderr = run_command_silent('pip install -r requirements.txt', cwd=current_dir)
                if lib_success:
                    print("Biblioteki zainstalowane/zaktualizowane pomyślnie.")
                else:
                    print(f"Nie udało się zainstalować/zaktualizować bibliotek:\n{lib_stderr}")
                    if channel:
                        await channel.send(f"Błąd podczas instalacji bibliotek: ```{lib_stderr}```")

            os.execv(sys.executable, ['python'] + sys.argv)
        else:
            print("Lokalne repozytorium jest aktualne. Nie ma nowych zmian do pobrania.")
            if "Already up to date." not in stdout and stdout:
                 print(f"  [Auto-Update Log] Git Output: {stdout}") # Dodatkowe logowanie jeśli nie "up to date" ale nie fast-forward
    else:
        print(f"Nie udało się pobrać zmian z GitHuba. Błąd:\nSTDOUT: {stdout}\nSTDERR: {stderr}")
        if channel:
            # Opcjonalnie: wysyłaj tylko krytyczne błędy do kanału
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
# Opcjonalnie: ID kanału do wysyłania powiadomień o aktualizacjach (możesz usunąć, jeśli nie chcesz powiadomień)
# ADMIN_CHANNEL_ID = int(os.getenv('ADMIN_CHANNEL_ID')) 

# Określ intencje bota
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Inicjalizuj klienta Discorda z określonymi intencjami
bot = discord.Client(intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} zalogował się!')
    print(f'Bot jest gotowy i działa na {len(bot.guilds)} serwerach.')

    # Wykonaj początkowe sprawdzenie aktualizacji od razu po starcie bota
    print("Wykonuję początkowe sprawdzenie aktualizacji przy starcie bota...")
    await perform_update_and_restart() # Bez kanału, bo bot mógł jeszcze nie być w pełni gotowy do wysyłki wiadomości
    print("Początkowe sprawdzenie aktualizacji zakończone. Uruchamiam cykliczne sprawdzanie.")

    # Uruchom cykliczne sprawdzanie aktualizacji co 30 minut
    check_for_updates_loop.start()

@tasks.loop(minutes=30) # Sprawdzaj co 30 minut
async def check_for_updates_loop():
    # Możesz określić ID kanału, na który mają być wysyłane powiadomienia, np. administratora
    # admin_channel = bot.get_channel(ADMIN_CHANNEL_ID) 
    # await perform_update_and_restart(admin_channel) # Przekazuj kanał do powiadomień

    # Na razie bez wysyłania wiadomości na Discorda z tła, tylko logowanie
    await perform_update_and_restart()
    print("Cykliczne sprawdzanie aktualizacji zakończone. Czekam na następne.")


@bot.event
async def on_message(message):
    # Ignoruj wiadomości wysłane przez samego bota
    if message.author == bot.user:
        return

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
