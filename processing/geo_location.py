"""
Module : processing/geo_location.py
Rôle   : Résoudre la géolocalisation des adresses IP via requests (ipinfo.io)
         conforme au code initial du cours.
         Inclut un cache mémoire, la déduplication et un repli local (geoip.csv)
         pour éviter les erreurs de quota ou de connexion réseau.
"""
import os
import re
import sys
from typing import Optional, Any

if "." not in sys.path:
    sys.path.insert(0, ".")

import requests
from logger.app_logger import get_logger

_log = get_logger("processing.geo_location")

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
    """
    default_res = {"ip": ip, "country": "Unknown", "city": "Unknown", "org": "Unknown"}

    if not ip or not isinstance(ip, str):
        return default_res

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
