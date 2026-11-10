"""
Module : processing/geo_location.py
<<<<<<< HEAD
Rôle   : Résoudre la géolocalisation d'une adresse IP via l'API ipinfo.io.
         Fournit le pays, la ville et l'organisation (FAI).

Performances et fiabilité :
  - Cache persistant sur disque (data/geo_cache.json) pour éviter les requêtes répétitives.
  - Mode offline_only : enrichissement instantané à partir du cache local sans accès Internet.
  - Déduplication préalable : une seule requête HTTP par adresse IP unique.
  - Timeout strict via socket.setdefaulttimeout() (y compris pendant le handshake TLS).
  - Gestion gracieuse du KeyboardInterrupt avec sauvegarde de l'état partiel.
"""
import json
import socket
import urllib.error
import urllib.request
from pathlib import Path
=======
Rôle   : Résoudre la géolocalisation des adresses IP via requests (ipinfo.io)
         conforme au code initial du cours.
         Inclut un cache mémoire, la déduplication et un repli local (geoip.csv)
         pour éviter les erreurs de quota ou de connexion réseau.
"""
import os
import re
import sys
from typing import Optional, Any
>>>>>>> 5e2f890a8d6fdd0cda6fc28e33fe12c4b6318d8f

if "." not in sys.path:
    sys.path.insert(0, ".")

import requests
from logger.app_logger import get_logger

_log = get_logger("processing.geo_location")

<<<<<<< HEAD
# ------------------------------------------------------------------
# Paramètres de configuration
# ------------------------------------------------------------------
_IPINFO_URL = "https://ipinfo.io/{ip}/json"
_TIMEOUT_SECONDS = 2

# Fichier de cache persistant (dans le répertoire data/)
_CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "geo_cache.json"

# Cache mémoire
_cache: dict = {}
_cache_loaded: bool = False

# Préfixes d'adresses privées et locales (RFC 1918 + loopback)
_PRIVATE_PREFIXES = (
    "127.", "10.", "192.168.",
    "172.16.", "172.17.", "172.18.", "172.19.", "172.20.",
    "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
    "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
    "::1", "0.0.0.0"
)


# ------------------------------------------------------------------
# Gestion du cache JSON
# ------------------------------------------------------------------

def _load_cache() -> None:
    """Charge le cache JSON depuis le disque s'il existe."""
    global _cache, _cache_loaded
    if _cache_loaded:
        return

    if _CACHE_FILE.exists():
        try:
            with open(_CACHE_FILE, mode="r", encoding="utf-8") as fh:
                loaded_data = json.load(fh)
                if isinstance(loaded_data, dict):
                    _cache = loaded_data
                    _log.info("Cache géo chargé : %d IPs disponibles (%s)", len(_cache), _CACHE_FILE.name)
                else:
                    _log.warning("Format de cache inattendu, initialisation d'un nouveau cache.")
                    _cache = {}
        except (json.JSONDecodeError, OSError) as exc:
            _log.warning("Impossible de lire le cache géo existant (%s) : %s", _CACHE_FILE.name, exc)
            _cache = {}
    else:
        _cache = {}

    _cache_loaded = True


def _save_cache() -> None:
    """Sauvegarde le cache mémoire sur disque de manière atomique."""
    if not _cache:
        return

    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_CACHE_FILE, mode="w", encoding="utf-8") as fh:
            json.dump(_cache, fh, ensure_ascii=False, indent=2)
        _log.info("Cache géo sauvegardé : %d adresses IP enregistrées.", len(_cache))
    except OSError as exc:
        _log.error("Échec de la sauvegarde du cache géo : %s", exc)


def _is_private_ip(ip: str) -> bool:
    """Indique si l'adresse IP est privée ou de test local."""
    return any(ip.startswith(prefix) for prefix in _PRIVATE_PREFIXES)


# ------------------------------------------------------------------
# Résolution d'adresse IP
# ------------------------------------------------------------------

