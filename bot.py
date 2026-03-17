import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
import asyncio

TOKEN = "TU_TOKEN_AQUI"
CANAL_ID = 123456789012345678  # <-- PONER EL ID DEL CANAL

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Guardamos timers activos
timers = {
    "ch2": None,
    "ch4": None
}

def timestamp_discord(dt):
    return f"<t:{int(dt.timestamp())}:t>"

async def programar_eventos(channel, boss, spawn_time):
    ahora = datetime.now(timezone.utc)

    aviso_10 = spawn_time - timedelta(minutes=10)
    aviso_5 = spawn_time - timedelta(minutes=5)

    # Esperar hasta aviso de 10 min
    if aviso_10 > ahora:
        await asyncio.sleep((aviso_10 - ahora).total_seconds())
        await channel.send(f"{boss.upper()} Boss in 10 min")

    # Esperar hasta aviso de 5 min
    ahora = datetime.now(timezone.utc)
    if aviso_5 > ahora:
        await asyncio.sleep((aviso_5 - ahora).total_seconds())
        await channel.send(f"{boss.upper()} Boss in 5 min")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id != CANAL_ID:
        return

    content = message.content.lower()

    # Detectar CH2 o CH4
    if content in ["ch2", "ch4"]:
        boss = content

        ahora = datetime.now(timezone.utc)
        spawn = ahora + timedelta(hours=2)

        timers[boss] = spawn

        ts = timestamp_discord(spawn)

        await message.channel.send(
            f"Boss {boss.upper()} Dead, Next Spawn {ts}"
        )

        bot.loop.create_task(programar_eventos(message.channel, boss, spawn))

    # Eliminar timers
    elif content in ["delete ch2", "delete ch4"]:
        boss = content.split()[1]

        if timers[boss]:
            timers[boss] = None
            await message.channel.send(f"{boss.upper()} timer deleted")
        else:
            await message.channel.send(f"No active timer for {boss.upper()}")

    await bot.process_commands(message)

import os
bot.run(os.getenv("TOKEN"))
