import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta

from dotenv import load_dotenv
import os

load_dotenv()

# -------------------------------------------
# INITIALISATION DU BOT
# -------------------------------------------

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

client = commands.Bot(command_prefix="!", intents=intents)

@client.event
async def on_ready():
    log("INFO", "READY", f"Connecté en tant que {client.user}")
    try:
        synced = await client.tree.sync()
        log("INFO", "SYNC", f"{len(synced)} commande(s) slash synchronisée(s)")
    except Exception as e:
        log("ERROR", "SYNC_FAIL", str(e))

# -------------------------------------------
# LOGS
# -------------------------------------------

def log(section, action, message):
    COLORS = {
        "EMS": "\033[95m",
        "INFO": "\033[92m",
        "WARN": "\033[93m",
        "ERROR": "\033[91m",
    }
    RESET = "\033[0m"
    color = COLORS.get(section, "\033[0m")
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{timestamp}][{section}][{action}] {message}{RESET}")


# -------------------------------------------
# CONFIG 
# -------------------------------------------

TOKEN = os.getenv("DISCORD_TOKEN")
ID_SALON_TEXTE = int(os.getenv("ID_SALON_TEXTE"))

# Vocal PAUSE (1 seul)
ID_VOCAL_PAUSE = int(os.getenv("ID_VOCAL_PAUSE"))

# Vocaux exemptés EMS (liste)
ID_VOCAL_EXEMPTE_EMS = [
    int(v.strip()) for v in os.getenv("ID_VOCAL_EXEMPTE_EMS").split(",")
]

ID_UTILISATEUR_EXEMPTE = int(os.getenv("ID_UTILISATEUR_EXEMPTE"))

timers_ems = {}
expulsion_forcee = set()
expulsion_pause = set()
heure_entree = {}
heure_sortie = {}


# -------------------------------------------
# VOCAUX
# -------------------------------------------

@client.event
async def on_voice_state_update(member, before, after):

    # -------------------------------------------
    # SORTIE DE VOCAL
    # -------------------------------------------
    if before.channel and not after.channel:
        heure_sortie[member.id] = datetime.now()
        log("EMS", "LEAVE", f"{member.name} a quitté le vocal")
        return

    # -------------------------------------------
    # ENTRÉE DANS LE VOCAL PAUSE
    # -------------------------------------------
    if after.channel and after.channel.id == ID_VOCAL_PAUSE:
        log("EMS", "PAUSE", f"{member.name} est entré dans le vocal PAUSE")

        # Stop timer EMS
        if member.id in timers_ems:
            timers_ems[member.id].cancel()
            del timers_ems[member.id]

        # Timer PAUSE 1h
        asyncio.create_task(timer_pause(member))

        expulsion_pause.add(member.id)
        heure_sortie[member.id] = datetime.now()
        return

    # -------------------------------------------
    # ENTRÉE DANS UN VOCAL EXEMPTÉ EMS (hors PAUSE)
    # -------------------------------------------
    if after.channel and after.channel.id in ID_VOCAL_EXEMPTE_EMS:
        log("EMS", "EXEMPT_VOCAL", f"{member.name} est entré dans un vocal exempté EMS")

        if member.id in timers_ems:
            timers_ems[member.id].cancel()
            del timers_ems[member.id]

        heure_sortie[member.id] = datetime.now()
        return

    # -------------------------------------------
    # ENTRÉE DANS UN VOCAL EMS
    # -------------------------------------------
    if after.channel and after.channel.id not in ID_VOCAL_EXEMPTE_EMS and after.channel.id != ID_VOCAL_PAUSE:

        # Exemption utilisateur
        if member.id == ID_UTILISATEUR_EXEMPTE:
            log("EMS", "EXEMPT", f"{member.name} est exempté EMS")
            return

        # Retour depuis PAUSE
        if member.id in expulsion_pause:
            expulsion_pause.remove(member.id)
            log("EMS", "RETURN", f"{member.name} revient après PAUSE → RESET")

            heure_entree[member.id] = datetime.now()

            if member.id in timers_ems:
                timers_ems[member.id].cancel()

            task = asyncio.create_task(timer_ems(member, after.channel.id))
            timers_ems[member.id] = task
            return

        # Retour normal
        if member.id in heure_sortie:
            absence = datetime.now() - heure_sortie[member.id]

            if absence.total_seconds() < 5 * 60:
                log("EMS", "RETURN", f"{member.name} revenu après {int(absence.total_seconds())} sec → continue")
                return
            else:
                log("EMS", "RETURN", f"{member.name} revenu après {int(absence.total_seconds())} sec → RESET")

        # Nouvelle entrée EMS
        heure_entree[member.id] = datetime.now()
        log("EMS", "START", f"Timer EMS démarré pour {member.name}")

        if member.id in timers_ems:
            timers_ems[member.id].cancel()

        task = asyncio.create_task(timer_ems(member, after.channel.id))
        timers_ems[member.id] = task


