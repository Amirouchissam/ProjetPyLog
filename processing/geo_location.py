"""
Module : processing/geo_location.py
Rôle   : Résoudre la géolocalisation d'une adresse IP via l'API ipinfo.io.
         Retourne un dictionnaire avec le pays, la ville et les coordonnées.

Optimisations :
  - Cache mémoire par IP (évite les doublons)
  - Déduplication : n appels réseau max = nombre d'IPs uniques
  - Timeout global via socket.setdefaulttimeout()
  - Interruption propre sur KeyboardInterrupt
"""
import json
import socket
import urllib.request
import urllib.error
from typing import Optional, Any

from logger.app_logger import get_logger

_log = get_logger("processing.geo_location")

# URL de l'API publique (pas de token requis pour usage limité)
_IPINFO_URL = "https://ipinfo.io/{ip}/json"

# Timeout réseau global en secondes (SSL handshake compris)
_TIMEOUT = 4

# Cache mémoire : { ip -> dict }
_cache: dict = {}

# IPs privées / locales à ne pas géolocaliser
_PRIVATE_PREFIXES = (
    "127.", "10.", "192.168.",
    "172.16.", "172.17.", "172.18.", "172.19.", "172.20.",
    "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
    "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
    "::1",
)


def _is_private(ip: str) -> bool:
    """Retourne True si l'IP est privée/locale."""
    return any(ip.startswith(prefix) for prefix in _PRIVATE_PREFIXES)


def get_location(ip: str) -> dict:
    """
    Retourne les informations de géolocalisation pour une IP donnée.

    Paramètres
    ----------
    ip : str
        Adresse IPv4 à géolocaliser.

    Retour
    ------
    dict
        Clés garanties : 'ip', 'country', 'city', 'org'.
        Valeurs 'Unknown' si la géolocalisation a échoué.

    Erreurs possibles loggées
    -------------------------
    - IP privée / locale         → DEBUG  (retourne 'Local')
    - Réponse HTTP non 200       → WARNING
    - Erreur réseau / timeout    → ERROR
    - Réponse JSON invalide      → ERROR
    - Exception inattendue       → ERROR
    """
    _default = {"ip": ip, "country": "Unknown", "city": "Unknown", "org": "Unknown"}

    if not ip or not isinstance(ip, str):
        _log.error("IP invalide reçue : %r", ip)
        return _default

    # --- IPs privées ---
    if _is_private(ip):
        _log.debug("IP locale ignorée : %s", ip)
        return {"ip": ip, "country": "Local", "city": "Local", "org": "Local"}

    # --- Cache ---
    if ip in _cache:
        _log.debug("Cache hit pour %s", ip)
        return _cache[ip]

    # --- Requête HTTP (stdlib urllib) ---
    # socket.setdefaulttimeout garantit le respect du timeout même pendant
    # le SSL handshake (urllib timeout=x seul ne suffit pas sur Windows/py3.14)
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(_TIMEOUT)

    url = _IPINFO_URL.format(ip=ip)
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                _log.warning("ipinfo.io a répondu %d pour %s", response.status, ip)
                return _default

            raw = response.read().decode("utf-8")
            data = json.loads(raw)

    except urllib.error.HTTPError as exc:
        _log.error("Erreur HTTP pour %s : %s", ip, exc)
        return _default
    except urllib.error.URLError as exc:
        _log.error("Erreur réseau pour %s : %s", ip, exc)
        return _default
    except json.JSONDecodeError as exc:
        _log.error("JSON invalide pour %s : %s", ip, exc)
        return _default
    except (TimeoutError, socket.timeout, OSError) as exc:
        _log.error("Timeout/socket pour %s : %s", ip, exc)
        return _default
    except Exception as exc:
        _log.error("Erreur inattendue pour %s : %s", ip, exc)
        return _default
    finally:
        # Restaurer le timeout système d'origine
        socket.setdefaulttimeout(old_timeout)

    result = {
        "ip":      data.get("ip", ip),
        "country": data.get("country", "Unknown"),
        "city":    data.get("city", "Unknown"),
        "org":     data.get("org", "Unknown"),
    }

    _cache[ip] = result
    _log.debug("Géolocalisation réussie pour %s → %s / %s", ip, result["country"], result["city"])
    return result


def enrich_events(events: list) -> list:
    """
    Ajoute les informations de géolocalisation à chaque événement.

    Optimisation : on résout d'abord les IPs **uniques**, puis on propage
    le résultat à tous les événements qui partagent la même IP.
    Cela évite des milliers de requêtes HTTP redondantes.

    Paramètres
    ----------
    events : list[dict]
        Liste d'événements avec clé 'ip'.

    Retour
    ------
    list[dict]
        Mêmes événements enrichis des clés 'country', 'city', 'org'.

    Erreurs possibles loggées
    -------------------------
    - events vide / None           → WARNING
    - Événement sans clé 'ip'      → WARNING (ignoré)
    - KeyboardInterrupt utilisateur → WARNING (arrêt propre, retourne partiel)
    """
    if not events:
        _log.warning("Liste d'événements vide reçue dans enrich_events()")
        return []

    # --- Déduplication des IPs ---
    unique_ips = {ev.get("ip") for ev in events if ev.get("ip")}
    unique_ips.discard(None)
    _log.info(
        "Géolocalisation : %d événements → %d IPs uniques à résoudre",
        len(events), len(unique_ips)
    )

    # --- Résolution IP par IP avec gestion d'interruption ---
    geo_map: dict = {}
    done = 0
    try:
        for ip in unique_ips:
            geo_map[ip] = get_location(ip)
            done += 1
            if done % 50 == 0:
                _log.info("  → %d / %d IPs résolues…", done, len(unique_ips))
    except KeyboardInterrupt:
        _log.warning(
            "Géolocalisation interrompue par l'utilisateur après %d / %d IPs. "
            "Les IPs non résolues recevront 'Unknown'.",
            done, len(unique_ips)
        )

    # --- Enrichissement de tous les événements ---
    enriched = []
    errors = 0
    for ev in events:
        ip = ev.get("ip")
        if not ip:
            _log.warning("Événement sans clé 'ip' ignoré : %s", ev)
            errors += 1
            continue

        location = geo_map.get(ip, {"ip": ip, "country": "Unknown", "city": "Unknown", "org": "Unknown"})
        enriched.append({**ev, **location})

    _log.info(
        "Géolocalisation terminée : %d enrichis, %d erreurs",
        len(enriched), errors
    )
    return enriched


# ---------------------------------------------------------------------------
# Test rapide si exécuté directement
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_ips = ["45.148.10.152", "94.232.41.236", "127.0.0.1"]
    for ip in test_ips:
        print(get_location(ip))
