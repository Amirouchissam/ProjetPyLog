"""
Module : processing/extract_transforme.py
<<<<<<< HEAD
Rôle   : Parser les lignes brutes du journal auth.log (service sshd).
         Extrait pour chaque événement SSH pertinent :
           - horodatage (mois, jour, heure)
           - machine hôte et service
           - adresse IP source (IPv4 / IPv6)
           - nom d'utilisateur ciblé
           - type d'événement : 'failed', 'accepted', 'invalid_user'
           - statut utilisateur invalide (booléen)
         Retourne une liste de dictionnaires structurés et typés.
=======
Rôle   : Parser les lignes brutes du auth.log (service sshd).
         Extrait pour chaque événement SSH :
           - horodatage (mois, jour, heure)
           - nom de serveur / hôte
           - adresse IP source
           - nom d'utilisateur
           - type d'événement : 'failed', 'accepted', 'invalid_user'
>>>>>>> 5e2f890a8d6fdd0cda6fc28e33fe12c4b6318d8f
"""
import re
from typing import Optional, Any

from logger.app_logger import get_logger

_log = get_logger("processing.extract_transforme")

<<<<<<< HEAD
# ---------------------------------------------------------------------------
# Expressions régulières compilées pour optimiser les performances
# ---------------------------------------------------------------------------

# Format standard de ligne syslog Linux :
# "May 24 00:28:00 ns sshd[1351222]: Failed password..."
_PATTERN_LINE = re.compile(
    r"^(?P<month>[A-Za-z]{3})\s+(?P<day>\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2})"
    r"\s+(?P<host>\S+)\s+(?P<service>[A-Za-z0-9_\-]+)(?:\[\d+\])?:\s+(?P<message>.+)$"
)

# 1. Tentative échouée : "Failed password for [invalid user] <user> from <ip> port <port>"
_PATTERN_FAILED = re.compile(
    r"Failed password for(?P<invalid> invalid user)?\s+(?P<user>\S+)\s+from\s+(?P<ip>[a-fA-F0-9.:]+)\s+port\s+\d+"
)

# 2. Connexion acceptée : "Accepted password/publickey for <user> from <ip> port <port>"
_PATTERN_ACCEPTED = re.compile(
    r"Accepted\s+\S+\s+for\s+(?P<user>\S+)\s+from\s+(?P<ip>[a-fA-F0-9.:]+)\s+port\s+\d+"
)

# 3. Utilisateur inexistant : "Invalid user [<user>] from <ip> port <port>"
_PATTERN_INVALID = re.compile(
    r"Invalid user\s*(?P<user>\S*)\s+from\s+(?P<ip>[a-fA-F0-9.:]+)\s+port\s+\d+"
=======
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
>>>>>>> 5e2f890a8d6fdd0cda6fc28e33fe12c4b6318d8f
)


def _classify_message(message: str) -> Optional[dict[str, Any]]:
    """
<<<<<<< HEAD
    Analyse le message d'un événement sshd et le catégorise.

    Retour
    ------
    dict | None
        event_type      : 'failed' | 'accepted' | 'invalid_user'
        ip              : str (adresse IP source)
        username        : str (compte utilisateur ciblé)
        is_invalid_user : bool (True si l'utilisateur n'existe pas)
    """
    # 1. Vérification connexion réussie
    m_accepted = _PATTERN_ACCEPTED.search(message)
    if m_accepted:
        return {
            "event_type": "accepted",
            "ip": m_accepted.group("ip"),
            "username": m_accepted.group("user"),
            "is_invalid_user": False,
        }

    # 2. Vérification mot de passe échoué
    m_failed = _PATTERN_FAILED.search(message)
    if m_failed:
        is_invalid = bool(m_failed.group("invalid"))
        return {
            "event_type": "failed",
            "ip": m_failed.group("ip"),
            "username": m_failed.group("user"),
            "is_invalid_user": is_invalid,
        }

    # 3. Vérification tentative avec utilisateur inexistant
    m_invalid = _PATTERN_INVALID.search(message)
    if m_invalid:
        user = m_invalid.group("user").strip()
        return {
            "event_type": "invalid_user",
            "ip": m_invalid.group("ip"),
            "username": user if user else "(vide)",
=======
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
>>>>>>> 5e2f890a8d6fdd0cda6fc28e33fe12c4b6318d8f
            "is_invalid_user": True,
        }

    return None


