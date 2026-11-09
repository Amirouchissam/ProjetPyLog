"""
Module : storage/db.py
Rôle   : Gérer la connexion à PostgreSQL (port 4001) et les opérations CRUD
         pour les événements SSH analysés.

Tables créées automatiquement :
  - ssh_events : stocke chaque événement SSH parsé et géolocalisé.

Dépendance : psycopg2-binary
"""
import psycopg2
from psycopg2 import sql, OperationalError, DatabaseError, InterfaceError

from logger.app_logger import get_logger

_log = get_logger("storage.db")

# ---------------------------------------------------------------------------
# Configuration de la connexion
# ---------------------------------------------------------------------------
DB_CONFIG = {
    "host":     "localhost",
    "port":     4001,
    "dbname":   "log_analysis",
    "user":     "postgres",
    "password": "issamam1010",
    # Note: client_encoding intentionally omitted — let psycopg2 negotiate with the
    # server automatically. Forcing 'utf8' on a Windows/French PostgreSQL instance
    # causes UnicodeDecodeError when the server returns accented error messages
    # (e.g. Latin-1 0xe9 'é') before the encoding handshake completes.
}

# SQL de création de la table principale
_CREATE_TABLE_SQL = """
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
"""


# ---------------------------------------------------------------------------
# Connexion
# ---------------------------------------------------------------------------

def get_connection():
    """
    Ouvre et retourne une connexion psycopg2 à PostgreSQL.

    Retour
    ------
    psycopg2.connection | None

    Erreurs possibles loggées
    -------------------------
    - Impossible de se connecter    → ERROR
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        _log.info(
            "Connexion PostgreSQL établie (host=%s port=%d dbname=%s)",
            DB_CONFIG["host"], DB_CONFIG["port"], DB_CONFIG["dbname"]
        )
        return conn
    except OperationalError as exc:
        _log.error(
            "Impossible de se connecter à PostgreSQL (%s:%d / %s) : %s",
            DB_CONFIG["host"], DB_CONFIG["port"], DB_CONFIG["dbname"], exc
        )
        return None
    except Exception as exc:
        _log.error(
            "Erreur inattendue lors de la connexion à PostgreSQL (%s:%d / %s) : %s",
            DB_CONFIG["host"], DB_CONFIG["port"], DB_CONFIG["dbname"], exc
        )
        return None


# ---------------------------------------------------------------------------
# Initialisation du schéma
# ---------------------------------------------------------------------------

def init_schema(conn) -> bool:
    """
    Crée la table ssh_events si elle n'existe pas encore.

    Paramètres
    ----------
    conn : psycopg2.connection

    Retour
    ------
    bool : True si succès, False si erreur.

    Erreurs possibles loggées
    -------------------------
    - Connexion None             → ERROR
    - Erreur SQL                 → ERROR
    """
    if conn is None:
        _log.error("init_schema() appelé avec une connexion None")
        return False

    try:
        with conn.cursor() as cur:
            cur.execute(_CREATE_TABLE_SQL)
        conn.commit()
        _log.info("Table ssh_events vérifiée / créée avec succès")
        return True
    except DatabaseError as exc:
        _log.error("Erreur lors de la création du schéma : %s", exc)
        conn.rollback()
        return False


# ---------------------------------------------------------------------------
# Insertion
# ---------------------------------------------------------------------------

def insert_events(conn, events: list) -> int:
    """
    Insère une liste d'événements dans la table ssh_events.

    Paramètres
    ----------
    conn   : psycopg2.connection
    events : list[dict]  — clés attendues : toutes celles du schéma.

    Retour
    ------
    int : nombre de lignes effectivement insérées.

    Erreurs possibles loggées
    -------------------------
    - Connexion None                 → ERROR
    - Liste vide                     → WARNING
    - Erreur d'insertion par lot     → ERROR  (rollback)
    - Clé manquante dans un événement→ WARNING (événement ignoré)
    """
    if conn is None:
        _log.error("insert_events() appelé avec une connexion None")
        return 0

    if not events:
        _log.warning("insert_events() : liste d'événements vide")
        return 0

    _INSERT_SQL = """
        INSERT INTO ssh_events
            (month, day, time, host, service, event_type,
             ip, username, is_invalid_user, country, city, org)
        VALUES
            (%(month)s, %(day)s, %(time)s, %(host)s, %(service)s, %(event_type)s,
             %(ip)s, %(username)s, %(is_invalid_user)s, %(country)s, %(city)s, %(org)s)
    """

    inserted = 0
    skipped = 0

    try:
        with conn.cursor() as cur:
            for ev in events:
                # Vérification des clés obligatoires
                required = {"month", "day", "time", "host", "service",
                            "event_type", "ip", "username", "is_invalid_user"}
                missing = required - ev.keys()
                if missing:
                    _log.warning("Événement ignoré (clés manquantes: %s) : %s", missing, ev)
                    skipped += 1
                    continue

                # Valeurs par défaut pour les champs géo
                row = {
                    **ev,
                    "country": ev.get("country", "Unknown"),
                    "city":    ev.get("city", "Unknown"),
                    "org":     ev.get("org", "Unknown"),
                }

                try:
                    cur.execute(_INSERT_SQL, row)
                    inserted += 1
                except DatabaseError as exc:
                    _log.error("Erreur insertion événement %s : %s", ev.get("ip"), exc)
                    conn.rollback()
                    skipped += 1

        conn.commit()
        _log.info("Insertion terminée : %d insérés, %d ignorés", inserted, skipped)

    except (DatabaseError, InterfaceError) as exc:
        _log.error("Erreur lors du lot d'insertions : %s", exc)
        conn.rollback()

    return inserted


# ---------------------------------------------------------------------------
# Requêtes pour le dashboard
# ---------------------------------------------------------------------------

def query_failed_by_country(conn) -> list:
    """
    Retourne le nombre de tentatives échouées par pays.

    SELECT country, COUNT(*) as nb_failed
    FROM ssh_events
    WHERE event_type IN ('failed', 'invalid_user')
    GROUP BY country ORDER BY nb_failed DESC

    Retour
    ------
    list[tuple(country, nb_failed)]

    Erreurs possibles loggées
    -------------------------
    - Connexion None   → ERROR
    - Erreur SQL       → ERROR
    """
    if conn is None:
        _log.error("query_failed_by_country() : connexion None")
        return []
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT country, COUNT(*) AS nb_failed
                FROM ssh_events
                WHERE event_type IN ('failed', 'invalid_user')
                GROUP BY country
                ORDER BY nb_failed DESC
            """)
            rows = cur.fetchall()
            _log.info("Requête failed_by_country : %d pays", len(rows))
            return rows
    except DatabaseError as exc:
        _log.error("query_failed_by_country() erreur SQL : %s", exc)
        return []


