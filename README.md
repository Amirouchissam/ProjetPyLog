# SSH Log Analysis Pipeline

Pipeline Python d'analyse de journaux d'authentification SSH (`auth.log`).  
Il ingère, parse, géolocalise et stocke les événements dans PostgreSQL, puis produit un **dashboard image PNG** avec matplotlib.

---

## Contexte

Les serveurs Linux exposés à Internet reçoivent en permanence des tentatives de connexion SSH automatisées. Ce projet analyse ces journaux pour :

- Identifier les pays d'où proviennent les attaques
- Recenser les connexions légitimes par utilisateur
- Repérer les tentatives avec des utilisateurs inexistants sur le système

---

## Architecture

```
log_analysis/
│
├── data/                       # Fichiers auth.log bruts (.log, .gz)
│
├── logger/
│   └── app_logger.py           # Logger centralisé (RotatingFileHandler + console)
│
├── ingestion/
│   └── raw.py                  # Lecture de tous les fichiers de logs
│
├── processing/
│   ├── extract_transforme.py   # Parsing regex des événements SSH
│   └── geo_location.py         # Géolocalisation des IPs (ipinfo.io)
│
├── storage/
│   └── db.py                   # PostgreSQL : schéma, insertion, requêtes
│
├── serving/
│   ├── dashboard.py            # Génération du dashboard PNG (matplotlib)
│   └── dashboard.png           # Image générée (ouvrir avec n'importe quel viewer)
│
├── logs/
│   └── app.log                 # Logs applicatifs (rotation automatique)
│
├── main.py                     # Orchestrateur du pipeline
├── pyproject.toml
└── README.md
```

---

## Packages Python utilisés

Uniquement les packages vus en cours ou autorisés explicitement :

| Package | Origine | Usage |
|---------|---------|-------|
| `logging` + `RotatingFileHandler` | Stdlib — vu en cours | Logs applicatifs par module |
| `re` | Stdlib — vu en cours | Parsing regex du auth.log |
| `gzip` | Stdlib | Lecture des fichiers .gz |
| `json`, `urllib` | Stdlib | Appels HTTP géolocalisation |
| `pathlib`, `os` | Stdlib | Gestion des chemins |
| `io`, `socket` | Stdlib | Réseau et buffers |
| `argparse`, `time` | Stdlib | CLI et chronométrage |
| `matplotlib` | Installé dans le projet | Graphiques du dashboard PNG |
| `psycopg2-binary` | Autorisé par le prof | Connexion PostgreSQL |

---

## Prérequis

- Python 3.14+
- uv (gestionnaire de paquets)
- PostgreSQL 14+ **sur le port 4001**

---

## Installation

```bash
git clone <url-du-depot>
cd log_analysis
uv sync
```

---

## Configuration PostgreSQL (port 4001)

Créer la base de données une seule fois :

```bash
# Avec psql
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -p 4001 -c "CREATE DATABASE log_analysis;"
```

La table `ssh_events` est **créée automatiquement** au premier lancement.

Paramètres de connexion dans `storage/db.py` :

```python
DB_CONFIG = {
    "host":            "localhost",
    "port":            4001,
    "dbname":          "log_analysis",
    "user":            "postgres",
    "password":        "123",
    "client_encoding": "utf8",
}
```

---

## Lancement

```bash
# Pipeline complet (avec géolocalisation réseau)
python main.py

# Sans géolocalisation (rapide, hors ligne)
python main.py --skip-geo

# Dry-run (aucune écriture en base)
python main.py --skip-db --skip-geo

# Répertoire de logs personnalisé
python main.py --data-dir ./data
```

---

## Dashboard PNG

Après le lancement, le fichier `serving/dashboard.png` contient 3 graphiques :

| Graphique | Description |
|-----------|-------------|
| ① Tentatives échouées par pays | Bar chart horizontal, top 15 pays sources |
| ② Connexions réussies par utilisateur | Bar chart vertical, top 12 users |
| ③ Utilisateurs invalides | Bar chart horizontal, top 15 logins inexistants |

---

## Logging

Format du cours : `date|level|nom_module|message`

```
10-11-2026 10:20:54|INFO|ingestion.raw|Total lignes lues : 65565
10-11-2026 10:20:55|ERROR|storage.db|Connexion impossible : ...
```

Les logs sont écrits dans `logs/app.log` avec rotation automatique (`RotatingFileHandler`, 500 Ko × 5 fichiers).

Chaque module loggue ses propres erreurs :

| Module | Niveaux utilisés |
|--------|-----------------|
| `ingestion.raw` | DEBUG, INFO, WARNING, ERROR |
| `processing.extract_transforme` | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `processing.geo_location` | DEBUG, INFO, WARNING, ERROR |
| `storage.db` | INFO, WARNING, ERROR |
| `serving.dashboard` | INFO, WARNING, ERROR |
| `main` | INFO, WARNING, ERROR, CRITICAL |

---

## Commits Git progressifs

| Commit | Module |
|--------|--------|
| `feat(logger)` | Logger avec RotatingFileHandler |
| `feat(ingestion)` | Lecture .log + .gz |
| `feat(processing)` | Regex SSH + géolocalisation |
| `feat(storage)` | PostgreSQL CRUD |
| `feat(serving)` | Dashboard PNG matplotlib |
| `feat(main)` | Orchestrateur |
| `docs` | README + .gitignore |
| `fix(geo_location)` | Déduplication IPs + timeout SSL |
| `fix(storage)` | Mot de passe + encodage UTF-8 |
| `refactor(logger)` | RotatingFileHandler (cours) |
| `feat(serving)` | Remplacement HTML → PNG |

---

## Auteur

Projet réalisé dans le cadre du cours **Python Avancée — Semestre 5**.  
Modules : `logging`, `re`, OOP / type hints, `psycopg2`, `matplotlib`.
