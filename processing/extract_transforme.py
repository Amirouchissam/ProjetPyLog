"""
Module : processing/extract_transforme.py
Rôle   : Parser les lignes brutes du auth.log (service sshd).
         Extrait pour chaque événement SSH :
           - horodatage (mois, jour, heure)
           - nom de serveur / hôte
           - adresse IP source
           - nom d'utilisateur
           - type d'événement : 'failed', 'accepted', 'invalid_user'
"""
import re
from typing import Optional, Any

from logger.app_logger import get_logger

_log = get_logger("processing.extract_transforme")

# Motif principal regex avec groupes nommés (conforme au cours)
pattern = re.compile(
    r"(?P<month>\w{3})\s+(?P<day>\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>\S+)\s+(?P<service>\w+)\[.+?:\s+(?P<message>.+)"
)

# Sous-motifs pour la classification des messages sshd
_FAILED_RE = re.compile(
    r"Failed password for(?P<invalid> invalid user)? (?P<user>\S+) from (?P<ip>[\d.]+) port \d+"
)
_ACCEPTED_RE = re.compile(
    r"Accepted \S+ for (?P<user>\S+) from (?P<ip>[\d.]+) port \d+"
)
_INVALID_RE = re.compile(
    r"Invalid user (?P<user>\S*) from (?P<ip>[\d.]+) port \d+"
)


def _classify_message(message: str) -> Optional[dict[str, Any]]:
    """
    Classe le message sshd en fonction de son type d'événement.
    """
    # 1. Connexion réussie
    m_ok = _ACCEPTED_RE.search(message)
    if m_ok:
        return {
            "event_type": "accepted",
            "ip": m_ok.group("ip"),
            "username": m_ok.group("user"),
            "is_invalid_user": False,
        }

    # 2. Échec de mot de passe
    m_fail = _FAILED_RE.search(message)
    if m_fail:
        return {
            "event_type": "failed",
            "ip": m_fail.group("ip"),
            "username": m_fail.group("user"),
            "is_invalid_user": bool(m_fail.group("invalid")),
        }

    # 3. Utilisateur inexistant
    m_inv = _INVALID_RE.search(message)
    if m_inv:
        return {
            "event_type": "invalid_user",
            "ip": m_inv.group("ip"),
            "username": m_inv.group("user") or "(vide)",
            "is_invalid_user": True,
        }

    return None


def extract_from_row(row: str) -> Optional[dict[str, Any]]:
    """
    Parse une ligne brute de log et retourne l'événement SSH structuré.
    """
    if not row or not row.strip():
        _log.debug("Ligne vide ignorée")
        return None

    try:
        match = re.search(pattern, row.strip())
        if not match:
            _log.debug("Ligne non reconnue : %.80s", row.strip())
            return None

        gd = match.groupdict()

        # Filtrer uniquement les événements sshd
        if gd.get("service", "").lower() != "sshd":
            return None

        event_details = _classify_message(gd["message"])
        if event_details is None:
            return None

        return {
            "month": gd["month"],
            "day": int(gd["day"]),
            "time": gd["time"],
            "host": gd["host"],
            "service": gd["service"],
            **event_details,
        }

    except Exception as exc:
        _log.error("Erreur parsing sur la ligne : %s | Ligne: %.100s", exc, row.strip())
        return None


def extract_all(rows: list[str]) -> list[dict[str, Any]]:
    """
    Extrait tous les événements SSH valides à partir de la liste de lignes brutes.
    """
    if not rows:
        _log.warning("Liste de lignes vide passée à extract_all()")
        return []

    _log.info("Début du parsing de %d lignes…", len(rows))
    events: list[dict[str, Any]] = []
    skipped = 0

    for row in rows:
        ev = extract_from_row(row)
        if ev:
            events.append(ev)
        else:
            skipped += 1

    _log.info("Parsing terminé : %d événements extraits, %d lignes ignorées", len(events), skipped)
    return events


if __name__ == "__main__":
    sample = "May 24 01:14:01 ns sshd[1351821]: Failed password for root from 45.148.10.147 port 8868 ssh2"
    res = extract_from_row(sample)
    print("Résultat extrait :", res)