# -------------------------------------------
# TIMER PAUSE (1h)
# -------------------------------------------

async def timer_pause(member):
    await asyncio.sleep(60 * 60)

    if member.voice and member.voice.channel and member.voice.channel.id == ID_VOCAL_PAUSE:
        salon = client.get_channel(ID_SALON_TEXTE)
        log("EMS", "PAUSE_EXPEL", f"{member.name} expulsé après 1h en PAUSE")
        await salon.send(f"{member.mention} Tu as été expulsé du vocal PAUSE après 1 heure.")
        await member.move_to(None)


# -------------------------------------------
# TIMER — 1h15 / 1h20 / 1h25 / 1h30
# -------------------------------------------

async def timer_ems(member, vocal_id):
    salon = client.get_channel(ID_SALON_TEXTE)

    def delai(minutes):
        cible = heure_entree[member.id] + timedelta(minutes=minutes)
        return max(0, (cible - datetime.now()).total_seconds())

    # 1h15
    log("EMS", "WAIT", "Attente jusqu’à T+75 min…")
    await asyncio.sleep(delai(75))
    if not await ping_ems(member, salon, vocal_id, "1h15"):
        return

    # 1h20
    log("EMS", "WAIT", "Attente jusqu’à T+80 min…")
    await asyncio.sleep(delai(80))
    if not await ping_ems(member, salon, vocal_id, "1h20"):
        return

    # 1h25
    log("EMS", "WAIT", "Attente jusqu’à T+85 min…")
    await asyncio.sleep(delai(85))
    if not await ping_ems(member, salon, vocal_id, "1h25"):
        return

    # 1h30 → expulsion
    log("EMS", "WAIT", "Attente jusqu’à T+90 min…")
    await asyncio.sleep(delai(90))

    if member.voice and member.voice.channel and member.voice.channel.id not in ID_VOCAL_EXEMPTE_EMS and member.voice.channel.id != ID_VOCAL_PAUSE:
        log("EMS", "EXPEL", f"{member.name} expulsé après 1h30")
        await salon.send(f"{member.mention} Tu as été expulsé du vocal car tu n'as pas réagi.")
        expulsion_forcee.add(member.id)
        await member.move_to(None)


# -------------------------------------------
# PING 
# -------------------------------------------

async def ping_ems(member, salon, vocal_id, label):

    if not member.voice or member.voice.channel.id in ID_VOCAL_EXEMPTE_EMS or member.voice.channel.id == ID_VOCAL_PAUSE:
        log("EMS", "STOP", f"{member.name} n'est plus en EMS ({label})")

        if member.id in timers_ems:
            timers_ems[member.id].cancel()
            del timers_ems[member.id]

        return False

    log("EMS", "PING", f"Envoi du message ({label}) pour {member.name}")

    msg = await salon.send(
        f"{member.mention} Tu es toujours en service ? Merci de réagir pour confirmer ta présence. ({label})"
    )
    await msg.add_reaction("✅")

    def check(reaction, user):
        return user.id == member.id and reaction.message.id == msg.id

    try:
        await client.wait_for("reaction_add", timeout=5 * 60, check=check)

        await salon.send(f"{member.mention} Merci, présence confirmée. ({label})")
        log("EMS", "REACTION", f"{member.name} a réagi ({label})")

        heure_entree[member.id] = datetime.now()

        if member.id in timers_ems:
            timers_ems[member.id].cancel()

        task = asyncio.create_task(timer_ems(member, member.voice.channel.id))
        timers_ems[member.id] = task

        return False

    except asyncio.TimeoutError:
        log("EMS", "NO-REACTION", f"{member.name} n'a pas réagi ({label})")
        return True


# -------------------------------------------
# LANCEMENT DU BOT
# -------------------------------------------

client.run(TOKEN)
