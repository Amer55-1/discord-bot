import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
import asyncio
import os
from zoneinfo import ZoneInfo

# ================= CONFIG =================
CANAL_ID = 1483549231246741575
RESPAWN = timedelta(hours=2, minutes=5)

# ==========================================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Timers por boss
timers = {
    "ch2": {"spawn": None, "task": None},
    "ch4": {"spawn": None, "task": None}
}

def timestamp_discord(dt):
    return f"<t:{int(dt.timestamp())}:t>"

# ================= LOOP =================
async def ciclo_boss(channel, boss):
    try:
        while timers[boss]["spawn"]:
            spawn_time = timers[boss]["spawn"]

            ahora = datetime.now(timezone.utc)

            aviso_10 = spawn_time - timedelta(minutes=10)
            aviso_5 = spawn_time - timedelta(minutes=5)

            # Aviso 10 min
            if aviso_10 > ahora:
                await asyncio.sleep((aviso_10 - ahora).total_seconds())
                if not timers[boss]["spawn"]:
                    return
                await channel.send(f"{boss.upper()} Boss in 10 min")

            # Aviso 5 min
            ahora = datetime.now(timezone.utc)
            if aviso_5 > ahora:
                await asyncio.sleep((aviso_5 - ahora).total_seconds())
                if not timers[boss]["spawn"]:
                    return
                await channel.send(f"{boss.upper()} Boss in 5 min")

            # Esperar spawn
            ahora = datetime.now(timezone.utc)
            if spawn_time > ahora:
                await asyncio.sleep((spawn_time - ahora).total_seconds())

            if not timers[boss]["spawn"]:
                return

            # Boss aparece
            await channel.send(f"{boss.upper()} BOSS UP!")

            # Siguiente spawn automático
            new_spawn = spawn_time + RESPAWN
            timers[boss]["spawn"] = new_spawn

            ts = timestamp_discord(new_spawn)
            await channel.send(f"{boss.upper()} Next Spawn {ts} (auto)")

    except asyncio.CancelledError:
        pass

# ================= PARSE NY =================
def parse_ny_time(hour_str):
    try:
        ny_tz = ZoneInfo("America/New_York")
        ahora_ny = datetime.now(ny_tz)

        hour, minute = map(int, hour_str.split(":"))

        target = ahora_ny.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # Si la hora es futura → fue ayer
        if target > ahora_ny:
            target -= timedelta(days=1)

        return target.astimezone(timezone.utc)

    except:
        return None

# ================= BOT =================
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id != CANAL_ID:
        return

    content = message.content.lower()

    # ===== ACTIVAR TIMER =====
    if content in ["ch2", "ch4"]:
        boss = content

        if timers[boss]["task"]:
            timers[boss]["task"].cancel()

        ahora = datetime.now(timezone.utc)
        spawn = ahora + timedelta(hours=2)

        timers[boss]["spawn"] = spawn

        ts = timestamp_discord(spawn)

        await message.channel.send(
            f"Boss {boss.upper()} Dead, Next Spawn {ts}"
        )

        task = bot.loop.create_task(ciclo_boss(message.channel, boss))
        timers[boss]["task"] = task

    # ===== RESET DESDE HORA NY =====
    elif content.startswith("reset"):
        parts = content.split()

        if len(parts) != 3:
            await message.channel.send("Use: reset ch2 02:34")
            return

        _, boss, hora = parts

        if boss not in timers:
            return

        muerte = parse_ny_time(hora)

        if not muerte:
            await message.channel.send("Invalid format. Use HH:MM")
            return

        spawn = muerte + timedelta(hours=2)

        if timers[boss]["task"]:
            timers[boss]["task"].cancel()

        timers[boss]["spawn"] = spawn

        ts = timestamp_discord(spawn)

        await message.channel.send(
            f"{boss.upper()} Reset (death NY {hora}) → Next Spawn {ts}"
        )

        task = bot.loop.create_task(ciclo_boss(message.channel, boss))
        timers[boss]["task"] = task

    # ===== DELETE =====
    elif content in ["delete ch2", "delete ch4"]:
        boss = content.split()[1]

        if timers[boss]["spawn"]:
            timers[boss]["spawn"] = None

            if timers[boss]["task"]:
                timers[boss]["task"].cancel()
                timers[boss]["task"] = None

            await message.channel.send(f"{boss.upper()} timer deleted")
        else:
            await message.channel.send(f"No active timer for {boss.upper()}")

    await bot.process_commands(message)

# ================= RUN =================
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("TOKEN no encontrado en Railway")

bot.run(TOKEN)
