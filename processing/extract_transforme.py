"""
Module : processing/extract_transforme.py
Rôle   : Parser les lignes brutes du auth.log Linux (service sshd).
         Extrait pour chaque événement SSH :
           - date/heure
           - adresse IP source
           - nom d'utilisateur
           - type d'événement : 'failed', 'accepted', 'invalid_user'
         Retourne une liste de dictionnaires structurés.
"""
import re
from typing import Optional, Any

from logger.app_logger import get_logger

_log = get_logger("processing.extract_transforme")

# ---------------------------------------------------------------------------
# Expressions régulières
# ---------------------------------------------------------------------------

# Ligne générique du auth.log
_PATTERN_LINE = re.compile(
    r"(?P<month>\w{3})\s+(?P<day>\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2})"
    r"\s+(?P<host>\S+)\s+(?P<service>\w+)\[.+?:\s+(?P<message>.+)"
)

# "Failed password for [invalid user] <user> from <ip> port <port>"
_PATTERN_FAILED = re.compile(
    r"Failed password for(?P<invalid> invalid user)? (?P<user>\S+) from (?P<ip>[\d.]+) port \d+"
)

# "Accepted password/publickey for <user> from <ip> port <port>"
_PATTERN_ACCEPTED = re.compile(
    r"Accepted \S+ for (?P<user>\S+) from (?P<ip>[\d.]+) port \d+"
)

# "Invalid user [<user>] from <ip> port <port>"
_PATTERN_INVALID = re.compile(
    r"Invalid user (?P<user>\S*) from (?P<ip>[\d.]+) port \d+"
)


def _classify_message(message: str) -> dict | None:
    """
    Tente de classer un message sshd et retourne un dict structuré ou None.

    Champs retournés
    ----------------
    event_type : 'failed' | 'accepted' | 'invalid_user'
    ip         : adresse IP source
    username   : nom d'utilisateur (peut être vide pour 'invalid_user')
    is_invalid_user : True si l'utilisateur n'existe pas sur le système
    """
    # --- Connexion réussie ---
    m = _PATTERN_ACCEPTED.search(message)
    if m:
        return {
            "event_type": "accepted",
            "ip": m.group("ip"),
            "username": m.group("user"),
            "is_invalid_user": False,
        }

    # --- Mot de passe échoué ---
    m = _PATTERN_FAILED.search(message)
    if m:
        return {
            "event_type": "failed",
            "ip": m.group("ip"),
            "username": m.group("user"),
            "is_invalid_user": bool(m.group("invalid")),
        }

    # --- Utilisateur inconnu (sans tentative de mot de passe encore) ---
    m = _PATTERN_INVALID.search(message)
    if m:
        return {
            "event_type": "invalid_user",
            "ip": m.group("ip"),
            "username": m.group("user") or "(vide)",
            "is_invalid_user": True,
        }

    return None


def extract_from_row(row: str) -> dict | None:
    """
    Parse une ligne brute du auth.log et retourne un dict structuré.

    Paramètres
    ----------
    row : str
        Ligne brute telle que lue depuis le fichier log.

    Retour
    ------
    dict | None
        Dictionnaire avec les clés :
          month, day, time, host, service, event_type, ip, username,
          is_invalid_user
        Retourne None si la ligne ne correspond pas à un événement sshd pertinent.

    Erreurs possibles loggées
    -------------------------
    - Ligne vide / None         → DEBUG
    - Ligne non reconnue        → DEBUG
    - Exception interne         → ERROR
    """
    if not row or not row.strip():
        _log.debug("Ligne vide ignorée")
        return None

    try:
        m = _PATTERN_LINE.match(row.strip())
        if not m:
            _log.debug("Ligne non reconnue (format inattendu) : %.80s", row.strip())
            return None

        gd = m.groupdict()

        # On ne traite que sshd
        if gd.get("service", "").lower() != "sshd":
            return None

        event = _classify_message(gd["message"])
        if event is None:
            return None

        return {
            "month": gd["month"],
            "day": gd["day"],
            "time": gd["time"],
            "host": gd["host"],
            "service": gd["service"],
            **event,
        }

    except Exception as exc:
        _log.error("Erreur lors du parsing de la ligne : %s | Ligne : %.120s", exc, row.strip())
        return None


def extract_all(rows: list) -> list:
    """
    Applique extract_from_row() sur chaque ligne et retourne
    la liste des événements valides (None exclus).

    Paramètres
    ----------
    rows : list[str]
        Lignes brutes issues du module ingestion.

    Retour
    ------
    list[dict]
        Liste des événements SSH structurés.

    Erreurs possibles loggées
    -------------------------
    - rows vide / None           → WARNING
    - Taux de lignes non parsées → INFO
    """
    if not rows:
        _log.warning("Liste de lignes vide reçue dans extract_all()")
        return []

    _log.info("Début du parsing : %d lignes à traiter", len(rows))

    results = []
    skipped = 0
    for row in rows:
        event = extract_from_row(row)
        if event:
            results.append(event)
        else:
            skipped += 1

    _log.info(
        "Parsing terminé : %d événements extraits, %d lignes ignorées",
        len(results), skipped
    )
    return results


# ---------------------------------------------------------------------------
# Test rapide si exécuté directement
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sample = [
        "May 24 01:14:01 ns sshd[1351821]: Failed password for root from 45.148.10.147 port 8868 ssh2",
        "May 24 01:13:16 ns sshd[1351812]: Invalid user elena from 94.232.41.236 port 46854",
        "May 25 10:00:00 ns sshd[9999]: Accepted password for alice from 192.168.1.1 port 22 ssh2",
    ]
    for ev in extract_all(sample):
        print(ev)
