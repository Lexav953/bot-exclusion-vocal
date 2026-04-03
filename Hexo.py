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
# CONFIG EMS
# -------------------------------------------

TOKEN = os.getenv("DISCORD_TOKEN")
ID_SALON_TEXTE = int(os.getenv("ID_SALON_TEXTE"))
ID_VOCAL_EXEMPTE_EMS = int(os.getenv("ID_VOCAL_EXEMPTE_EMS"))
ID_UTILISATEUR_EXEMPTE = int(os.getenv("ID_UTILISATEUR_EXEMPTE"))

timers_ems = {}
expulsion_forcee = set()
expulsion_pause = set()
heure_entree = {}
heure_sortie = {}


# -------------------------------------------
# VOCAUX EMS
# -------------------------------------------

@client.event
async def on_voice_state_update(member, before, after):

    # -------------------------------------------
    # DEPLACEMENT DE VOCAL 
    # -------------------------------------------
    if before.channel and after.channel and before.channel.id != after.channel.id:
        if after.channel.id != ID_VOCAL_EXEMPTE_EMS:

            # Aucun timer EMS actif → RESET
            if member.id not in timers_ems:
                log("EMS", "MOVE", f"{member.name} a été déplacé → aucun timer actif → RESET")
                heure_entree[member.id] = datetime.now()
                log("EMS", "START", f"Timer EMS démarré pour {member.name}")
                task = asyncio.create_task(timer_ems(member, after.channel.id))
                timers_ems[member.id] = task
                return

            # Timer actif → continue
            log("EMS", "MOVE", f"{member.name} a été déplacé → timer continue")
            return

    # -------------------------------------------
    # SORTIE D'UN VOCAL EMS
    # -------------------------------------------
    if before.channel and not after.channel:
        heure_sortie[member.id] = datetime.now()
        log("EMS", "LEAVE", f"{member.name} a quitté le vocal")
        return

    # -------------------------------------------
    # ENTRÉE DANS UN VOCAL EMS
    # -------------------------------------------
    if after.channel and after.channel.id != ID_VOCAL_EXEMPTE_EMS:

        # Exemption utilisateur
        if member.id == ID_UTILISATEUR_EXEMPTE:
            log("EMS", "EXEMPT", f"{member.name} est exempté EMS")
            return

        # Retour après expulsion PAUSE
        if member.id in expulsion_pause:
            expulsion_pause.remove(member.id)
            log("EMS", "RETURN", f"{member.name} revient après expulsion PAUSE → RESET")

            heure_entree[member.id] = datetime.now()
            log("EMS", "START", f"Timer EMS démarré pour {member.name}")

            if member.id in timers_ems:
                timers_ems[member.id].cancel()

            task = asyncio.create_task(timer_ems(member, after.channel.id))
            timers_ems[member.id] = task
            return

        # Retour normal
        if member.id in heure_sortie:
            absence = datetime.now() - heure_sortie[member.id]

            if absence.total_seconds() < 5 * 60:
                log("EMS", "RETURN", f"{member.name} est revenu après {int(absence.total_seconds())} sec → continue")
                return
            else:
                log("EMS", "RETURN", f"{member.name} est revenu après {int(absence.total_seconds())} sec → RESET")

        # Nouvelle entrée → RESET
        heure_entree[member.id] = datetime.now()
        log("EMS", "START", f"Timer EMS démarré pour {member.name}")

        if member.id in timers_ems:
            timers_ems[member.id].cancel()

        task = asyncio.create_task(timer_ems(member, after.channel.id))
        timers_ems[member.id] = task


# -------------------------------------------
# TIMER EMS — 45 / 50 / 55 / 60
# -------------------------------------------

async def timer_ems(member, vocal_id):
    salon = client.get_channel(ID_SALON_TEXTE)

    def delai(minutes):
        cible = heure_entree[member.id] + timedelta(minutes=minutes)
        return max(0, (cible - datetime.now()).total_seconds())

    # 45 minutes
    log("EMS", "WAIT", "Attente jusqu’à T+45 min…")
    await asyncio.sleep(delai(45))
    if not await ping_ems(member, salon, vocal_id, "45 minutes"):
        return

    # 50 minutes
    log("EMS", "WAIT", "Attente jusqu’à T+50 min…")
    await asyncio.sleep(delai(50))
    if not await ping_ems(member, salon, vocal_id, "50 minutes"):
        return

    # 55 minutes
    log("EMS", "WAIT", "Attente jusqu’à T+55 min…")
    await asyncio.sleep(delai(55))
    if not await ping_ems(member, salon, vocal_id, "55 minutes"):
        return

    # 60 minutes → expulsion
    log("EMS", "WAIT", "Attente jusqu’à T+60 min…")
    await asyncio.sleep(delai(60))

    if member.voice and member.voice.channel and member.voice.channel.id != ID_VOCAL_EXEMPTE_EMS:
        log("EMS", "EXPEL", f"{member.name} expulsé après 60 minutes")
        await salon.send(f"{member.mention} Tu as été expulsé du vocal car tu n'as pas réagi.")
        expulsion_forcee.add(member.id)
        await member.move_to(None)


# -------------------------------------------
# PING EMS
# -------------------------------------------

async def ping_ems(member, salon, vocal_id, label):

    # STOP si plus en EMS
    if not member.voice or member.voice.channel.id == ID_VOCAL_EXEMPTE_EMS:
        log("EMS", "STOP", f"{member.name} n'est plus dans un vocal EMS ({label})")

        if member.id in timers_ems:
            timers_ems[member.id].cancel()
            del timers_ems[member.id]

        return False

    # Envoi du ping
    log("EMS", "PING", f"Envoi du message ({label}) pour {member.name}")

    msg = await salon.send(
        f"{member.mention} Tu es toujours en service ? Réagis à ce message pour éviter l'expulsion du vocal. ({label})"
    )
    await msg.add_reaction("✅")

    def check(reaction, user):
        return user.id == member.id and reaction.message.id == msg.id

    try:
        await client.wait_for("reaction_add", timeout=5 * 60, check=check)

        await salon.send(f"{member.mention} Tu es encore en service.")
        log("EMS", "REACTION", f"{member.name} a réagi ({label})")

        # RESET EMS
        heure_entree[member.id] = datetime.now()
        log("EMS", "RESET", f"Timer EMS reset pour {member.name}")

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
