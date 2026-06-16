import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
import asyncio
import os
from zoneinfo import ZoneInfo

# ================= CONFIG =================
CANAL_ID = 1483549231246741575
RESPAWN = timedelta(hours=2, minutes=5)
BOSS_ROLE_ID = 1516505086686396496

# ==========================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # necesario para roles

bot = commands.Bot(command_prefix="!", intents=intents)

# Timers
timers = {
    "ch2": {"spawn": None, "task": None},
    "ch4": {"spawn": None, "task": None}
}

# ================= HELPERS =================
def timestamp_discord(dt):
    ts = int(dt.timestamp())
    return f"<t:{ts}:t> (<t:{ts}:R>)"


def boss_role(guild):
    return guild.get_role(BOSS_ROLE_ID)


def boss_ping():
    return f"<@&{BOSS_ROLE_ID}>"


# ================= BOTONES =================
class BossRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Unirme a Boss-Timer", style=discord.ButtonStyle.green)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = boss_role(interaction.guild)

        if role is None:
            await interaction.response.send_message("Rol no encontrado ❌", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.response.send_message("Ya tienes el rol.", ephemeral=True)
            return

        await interaction.user.add_roles(role)
        await interaction.response.send_message("Te uniste a Boss-Timer ✅", ephemeral=True)

    @discord.ui.button(label="Salir del Boss-Timer", style=discord.ButtonStyle.red)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = boss_role(interaction.guild)

        if role is None:
            await interaction.response.send_message("Rol no encontrado ❌", ephemeral=True)
            return

        if role not in interaction.user.roles:
            await interaction.response.send_message("No tienes el rol.", ephemeral=True)
            return

        await interaction.user.remove_roles(role)
        await interaction.response.send_message("Saliste del Boss-Timer ❌", ephemeral=True)


# ================= LOOP =================
async def ciclo_boss(channel, boss):
    print(f"Starting ciclo_boss for {boss}")

    try:
        while timers[boss]["spawn"]:
            spawn_time = timers[boss]["spawn"]

            now = datetime.now(timezone.utc)

            while spawn_time <= now:
                spawn_time += RESPAWN

            timers[boss]["spawn"] = spawn_time

            aviso_10 = spawn_time - timedelta(minutes=10)
            aviso_5 = spawn_time - timedelta(minutes=5)

            now = datetime.now(timezone.utc)

            # 10 min
            if aviso_10 > now:
                await asyncio.sleep((aviso_10 - now).total_seconds())
                if not timers[boss]["spawn"]:
                    return

                await channel.send(
                    f"{boss.upper()} Boss in 10 min {boss_ping()}",
                    allowed_mentions=discord.AllowedMentions(roles=True)
                )

            now = datetime.now(timezone.utc)

            # 5 min
            if aviso_5 > now:
                await asyncio.sleep((aviso_5 - now).total_seconds())
                if not timers[boss]["spawn"]:
                    return

                await channel.send(
                    f"{boss.upper()} Boss in 5 min {boss_ping()}",
                    allowed_mentions=discord.AllowedMentions(roles=True)
                )

            now = datetime.now(timezone.utc)
            wait = (spawn_time - now).total_seconds()

            if wait > 0:
                await asyncio.sleep(wait)

            if not timers[boss]["spawn"]:
                return

            await channel.send(f"{boss.upper()} BOSS UP!")

            spawn_time += RESPAWN
            timers[boss]["spawn"] = spawn_time

            ts = timestamp_discord(spawn_time)
            await channel.send(f"{boss.upper()} Next Spawn {ts} (auto)")

    except asyncio.CancelledError:
        print("Task cancelada")


# ================= NY PARSE =================
def parse_ny_time(hour_str):
    try:
        ny = ZoneInfo("America/New_York")
        now = datetime.now(ny)

        h, m = map(int, hour_str.split(":"))

        target = now.replace(hour=h, minute=m, second=0, microsecond=0)

        if target > now:
            target -= timedelta(days=1)

        return target.astimezone(timezone.utc)

    except:
        return None


# ================= EVENTS =================
@bot.event
async def on_ready():
    print(f"Bot listo como {bot.user}")

    channel = bot.get_channel(CANAL_ID)
    if channel:
        await channel.send("🎯 Boss Timer Panel", view=BossRoleView())


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id != CANAL_ID:
        return

    content = message.content.lower()

    # ===== START =====
    if content in ["ch2", "ch4"]:
        boss = content

        if timers[boss]["task"]:
            timers[boss]["task"].cancel()

        now = datetime.now(timezone.utc)
        spawn = now + timedelta(hours=2)

        timers[boss]["spawn"] = spawn

        ts = timestamp_discord(spawn)

        await message.channel.send(
            f"Boss {boss.upper()} Dead, Next Spawn {ts}"
        )

        timers[boss]["task"] = bot.loop.create_task(ciclo_boss(message.channel, boss))


    # ===== RESET =====
    elif content.startswith("reset"):
        parts = content.split()

        if len(parts) != 3:
            await message.channel.send("Use: reset ch2 02:34")
            return

        _, boss, hora = parts

        if boss not in timers:
            return

        death = parse_ny_time(hora)

        if not death:
            await message.channel.send("Invalid time HH:MM")
            return

        spawn = death + timedelta(hours=2)

        if timers[boss]["task"]:
            timers[boss]["task"].cancel()

        timers[boss]["spawn"] = spawn

        ts = timestamp_discord(spawn)

        await message.channel.send(
            f"{boss.upper()} Reset → Next Spawn {ts}"
        )

        timers[boss]["task"] = bot.loop.create_task(ciclo_boss(message.channel, boss))


    # ===== DELETE =====
    elif content in ["delete ch2", "delete ch4"]:
        boss = content.split()[1]

        timers[boss]["spawn"] = None

        if timers[boss]["task"]:
            timers[boss]["task"].cancel()
            timers[boss]["task"] = None

        await message.channel.send(f"{boss.upper()} timer deleted")

    await bot.process_commands(message)


# ================= RUN =================
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("TOKEN no encontrado")

bot.run(TOKEN)