def extract_from_row(row: str) -> Optional[dict[str, Any]]:
    """
<<<<<<< HEAD
    Parse une ligne brute de log et retourne un événement structuré.

    Paramètres
    ----------
    row : str
        Ligne issue du fichier auth.log.

    Retour
    ------
    dict | None
        Dictionnaire contenant les champs standardisés, ou None si la ligne
        ne concerne pas un événement SSH d'authentification.
=======
    Parse une ligne brute de log et retourne l'événement SSH structuré.
>>>>>>> 5e2f890a8d6fdd0cda6fc28e33fe12c4b6318d8f
    """
    if not row or not isinstance(row, str):
        return None

    cleaned_row = row.strip()
    if not cleaned_row:
        return None

    try:
<<<<<<< HEAD
        match = _PATTERN_LINE.match(cleaned_row)
        if not match:
=======
        match = re.search(pattern, row.strip())
        if not match:
            _log.debug("Ligne non reconnue : %.80s", row.strip())
>>>>>>> 5e2f890a8d6fdd0cda6fc28e33fe12c4b6318d8f
            return None

        gd = match.groupdict()

<<<<<<< HEAD
        # On se concentre exclusivement sur le service SSH (sshd)
=======
        # Filtrer uniquement les événements sshd
>>>>>>> 5e2f890a8d6fdd0cda6fc28e33fe12c4b6318d8f
        if gd.get("service", "").lower() != "sshd":
            return None

        event_details = _classify_message(gd["message"])
        if event_details is None:
            return None

        # Conversion sécurisée du jour en entier
        try:
            day_int = int(gd["day"])
        except (ValueError, TypeError):
            day_int = 1

        return {
            "month": gd["month"],
<<<<<<< HEAD
            "day": day_int,
=======
            "day": int(gd["day"]),
>>>>>>> 5e2f890a8d6fdd0cda6fc28e33fe12c4b6318d8f
            "time": gd["time"],
            "host": gd["host"],
            "service": gd["service"],
            **event_details,
        }

    except Exception as exc:
<<<<<<< HEAD
        _log.error("Erreur inattendue au parsing de la ligne : %s | Extrait : %.100s", exc, cleaned_row)
=======
        _log.error("Erreur parsing sur la ligne : %s | Ligne: %.100s", exc, row.strip())
>>>>>>> 5e2f890a8d6fdd0cda6fc28e33fe12c4b6318d8f
        return None


def extract_all(rows: list[str]) -> list[dict[str, Any]]:
    """
<<<<<<< HEAD
    Parse l'ensemble des lignes de logs fournies.

    Paramètres
    ----------
    rows : list[str]
        Liste des lignes brutes.

    Retour
    ------
    list[dict]
        Liste des événements SSH structurés et validés.
    """
    if not rows:
        _log.warning("extract_all() appelé avec une liste vide.")
        return []

    _log.info("Début du parsing de %d lignes brutes…", len(rows))

    extracted_events = []
    skipped = 0

    for row in rows:
        event = extract_from_row(row)
        if event is not None:
            extracted_events.append(event)
        else:
            skipped += 1

    _log.info(
        "Parsing achevé avec succès : %d événements SSH identifiés (%d lignes ignorées).",
        len(extracted_events), skipped
    )
    return extracted_events


# ---------------------------------------------------------------------------
# Test direct du module
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sample_lines = [
        "May 24 01:14:01 ns sshd[1351821]: Failed password for root from 45.148.10.147 port 8868 ssh2",
        "May 24 01:13:16 ns sshd[1351812]: Invalid user elena from 94.232.41.236 port 46854",
        "May 24 00:26:51 ns sshd[1351208]: Invalid user  from 45.156.87.204 port 35940",
        "May 25 10:00:00 ns sshd[9999]: Accepted password for alice from 192.168.1.1 port 22 ssh2",
    ]
    results = extract_all(sample_lines)
    for r in results:
        print(r)
=======
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
>>>>>>> 5e2f890a8d6fdd0cda6fc28e33fe12c4b6318d8f
