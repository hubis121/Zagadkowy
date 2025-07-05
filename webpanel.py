# webpanel.py
from flask import Flask, render_template_string, redirect, url_for, jsonify
import asyncio
import threading
import time
import subprocess
import sys
import os
from config import PANEL_IP, PANEL_PORT # Importujemy z config.py

app = Flask(__name__)

bot_process = None
bot_status = "stopped"
countdown_value = 0
countdown_active = False

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Panel Zarządzania Botem Discord</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background-color: #f4f4f4; color: #333; }
        .container { max-width: 600px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #0056b3; }
        .button-group { display: flex; justify-content: space-around; margin-top: 20px; }
        .button-group button {
            padding: 10px 20px;
            font-size: 16px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            color: white;
            transition: background-color 0.3s ease;
        }
        .button-group button.start { background-color: #28a745; }
        .button-group button.start:hover { background-color: #218838; }
        .button-group button.stop { background-color: #dc3545; }
        .button-group button.stop:hover { background-color: #c82333; }
        .button-group button.restart { background-color: #ffc107; color: #333; }
        .button-group button.restart:hover { background-color: #e0a800; }
        .status-info { margin-top: 20px; text-align: center; font-size: 1.2em; }
        #countdown { font-weight: bold; color: #007bff; }
        .message { margin-top: 20px; padding: 10px; border-radius: 5px; }
        .message.success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .message.error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .message.info { background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
    </style>
    <script>
        function updateStatus() {
            fetch('/status_json')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('botStatus').innerText = data.status.charAt(0).toUpperCase() + data.status.slice(1);
                    const countdownElement = document.getElementById('countdown');
                    if (data.countdown_active) {
                        countdownElement.innerText = data.countdown_value + ' sekund';
                        countdownElement.style.display = 'inline';
                    } else {
                        countdownElement.style.display = 'none';
                    }
                })
                .catch(error => console.error('Błąd pobierania statusu:', error));
        }

        setInterval(updateStatus, 1000);
        document.addEventListener('DOMContentLoaded', updateStatus);
    </script>
</head>
<body>
    <div class="container">
        <h1>Panel Zarządzania Botem Discord</h1>
        <div class="status-info">
            Status bota: <span id="botStatus">{{ bot_status.capitalize() }}</span>
            <span id="countdown" style="display: {{ 'inline' if countdown_active else 'none' }}">
                {{ countdown_value }} sekund
            </span>
        </div>
        <div class="button-group">
            <form action="/start" method="post">
                <button type="submit" class="start" {{ 'disabled' if bot_status == 'starting' or bot_status == 'running' }}>Start</button>
            </form>
            <form action="/stop" method="post">
                <button type="submit" class="stop" {{ 'disabled' if bot_status == 'stopping' or bot_status == 'stopped' }}>Stop</button>
            </form>
            <form action="/restart" method="post">
                <button type="submit" class="restart" {{ 'disabled' if bot_status == 'restarting' or bot_status == 'starting' or bot_status == 'stopping' }}>Restart</button>
            </form>
        </div>
        {% if message %}
            <div class="message {{ message_type }}">{{ message }}</div>
        {% endif %}
    </div>
</body>
</html>
"""

def run_bot_in_thread():
    global bot_process, bot_status, countdown_value, countdown_active
    try:
        # Użyj sys.executable aby zapewnić, że używamy właściwego interpretera Pythona z Termuxa
        # cwd=os.path.dirname(os.path.abspath(__file__)) zapewnia, że bot.py jest szukany w tym samym katalogu
        bot_process = subprocess.Popen([sys.executable, "bot.py"],
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       text=True,
                                       cwd=os.path.dirname(os.path.abspath(__file__)))
        bot_status = "starting"
        countdown_active = True
        countdown_value = 5

        for i in range(countdown_value, 0, -1):
            countdown_value = i
            time.sleep(1)
        countdown_active = False

        # Nie ustawiaj bot_status na running tutaj, to bot.py sam powinien to zrobić po połączeniu
        print("Bot Discord próbuje się uruchomić. Sprawdź logi bota w tmuxie.")
        bot_process.wait() # Czekaj na zakończenie procesu bota
        print("Bot Discord zakończył działanie (proces subprocess się zakończył).")
        bot_status = "stopped"
    except Exception as e:
        print(f"Błąd podczas uruchamiania bota (subprocess): {e}")
        bot_status = "stopped"
        countdown_active = False

def stop_bot_in_thread():
    global bot_process, bot_status, countdown_value, countdown_active
    if bot_process and bot_process.poll() is None: # Jeśli proces bota nadal działa
        try:
            bot_status = "stopping"
            countdown_active = True
            countdown_value = 5

            for i in range(countdown_value, 0, -1):
                countdown_value = i
                time.sleep(1)
            countdown_active = False

            bot_process.terminate() # Wysyła sygnał zakończenia
            bot_process.wait(timeout=5) # Daj czas na czyste zakończenie
            if bot_process.poll() is None: # Jeśli nadal działa po terminacji, zabij
                bot_process.kill()
            print("Bot Discord zatrzymany.")
            bot_status = "stopped"
        except Exception as e:
            print(f"Błąd podczas zatrzymywania bota: {e}")
            # Jeśli błąd podczas zatrzymywania, ustaw status na running, bo bot mógł nie zostać zatrzymany
            bot_status = "running" 
    else:
        bot_status = "stopped" # Jeśli proces już nie działał, ustaw status na zatrzymany
    bot_process = None

def restart_bot_in_thread():
    global bot_status, countdown_value, countdown_active
    if bot_status in ["starting", "stopping", "restarting"]:
        return "Bot jest w trakcie operacji, poczekaj."

    bot_status = "restarting"
    countdown_active = True
    countdown_value = 5
    for i in range(countdown_value, 0, -1):
        countdown_value = i
        time.sleep(1)
    countdown_active = False

    stop_bot_in_thread() # Zatrzymujemy bota
    time.sleep(2) # Krótka przerwa przed ponownym uruchomieniem
    threading.Thread(target=run_bot_in_thread).start() # Uruchamiamy bota ponownie
    return "Bot zrestartowany pomyślnie."


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE,
                                  bot_status=bot_status,
                                  countdown_value=countdown_value,
                                  countdown_active=countdown_active)

@app.route('/start', methods=['POST'])
def start_bot_route(): # Zmieniona nazwa funkcji, aby uniknąć konfliktu
    global bot_status
    if bot_status == "running" or bot_status == "starting":
        return render_template_string(HTML_TEMPLATE,
                                      bot_status=bot_status,
                                      countdown_value=countdown_value,
                                      countdown_active=countdown_active,
                                      message="Bot już działa lub się uruchamia.",
                                      message_type="info")
    threading.Thread(target=run_bot_in_thread).start()
    return render_template_string(HTML_TEMPLATE,
                                  bot_status=bot_status,
                                  countdown_value=countdown_value,
                                  countdown_active=countdown_active,
                                  message="Rozpoczynanie uruchamiania bota...",
                                  message_type="success")

@app.route('/stop', methods=['POST'])
def stop_bot_route(): # Zmieniona nazwa funkcji, aby uniknąć konfliktu
    global bot_status
    if bot_status == "stopped" or bot_status == "stopping":
        return render_template_string(HTML_TEMPLATE,
                                      bot_status=bot_status,
                                      countdown_value=countdown_value,
                                      countdown_active=countdown_active,
                                      message="Bot jest już zatrzymany lub się zatrzymuje.",
                                      message_type="info")
    threading.Thread(target=stop_bot_in_thread).start()
    return render_template_string(HTML_TEMPLATE,
                                  bot_status=bot_status,
                                  countdown_value=countdown_value,
                                  countdown_active=countdown_active,
                                  message="Rozpoczynanie zatrzymywania bota...",
                                  message_type="info")

@app.route('/restart', methods=['POST'])
def restart_bot_route(): # Zmieniona nazwa funkcji, aby uniknąć konfliktu
    global bot_status
    if bot_status in ["starting", "stopping", "restarting"]:
        return render_template_string(HTML_TEMPLATE,
                                      bot_status=bot_status,
                                      countdown_value=countdown_value,
                                      countdown_active=countdown_active,
                                      message="Bot jest w trakcie innej operacji, poczekaj.",
                                      message_type="info")
    threading.Thread(target=restart_bot_in_thread).start()
    return render_template_string(HTML_TEMPLATE,
                                  bot_status=bot_status,
                                  countdown_value=countdown_value,
                                  countdown_active=countdown_active,
                                  message="Rozpoczynanie restartowania bota...",
                                  message_type="info")

@app.route('/status_json')
def status_json():
    global bot_status, countdown_value, countdown_active
    return jsonify(status=bot_status,
                   countdown_value=countdown_value,
                   countdown_active=countdown_active)

if __name__ == '__main__':
    print(f"Webpanel uruchomiony na http://{PANEL_IP}:{PANEL_PORT}")
    app.run(host=PANEL_IP, port=PANEL_PORT)