def query_success_by_user(conn) -> list:
    """
    Retourne le nombre de connexions réussies par utilisateur.

    SELECT username, COUNT(*) as nb_success
    FROM ssh_events WHERE event_type = 'accepted'
    GROUP BY username ORDER BY nb_success DESC

    Retour
    ------
    list[tuple(username, nb_success)]

    Erreurs possibles loggées
    -------------------------
    - Connexion None   → ERROR
    - Erreur SQL       → ERROR
    """
    if conn is None:
        _log.error("query_success_by_user() : connexion None")
        return []
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT username, COUNT(*) AS nb_success
                FROM ssh_events
                WHERE event_type = 'accepted'
                GROUP BY username
                ORDER BY nb_success DESC
            """)
            rows = cur.fetchall()
            _log.info("Requête success_by_user : %d utilisateurs", len(rows))
            return rows
    except DatabaseError as exc:
        _log.error("query_success_by_user() erreur SQL : %s", exc)
        return []


def query_failed_invalid_users(conn) -> list:
    """
    Retourne les tentatives échouées avec des utilisateurs invalides.

    SELECT username, ip, country, COUNT(*) as nb_attempts
    FROM ssh_events
    WHERE is_invalid_user = TRUE
    GROUP BY username, ip, country ORDER BY nb_attempts DESC

    Retour
    ------
    list[tuple(username, ip, country, nb_attempts)]

    Erreurs possibles loggées
    -------------------------
    - Connexion None   → ERROR
    - Erreur SQL       → ERROR
    """
    if conn is None:
        _log.error("query_failed_invalid_users() : connexion None")
        return []
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT username, ip, country, COUNT(*) AS nb_attempts
                FROM ssh_events
                WHERE is_invalid_user = TRUE
                GROUP BY username, ip, country
                ORDER BY nb_attempts DESC
                LIMIT 50
            """)
            rows = cur.fetchall()
            _log.info("Requête failed_invalid_users : %d entrées", len(rows))
            return rows
    except DatabaseError as exc:
        _log.error("query_failed_invalid_users() erreur SQL : %s", exc)
        return []


# ---------------------------------------------------------------------------
# Test rapide si exécuté directement
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    conn = get_connection()
    if conn:
        init_schema(conn)
        print("Schéma initialisé.")
        conn.close()
