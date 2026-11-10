# Analyse des logs SSH (auth.log)

Projet d'ingestion, d'analyse et de visualisation des journaux d'authentification SSH sous Linux. Le pipeline extrait les événements de connexion via des expressions régulières, enrichit les adresses IP avec leur géolocalisation, stocke les résultats dans une base PostgreSQL et génère un tableau de bord récapitulatif sous forme d'image PNG (`dashboard.png`).

---

## 1. Structure du projet

Le projet est découpé en modules indépendants et réutilisables :

```text
log_analysis/
│
├── data/                       # Fichiers de logs sources (auth.log, .gz)
├── logs/                       # Fichier de logs applicatif (app.log)
│
├── logger/
│   └── app_logger.py           # Configuration centralisée de logging
│
├── ingestion/
│   └── raw.py                  # Lecture des fichiers texte et archives .gz
│
├── processing/
│   ├── extract_transforme.py   # Parsing regex et classification des événements
│   └── geo_location.py         # Géolocalisation des adresses IP (ipinfo.io)
│
├── storage/
│   └── db.py                   # Connexion PostgreSQL, création de table et requêtes
│
├── serving/
│   ├── dashboard.py            # Génération du dashboard graphique matplotlib
│   └── dashboard.png           # Image PNG produite par le pipeline
│
├── main.py                     # Script principal (orchestrateur)
├── pyproject.toml              # Configuration du projet et dépendances
└── README.md
```

---

## 2. Dépendances et environnement

Le projet utilise uniquement les modules standards Python vus en cours (`logging`, `re`, `urllib`, `gzip`, `json`, `socket`, `pathlib`, `typing`, `argparse`), complétés par deux bibliothèques tierces nécessaires au stockage et au tracé :

| Bibliothèque | Rôle |
|---|---|
| `psycopg2-binary` | Driver de communication avec PostgreSQL |
| `matplotlib` | Tracé et sauvegarde du tableau de bord PNG |

### Installation avec `uv`

```bash
# Cloner le dépôt
git clone https://github.com/Amirouchissam/ProjetPyLog.git
cd log_analysis

# Installer les dépendances dans le venv
uv sync
```

---

## 3. Configuration de PostgreSQL

Le module de stockage se connecte à PostgreSQL sur le **port 4001** (modifiable dans `storage/db.py`) :

```python
DB_CONFIG = {
    "host":     "localhost",
    "port":     4001,
    "dbname":   "log_analysis",
    "user":     "postgres",
    "password": "issamam1010",
}
```

La table `ssh_events` est créée automatiquement si elle n'existe pas lors du premier lancement :

```sql
CREATE TABLE IF NOT EXISTS ssh_events (
    id              SERIAL PRIMARY KEY,
    month           VARCHAR(3)   NOT NULL,
    day             INTEGER      NOT NULL,
    time            VARCHAR(8)   NOT NULL,
    host            VARCHAR(255) NOT NULL,
    service         VARCHAR(50)  NOT NULL,
    event_type      VARCHAR(20)  NOT NULL,   -- 'failed', 'accepted', 'invalid_user'
    ip              VARCHAR(45)  NOT NULL,
    username        VARCHAR(100) NOT NULL,
    is_invalid_user BOOLEAN      NOT NULL DEFAULT FALSE,
    country         VARCHAR(100) DEFAULT 'Unknown',
    city            VARCHAR(100) DEFAULT 'Unknown',
    org             VARCHAR(255) DEFAULT 'Unknown',
    inserted_at     TIMESTAMP    DEFAULT NOW()
);
```

---

## 4. Exécution du pipeline

Le script `main.py` pilote l'ensemble des étapes dans l'ordre.

```bash
# Exécution complète (ingestion -> parsing -> géolocalisation -> base -> dashboard PNG)
uv run python main.py

# Mode rapide sans appels API réseau (recommandé si connexion limitée)
uv run python main.py --skip-geo

# Mode test sans base de données (dry-run)
uv run python main.py --skip-geo --skip-db
```

---

## 5. Dashboard généré (`serving/dashboard.png`)

Le dashboard produit est une image PNG unique haute résolution sauvegardée dans `serving/dashboard.png`. Il regroupe les 3 visualisations demandées :

1. **Tentatives échouées par pays** : diagramme à barres horizontales identifiant les pays d'où proviennent le plus d'attaques.
2. **Connexions réussies par utilisateur** : diagramme à barres montrant le nombre d'accès légitimes acceptés par compte.
3. **Tentatives échouées avec utilisateurs invalides** : diagramme détaillant les comptes inexistants les plus ciblés par les attaques par force brute (ex : `admin`, `esisa`, `support`, `ubuntu`, `test`).

Un bandeau supérieur résume également les compteurs globaux (total échecs, total succès, total invalid users, pays distincts).

---

## 6. Gestion des logs et erreurs par module

Tous les modules enregistrent leurs événements dans `logs/app.log` (niveau DEBUG) et affichent les informations clés en console (niveau INFO).

Les erreurs potentielles sont interceptées et journalisées module par module :

- **`logger/app_logger.py`** : création sécurisée du dossier `logs/`, gestion des permissions sur le système de fichiers.
- **`ingestion/raw.py`** : vérification de l'existence du dossier `data/`, capture des `PermissionError`, gestion des archives gzip corrompues (`gzip.BadGzipFile`) et erreurs d'encodage.
- **`processing/extract_transforme.py`** : détection des lignes vides ou non conformes, filtrage strict sur `sshd`, extraction sécurisée par expressions régulières compilées (`re.compile`).
- **`processing/geo_location.py`** : gestion des timeouts réseau (`socket.timeout`), erreurs HTTP (`urllib.error.HTTPError`), parsing JSON invalide, mise en cache mémoire des IPs et interruption propre (`KeyboardInterrupt`).
- **`storage/db.py`** : capture des `OperationalError` et `DatabaseError`, vérification des champs obligatoires avant insertion, transactions avec rollback en cas d'erreur.
- **`serving/dashboard.py`** : gestion des jeux de données vides, capture des erreurs de rendu matplotlib et des exceptions d'écriture disque.
- **`main.py`** : arrêt propre avec code retour approprié (`sys.exit(1)`) si une étape bloquante échoue.
