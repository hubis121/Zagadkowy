# Sprawdzanie flagi STOP
        if os.path.exists(STOP_FLAG_FILE):
            print(f"Wykryto flagę zatrzymania: {STOP_FLAG_FILE}")
            if admin_notification_channel: # <--- TEN FRAGMENT KODU
                embed = discord.Embed(
                    title="Zatrzymywanie Bota",
                    description="Bot zostanie zatrzymany przez panel webowy!",
                    color=discord.Color.red()
                )
                await admin_notification_channel.send(embed=embed) # <--- TO WYSYŁA WIADOMOŚĆ NA DISCORDA

            # Usuń flagę przed zamknięciem
            os.remove(STOP_FLAG_FILE)
            print("Usunięto flagę zatrzymania.")
            
            await bot.close()
            print("Bot został zatrzymany przez panel webowy.")
