
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
ROLE_PANEL_CHANNEL_ID = 1515422185462956082
# ==========================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

timers = {
    "ch2": {"spawn": None, "task": None},
    "ch4": {"spawn": None, "task": None}
}

def timestamp_discord(dt):
    ts = int(dt.timestamp())
    return f"<t:{ts}:t> (<t:{ts}:R>)"

def boss_role(guild):
    return guild.get_role(BOSS_ROLE_ID)


async def enviar_dm_rol(guild, mensaje):
    role = guild.get_role(BOSS_ROLE_ID)
    if role is None:
        return

    enviados = 0
    for member in role.members:
        if member.bot:
            continue
        try:
            await member.send(mensaje)
            enviados += 1
            await asyncio.sleep(0.8)
        except discord.Forbidden:
            pass
        except Exception as e:
            print(f"Error enviando DM a {member}: {e}")
    print(f"DM enviados: {enviados}")

class BossRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Unirme a Boss-Timer", style=discord.ButtonStyle.green)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = boss_role(interaction.guild)
        if role is None:
            return await interaction.response.send_message("Rol no encontrado ❌", ephemeral=True)
        if role in interaction.user.roles:
            return await interaction.response.send_message("Ya tienes el rol.", ephemeral=True)
        await interaction.user.add_roles(role)
        await interaction.response.send_message("Te uniste a Boss-Timer ✅", ephemeral=True)

    @discord.ui.button(label="Salir del Boss-Timer", style=discord.ButtonStyle.red)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = boss_role(interaction.guild)
        if role is None:
            return await interaction.response.send_message("Rol no encontrado ❌", ephemeral=True)
        if role not in interaction.user.roles:
            return await interaction.response.send_message("No tienes el rol.", ephemeral=True)
        await interaction.user.remove_roles(role)
        await interaction.response.send_message("Saliste del Boss-Timer ❌", ephemeral=True)

async def ciclo_boss(channel, boss):
    guild = channel.guild
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
            if aviso_10 > now:
                await asyncio.sleep((aviso_10 - now).total_seconds())
                if not timers[boss]["spawn"]:
                    return
                await channel.send(f"{boss.upper()} Boss in 10 min ",
                                   allowed_mentions=discord.AllowedMentions.none())
                await enviar_dm_rol(guild, f"🔔 {boss.upper()} Boss in 10 minutes!")

            now = datetime.now(timezone.utc)
            if aviso_5 > now:
                await asyncio.sleep((aviso_5 - now).total_seconds())
                if not timers[boss]["spawn"]:
                    return
                await channel.send(f"{boss.upper()} Boss in 5 min ",
                                   allowed_mentions=discord.AllowedMentions.none())
                await enviar_dm_rol(guild, f"⚠️ {boss.upper()} Boss in 5 minutes!")

            now = datetime.now(timezone.utc)
            wait = (spawn_time - now).total_seconds()
            if wait > 0:
                await asyncio.sleep(wait)

            if not timers[boss]["spawn"]:
                return

            await channel.send(f"{boss.upper()} BOSS UP!")

            spawn_time += RESPAWN
            timers[boss]["spawn"] = spawn_time
            
    except asyncio.CancelledError:
        print("Task cancelada")

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

@bot.event
async def on_ready():
    print(f"Bot listo como {bot.user}")

    bot.add_view(BossRoleView())

    panel_channel = bot.get_channel(ROLE_PANEL_CHANNEL_ID)

    print("Canal:", panel_channel)

    if panel_channel is None:
        print("❌ No se encontró el canal")
        return

    found = False

    async for msg in panel_channel.history(limit=20):
        print("Mensaje encontrado:", msg.id)

        if msg.author.id == bot.user.id and msg.components:
            print("✅ Panel ya existe")
            found = True
            break

    if not found:
        print("📨 Creando panel...")

        await panel_channel.send(
            "## 🔔 Boss Timer Notifications\n\n"
            "Receive a **DM** whenever a boss is about to spawn.\n\n"
            "Use the buttons below to join or leave the notification role.",
            view=BossRoleView()
        )

        print("✅ Panel enviado")

@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id != CANAL_ID:
        return

    content = message.content.lower()

    if content in ["ch2","ch4"]:
        boss = content
        if timers[boss]["task"]:
            timers[boss]["task"].cancel()
        spawn = datetime.now(timezone.utc) + timedelta(hours=2)
        timers[boss]["spawn"] = spawn
        await message.channel.send(f"Boss {boss.upper()} Dead, Next Spawn {timestamp_discord(spawn)}")
        timers[boss]["task"] = bot.loop.create_task(ciclo_boss(message.channel,boss))

    elif content.startswith("reset"):
        parts = content.split()
        if len(parts)!=3:
            return await message.channel.send("Use: reset ch2 02:34")
        _, boss, hora = parts
        if boss not in timers:
            return
        death = parse_ny_time(hora)
        if not death:
            return await message.channel.send("Invalid time HH:MM")
        spawn = death + timedelta(hours=2)
        if timers[boss]["task"]:
            timers[boss]["task"].cancel()
        timers[boss]["spawn"] = spawn
        await message.channel.send(f"{boss.upper()} Reset → Next Spawn {timestamp_discord(spawn)}")
        timers[boss]["task"] = bot.loop.create_task(ciclo_boss(message.channel,boss))

    elif content in ["delete ch2","delete ch4"]:
        boss = content.split()[1]
        timers[boss]["spawn"] = None
        if timers[boss]["task"]:
            timers[boss]["task"].cancel()
            timers[boss]["task"] = None
        await message.channel.send(f"{boss.upper()} timer deleted")

    await bot.process_commands(message)

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN no encontrado")

bot.run(TOKEN)
