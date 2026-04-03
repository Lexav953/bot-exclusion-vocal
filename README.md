# Bot Discord — Système de vocaux automatisé

Ce projet est un bot Discord permettant de gérer automatiquement un système de temps passer dans les vocaux.

➡️ Initialement conçu pour le Discord EMS PILLBOX du serveur GTA RP LS CITY, mais totalement réutilisable pour n’importe quel serveur.


## ✨ Fonctionnalités

### 🎧 Gestion des vocaux 
- Timer EMS automatique avec paliers :
  - **1h15** → premier ping
  - **1h20** → deuxième ping
  - **1h25** → troisième ping
  - **1h30** → expulsion automatique
- Ping avec réaction obligatoire (⏱️ délai 5 minutes)
- Expulsion si aucune réaction
- Gestion des retours rapides (< 5 minutes)
- Reset automatique du timer en cas de réaction

### 🟦 Vocal PAUSE (exempté EMS)
- Salon vocal dédié à la pause
- Aucun timer EMS dans ce salon
- **Timer PAUSE de 1 heure**
- Expulsion automatique après 1h en PAUSE
- Retour depuis PAUSE → reset propre du timer EMS

### 🟩 Vocaux exemptés EMS (multiples)
- Possibilité d’ajouter **plusieurs vocaux exemptés**
- Aucun timer EMS
- Aucun ping
- Aucun timer PAUSE
- Retour vers un vocal EMS → reset propre

### 🛡️ Exemptions utilisateur
- Possibilité d’exempter un utilisateur spécifique du système EMS

### 📝 Logs détaillés
- Logs colorés dans la console
- Suivi complet des actions : entrée, sortie, ping, reset, expulsion, pause…

---

## 🚀 Installation

1. Clonez le dépôt :
https://github.com/Lexav953/bot-exclusion-vocal/

2. Installez les dépendances :
pip install -r requirements.txt

3. Créez un fichier `.env` à partir de `.env.example` :

DISCORD_TOKEN=VOTRE_TOKEN  
ID_SALON_TEXTE=ID_DU_SALON_TEXTE  
ID_VOCAL_PAUSE=ID_DU_VOCAL_PAUSE  
ID_VOCAL_EXEMPTE_EMS=ID1,ID2,ID3  
ID_UTILISATEUR_EXEMPTE=0  

4. Lancez le bot :
python votre_bot.py

---

## 📂 Structure du projet

/
├── .env  
├── .gitignore  
├── README.md  
├── env.example  
├── Requirements.txt  
└── Votre_bot.py  

---

## 🛠 Technologies

- Python 3.10+
- discord.py
- python-dotenv