def get_location(ip: str, allow_network: bool = True) -> dict:
    """
    Retourne la géolocalisation d'une adresse IP donnée.

    Paramètres
    ----------
    ip : str
        Adresse IP à géolocaliser.
    allow_network : bool, optional
        Si False, ne fait aucun appel réseau et retourne le cache ou 'Unknown'.

    Retour
    ------
    dict
        Clés garanties : ip, country, city, org.
=======
URL_IPINFO: str = "https://ipinfo.io"
GEOIP_CSV: str = os.path.join("data", "geoip.csv")

# Cache mémoire pour éviter les requêtes HTTP répétitives
_cache: dict[str, dict[str, str]] = {}

# Table locale de secours chargée depuis data/geoip.csv
_local_table: list[tuple[list[int], int, str]] = []
_CIDR_PATTERN = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/(\d{1,2})$")


def _load_local_geoip() -> None:
    """Charge la table locale de secours en cas d'absence d'Internet ou de quota dépassé."""
    global _local_table
    if _local_table or not os.path.exists(GEOIP_CSV):
        return
    try:
        with open(GEOIP_CSV, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(",")
                if len(parts) >= 2:
                    m = _CIDR_PATTERN.match(parts[0].strip())
                    if m:
                        octets = [int(g) for g in m.groups()[:4]]
                        mask = int(m.group(5))
                        _local_table.append((octets, mask, parts[1].strip()))
    except OSError as exc:
        _log.error("Erreur lecture table locale geoip.csv : %s", exc)


def _resolve_local(ip: str) -> str:
    """Résolution hors-ligne via la table locale."""
    _load_local_geoip()
    parts = ip.split(".")
    if len(parts) != 4:
        return "Unknown"
    try:
        nums = [int(p) for p in parts]
        ip_int = (nums[0] << 24) | (nums[1] << 16) | (nums[2] << 8) | nums[3]
    except ValueError:
        return "Unknown"

    best_match = "Unknown"
    best_mask = -1
    for octets, mask, country in _local_table:
        net_int = (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]
        mask_val = ((1 << 32) - 1) ^ ((1 << (32 - mask)) - 1) if mask > 0 else 0
        if (ip_int & mask_val) == (net_int & mask_val) and mask > best_mask:
            best_mask = mask
            best_match = country
    return best_match


def get_location(ip: str) -> dict[str, str]:
    """
    Fonction demandée par le professeur : interroge ipinfo.io via requests.
    Optimisée avec vérification locale préalable pour la rapidité.
