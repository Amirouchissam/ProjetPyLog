# SSH Log Analysis Pipeline

Pipeline Python d'analyse de journaux d'authentification SSH (`auth.log`).  
Il ingère, parse, géolocalise et stocke les événements dans une base PostgreSQL, puis génère un dashboard HTML interactif.

---

## Contexte

Les serveurs Linux exposés à Internet reçoivent en permanence des tentatives de connexion SSH automatisées (brute-force, scans, bots). Ce projet vise à analyser ces journaux pour :

- Identifier les pays sources des attaques
- Recenser les connexions légitimes par utilisateur
- Repérer les tentatives avec des utilisateurs inexistants

---

## Architecture du projet

```
log_analysis/
│
├── data/                       # Fichiers auth.log bruts (.log, .gz)
│
├── logger/
│   └── app_logger.py           # Logger centralisé (fichier + console)
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
│   ├── dashboard.py            # Génération du dashboard HTML
│   └── dashboard.html          # Fichier généré (ouvrir dans le navigateur)
│
├── logs/
│   └── app.log                 # Logs applicatifs (créé automatiquement)
│
├── main.py                     # Orchestrateur du pipeline
├── pyproject.toml              # Dépendances (uv)
└── README.md
```

---

## Prérequis

| Outil       | Version minimum |
|-------------|----------------|
| Python      | 3.14+          |
| uv          | 0.5+           |
| PostgreSQL  | 14+            |

Paquets Python utilisés (tous standards ou déjà installés) :

| Paquet           | Usage                         |
|-----------------|-------------------------------|
| `psycopg2-binary` | Connexion PostgreSQL          |
| `matplotlib`      | Génération des graphiques     |
| `requests`        | Appels HTTP (géolocalisation) |
| `re`, `gzip`, `logging`, `json`, `urllib` | Bibliothèque standard Python |

---

## Installation

```bash
# 1. Cloner le dépôt
git clone <url-du-depot>
cd log_analysis

# 2. Créer l'environnement virtuel et installer les dépendances
uv sync

# 3. Placer vos fichiers auth.log dans data/
#    (formats acceptés : .log, .1, .2, .gz)
```

---

## Configuration PostgreSQL

Le projet attend une base PostgreSQL sur le **port 4001**.

### Démarrage rapide (si PostgreSQL est installé localement)

```bash
# Créer la base de données
createdb -p 4001 -U postgres log_analysis
```

### Modifier la configuration

Éditer le dictionnaire `DB_CONFIG` dans [`storage/db.py`](storage/db.py) :

```python
DB_CONFIG = {
    "host":     "localhost",
    "port":     4001,
    "dbname":   "log_analysis",
    "user":     "postgres",
    "password": "postgres",
}
```

La table `ssh_events` est **créée automatiquement** au premier lancement.

### Schéma de la table

| Colonne           | Type         | Description                            |
|-------------------|-------------|----------------------------------------|
| `id`              | SERIAL PK   | Identifiant auto-incrémenté            |
| `month`           | VARCHAR(3)  | Mois de l'événement (ex: `May`)        |
| `day`             | INTEGER     | Jour du mois                           |
| `time`            | VARCHAR(8)  | Heure `HH:MM:SS`                       |
| `host`            | VARCHAR     | Nom de l'hôte serveur                  |
| `service`         | VARCHAR     | Service (`sshd`)                       |
| `event_type`      | VARCHAR(20) | `accepted`, `failed`, `invalid_user`   |
| `ip`              | VARCHAR(45) | Adresse IP source                      |
| `username`        | VARCHAR     | Nom d'utilisateur tenté                |
| `is_invalid_user` | BOOLEAN     | True si l'utilisateur n'existe pas     |
| `country`         | VARCHAR     | Pays (géolocalisation)                 |
| `city`            | VARCHAR     | Ville (géolocalisation)                |
| `org`             | VARCHAR     | Organisation / FAI                     |
| `inserted_at`     | TIMESTAMP   | Date d'insertion automatique           |

---

## Utilisation

### Lancement standard

```bash
python main.py
```

### Options disponibles

```bash
python main.py --data-dir ./data     # Répertoire des logs (défaut: ./data)
python main.py --skip-geo            # Désactive la géolocalisation (mode hors ligne)
python main.py --skip-db             # Mode dry-run (pas d'écriture en base)
```

### Exemple de sortie

```
2026-11-09 23:50:00 | INFO     | main                          | DÉMARRAGE DU PIPELINE LOG ANALYSIS
2026-11-09 23:50:00 | INFO     | ingestion.raw                 | Total lignes lues : 48532
2026-11-09 23:50:01 | INFO     | processing.extract_transforme | Parsing terminé : 3812 événements extraits
2026-11-09 23:50:45 | INFO     | processing.geo_location       | Géolocalisation terminée : 3812 enrichis
2026-11-09 23:50:45 | INFO     | storage.db                    | Insertion terminée : 3812 insérés
2026-11-09 23:50:46 | INFO     | serving.dashboard             | Dashboard généré : serving/dashboard.html
2026-11-09 23:50:46 | INFO     | main                          | PIPELINE TERMINÉ en 46.3 secondes
```

---

## Dashboard

Après le lancement, ouvrir dans le navigateur :

```
serving/dashboard.html
```

Le dashboard présente :

1. **KPIs globaux** — total des tentatives échouées, réussies, utilisateurs invalides et pays distincts
2. **Graphique : tentatives échouées par pays** — bar chart horizontal (Top 20 pays)
3. **Graphique : connexions réussies par utilisateur** — bar chart (Top 15 utilisateurs)
4. **Tableau : tentatives avec utilisateurs invalides** — Top 50 avec IP, pays et nombre de tentatives

---

## Logging

Tous les modules écrivent dans `logs/app.log` (niveau DEBUG) et dans la console (niveau INFO).

Format des logs :
```
2026-11-09 23:50:00 | INFO     | processing.geo_location       | Géolocalisation réussie pour 45.148.10.152 → DE / Frankfurt
```

Chaque module loggue les erreurs suivantes :

| Module                  | Erreurs loggées                                      |
|-------------------------|------------------------------------------------------|
| `ingestion.raw`         | Répertoire introuvable, permission refusée, fichier corrompu |
| `processing.extract`    | Ligne non parsée, exception interne                  |
| `processing.geo_location` | Timeout réseau, HTTP non-200, JSON invalide        |
| `storage.db`            | Connexion impossible, erreur SQL, clé manquante      |
| `serving.dashboard`     | Données vides, erreur écriture fichier               |
| `main`                  | Erreur critique à chaque étape (CRITICAL si fatal)   |

---

## Flux du pipeline

```
data/auth.log.*
      │
      ▼
[ingestion.raw]          Lecture brute (texte + gzip)
      │
      ▼
[processing.extract]     Regex → {event_type, ip, username, ...}
      │
      ▼
[processing.geo_location] ipinfo.io → {country, city, org}
      │
      ▼
[storage.db]             INSERT INTO ssh_events (PostgreSQL :4001)
      │
      ▼
[serving.dashboard]      HTML avec graphiques matplotlib embarqués
```

---

## Auteur

Projet réalisé dans le cadre du cours **Python Avancée — S5**.  
Tous les modules sont documentés, testables individuellement et committés progressivement.
