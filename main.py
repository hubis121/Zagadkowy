import os
import discord
from dotenv import load_dotenv
import sys
import subprocess
import asyncio # Dodane do obsługi asynchronicznego odliczania

# --- Automatyczna aktualizacja kodu z GitHuba i instalacja bibliotek (przy starcie bota) ---
print("Sprawdzam aktualizacje kodu z GitHuba...")

# Funkcja pomocnicza do wykonywania komend systemowych
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
        print(f"  [Auto-Update Log] Komenda '{command}' - Sukces.")
        if result.stdout:
            pass # print(f"  [Auto-Update Log] STDOUT: {result.stdout.strip()}") # Opcjonalnie: odkomentuj, żeby widzieć logi
        if result.stderr:
            print(f"  [Auto-Update Log] STDERR: {result.stderr.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  [Auto-Update Log] Błąd podczas wykonywania komendy '{command}':")
        print(f"  [Auto-Update Log] STDOUT: {e.stdout.strip()}")
        print(f"  [Auto-Update Log] STDERR: {e.stderr.strip()}")
        return False
    except Exception as e:
        print(f"  [Auto-Update Log] Nieoczekiwany błąd: {e}")
        return False

# Pobierz najnowsze zmiany z GitHuba
current_dir = os.getcwd()

# Wykonaj git pull
if run_command_silent('git pull origin master', cwd=current_dir):
    print("Pomyślnie pobrano najnowsze zmiany z GitHuba.")
else:
    print("Nie udało się pobrać zmian z GitHuba (może być brak połączenia, brak zmian lub błędy autoryzacji). Kontynuuję z istniejącym kodem.")

# Zainstaluj/zaktualizuj biblioteki
if os.path.exists(os.path.join(current_dir, 'requirements.txt')):
    print("Instaluję/aktualizuję biblioteki z requirements.txt...")
    if run_command_silent('pip install -r requirements.txt', cwd=current_dir):
        print("Biblioteki zainstalowane/zaktualizowane pomyślnie.")
    else:
        print("Nie udało się zainstalować/zaktualizować bibliotek.")
else:
    print("Brak pliku requirements.txt. Pomijam instalację bibliotek.")

print("Sprawdzanie aktualizacji zakończone. Uruchamiam bota...")
# --- Koniec automatycznej aktualizacji ---


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
    print(f'{bot.user} zalogował się!')
    print(f'Bot jest gotowy i działa na {len(bot.guilds)} serwerach.')

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
                    description="Rozpoczynam restart bota...",
                    color=discord.Color.orange()
                )
                countdown_message = await message.channel.send(embed=embed)

                for i in range(5, 0, -1):
                    embed.description = f"Bot zostanie zrestartowany za **{i}** sekund..."
                    await countdown_message.edit(embed=embed)
                    await asyncio.sleep(1)

                embed.description = "Restartuję bota teraz!"
                embed.color = discord.Color.green()
                await countdown_message.edit(embed=embed)
                await asyncio.sleep(1) # Krótka pauza, aby użytkownik zobaczył finalny komunikat

                os.execv(sys.executable, ['python'] + sys.argv)

            elif message.content == '!stop':
                print('Zatrzymywanie bota - rozpoczęcie odliczania...')
                embed = discord.Embed(
                    title="Zatrzymywanie Bota",
                    description="Rozpoczynam zatrzymywanie bota...",
                    color=discord.Color.red()
                )
                countdown_message = await message.channel.send(embed=embed)

                for i in range(5, 0, -1):
                    embed.description = f"Bot zostanie zatrzymany za **{i}** sekund..."
                    await countdown_message.edit(embed=embed)
                    await asyncio.sleep(1)

                embed.description = "Zatrzymuję bota teraz!"
                embed.color = discord.Color.dark_red()
                await countdown_message.edit(embed=embed)
                await asyncio.sleep(1) # Krótka pauza

                await bot.close()
        else:
            # Jeśli użytkownik nie jest administratorem i próbuje użyć komendy admina
            if message.content in ['!restart', '!stop']:
                await message.channel.send(f'{message.author.mention}, nie masz uprawnień do użycia tej komendy.')
                print(f'Użytkownik {message.author} próbował użyć komendy admina bez uprawnień.')

# Uruchom bota
bot.run(TOKEN)