>>>>>>> 5e2f890a8d6fdd0cda6fc28e33fe12c4b6318d8f
    """
    default_res = {"ip": ip, "country": "Unknown", "city": "Unknown", "org": "Unknown"}

    if not ip or not isinstance(ip, str):
        return default_res

<<<<<<< HEAD
    clean_ip = ip.strip()

    # Détection IP privée
    if _is_private_ip(clean_ip):
        return {"ip": clean_ip, "country": "Local", "city": "Local", "org": "Local"}

    _load_cache()

    # Vérification dans le cache
    if clean_ip in _cache:
        return _cache[clean_ip]

    # Si le réseau est interdit (mode offline)
    if not allow_network:
        return default_res

    # Appel HTTP externe (ipinfo.io) avec timeout strict
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(_TIMEOUT_SECONDS)
    url = _IPINFO_URL.format(ip=clean_ip)

    try:
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (SecurityLogAnalyzer/1.0)"
            }
        )
        with urllib.request.urlopen(req) as resp:
            if resp.status == 200:
                body = resp.read().decode("utf-8")
                data = json.loads(body)
                result = {
                    "ip": clean_ip,
                    "country": data.get("country", "Unknown") or "Unknown",
                    "city": data.get("city", "Unknown") or "Unknown",
                    "org": data.get("org", "Unknown") or "Unknown",
                }
                _cache[clean_ip] = result
                return result
            else:
                _log.warning("ipinfo.io code HTTP %d pour %s", resp.status, clean_ip)

    except urllib.error.HTTPError as exc:
        _log.debug("HTTP %d pour %s : %s", exc.code, clean_ip, exc.reason)
    except urllib.error.URLError as exc:
        _log.debug("Erreur réseau pour %s : %s", clean_ip, exc.reason)
    except (socket.timeout, TimeoutError, OSError) as exc:
        _log.debug("Timeout réseau pour %s : %s", clean_ip, exc)
    except Exception as exc:
        _log.error("Erreur inattendue pour %s : %s", clean_ip, exc)
    finally:
        socket.setdefaulttimeout(old_timeout)

    return default_res


def enrich_events(events: list, offline_only: bool = False) -> list:
    """
    Enrichit chaque événement SSH avec ses informations géographiques.

    Paramètres
    ----------
    events : list[dict]
        Liste d'événements contenant la clé 'ip'.
    offline_only : bool, optional
        Si True, utilise uniquement le cache local sans faire d'appels réseau.

    Retour
    ------
    list[dict]
        Événements enrichis avec 'country', 'city', 'org'.
    """
    if not events:
        return []

    _load_cache()

    # Identifier toutes les IPs uniques
    unique_ips = {ev.get("ip") for ev in events if ev.get("ip")}
    unique_ips.discard(None)

    cached_count = sum(1 for ip in unique_ips if ip in _cache or _is_private_ip(ip))
    missing_count = len(unique_ips) - cached_count

    _log.info(
        "Géolocalisation : %d événements, %d IPs uniques (%d en cache, %d non résolues).",
        len(events), len(unique_ips), cached_count, missing_count
    )

    if offline_only:
        _log.info("Mode hors ligne actif : aucun appel réseau externe.")
    elif missing_count > 0:
        _log.info("Résolution réseau des nouvelles adresses IP (timeout %ds)…", _TIMEOUT_SECONDS)
        resolved = 0
        try:
            for ip in unique_ips:
                if ip not in _cache and not _is_private_ip(ip):
                    get_location(ip, allow_network=True)
                    resolved += 1
                    if resolved % 50 == 0:
                        _log.info("  → %d / %d adresses résolues…", resolved, missing_count)
        except KeyboardInterrupt:
            _log.warning("Interruption utilisateur lors de la géolocalisation (%d résolues).", resolved)
        finally:
            _save_cache()

    # Propagation rapide du dictionnaire géographique à tous les événements
    enriched_list = []
    for ev in events:
        ip = ev.get("ip")
        if not ip:
            enriched_list.append({**ev, "country": "Unknown", "city": "Unknown", "org": "Unknown"})
            continue

        loc = _cache.get(ip) or (
            {"ip": ip, "country": "Local", "city": "Local", "org": "Local"}
            if _is_private_ip(ip) else
            {"ip": ip, "country": "Unknown", "city": "Unknown", "org": "Unknown"}
        )
        enriched_list.append({**ev, **loc})

    _log.info("Enrichissement géographique terminé pour %d événements.", len(enriched_list))
    return enriched_list


# ---------------------------------------------------------------------------
# Test direct du module
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_ips = ["45.148.10.152", "127.0.0.1", "192.168.1.50"]
    for ip in test_ips:
        print(f"{ip} -> {get_location(ip)}")
=======
    # 1. Vérification du cache mémoire
    if ip in _cache:
        return _cache[ip]

    # 2. Vérification locale rapide (sans latence réseau)
    local_country = _resolve_local(ip)
    if local_country != "Unknown":
        info = {"ip": ip, "country": local_country, "city": local_country, "org": local_country}
        _cache[ip] = info
        return info

    # 3. Requête HTTP via requests (code du cours)
    try:
        response = requests.get(f"{URL_IPINFO}/{ip}/json", timeout=1.5)
        if response.status_code == 200:
            data = response.json()
            info = {
                "ip": ip,
                "country": data.get("country", "Unknown"),
                "city": data.get("city", "Unknown"),
                "org": data.get("org", "Unknown"),
            }
            _cache[ip] = info
            return info
        else:
            _log.warning("ipinfo.io code HTTP %d pour l'IP %s", response.status_code, ip)

    except requests.exceptions.Timeout:
        _log.debug("Timeout réseau ipinfo.io pour %s", ip)
    except requests.exceptions.RequestException as exc:
        _log.error("Erreur réseau requests pour %s : %s", ip, exc)
    except Exception as exc:
        _log.error("Erreur inattendue pour %s : %s", ip, exc)

    _cache[ip] = default_res
    return default_res


def enrich_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Enrichit tous les événements SSH avec leur géolocalisation.
    Optimisé : résout les IPs uniques pour minimiser les appels réseau.
    """
    if not events:
        _log.warning("enrich_events appelé avec une liste vide")
        return []

    unique_ips = {ev.get("ip") for ev in events if ev.get("ip")}
    unique_ips.discard(None)
    _log.info("Géolocalisation : %d événements -> %d IPs uniques", len(events), len(unique_ips))

    geo_map: dict[str, dict[str, str]] = {}
    done = 0
    for ip in unique_ips:
        geo_map[ip] = get_location(ip)
        done += 1
        if done % 100 == 0:
            _log.info("Géolocalisation en cours : %d / %d", done, len(unique_ips))

    enriched: list[dict[str, Any]] = []
    for ev in events:
        ip = ev.get("ip", "")
        location = geo_map.get(ip, {"country": "Unknown", "city": "Unknown", "org": "Unknown"})
        enriched.append({
            **ev,
            "country": location.get("country", "Unknown"),
            "city": location.get("city", "Unknown"),
            "org": location.get("org", "Unknown"),
        })

    _log.info("✓ Géolocalisation terminée pour %d événements", len(enriched))
    return enriched


if __name__ == "__main__":
    test_ip = "94.232.41.236"
    print(f"Test get_location('{test_ip}') :", get_location(test_ip))
>>>>>>> 5e2f890a8d6fdd0cda6fc28e33fe12c4b6318d8f
