"""
Module : processing/geo_location.py
Rôle   : Résoudre le pays d'origine d'une adresse IP à partir d'un fichier CSV local (data/geoip.csv).
         Conforme au cours : utilise uniquement 'open' et 're' (aucun package externe ni requête HTTP).
"""
import os
import re
import sys
from typing import Optional

# Assurer l'accès aux modules parents lors d'une exécution directe
if "." not in sys.path:
    sys.path.insert(0, ".")

from logger.app_logger import get_logger

_log = get_logger("processing.geo_location")

# Fichier GeoIP local
GEOIP_FILE: str = os.path.join("data", "geoip.csv")

# Regex pour valider un CIDR : ex. 192.168.0.0/16
_CIDR_PATTERN = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/(\d{1,2})$")

# Cache mémoire pour éviter de recalculer la même IP
_cache: dict[str, str] = {}

# Table locale chargée en mémoire : [(prefix_parts, mask, country), ...]
_geo_table: list[tuple[list[int], int, str]] = []


def _ip_to_int(ip_str: str) -> Optional[int]:
    """Convertit une chaîne IPv4 en entier 32 bits."""
    parts = ip_str.split(".")
    if len(parts) != 4:
        return None
    try:
        nums = [int(p) for p in parts]
        if any(n < 0 or n > 255 for n in nums):
            return None
        return (nums[0] << 24) | (nums[1] << 16) | (nums[2] << 8) | nums[3]
    except ValueError:
        return None


def load_geoip_table(filepath: str = GEOIP_FILE) -> int:
    """
    Charge la table GeoIP depuis un fichier CSV (format: cidr,pays).
    Utilise open() et re.compile() selon les notions du cours.
    """
    global _geo_table
    _geo_table = []

    if not os.path.exists(filepath):
        _log.warning("Fichier GeoIP introuvable : %s (pays par défaut : 'Unknown')", filepath)
        return 0

    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, start=1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split(",")
                if len(parts) < 2:
                    continue

                cidr_str = parts[0].strip()
                country = parts[1].strip()

                m = _CIDR_PATTERN.match(cidr_str)
                if not m:
                    _log.debug("Ligne %d ignorée (format CIDR invalide) : %s", line_no, line)
                    continue

                octets = [int(g) for g in m.groups()[:4]]
                mask_len = int(m.group(5))

                if any(o > 255 for o in octets) or mask_len > 32 or mask_len < 0:
                    continue

                _geo_table.append((octets, mask_len, country))

        _log.info("GeoIP : %d règles chargées depuis %s", len(_geo_table), filepath)
        return len(_geo_table)

    except OSError as exc:
        _log.error("Erreur lecture fichier GeoIP '%s' : %s", filepath, exc)
        return 0


def get_country(ip: str) -> str:
    """
    Retourne le pays associé à une adresse IP par correspondance avec la table GeoIP.
    """
    if not ip or not isinstance(ip, str):
        return "Unknown"

    if ip in _cache:
        return _cache[ip]

    ip_int = _ip_to_int(ip)
    if ip_int is None:
        _cache[ip] = "Unknown"
        return "Unknown"

    # Recherche de la règle la plus précise (masque le plus grand)
    best_match_country = "Unknown"
    best_mask = -1

    for octets, mask_len, country in _geo_table:
        net_int = (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]
        mask_val = ((1 << 32) - 1) ^ ((1 << (32 - mask_len)) - 1) if mask_len > 0 else 0

        if (ip_int & mask_val) == (net_int & mask_val):
            if mask_len > best_mask:
                best_mask = mask_len
                best_match_country = country

    _cache[ip] = best_match_country
    return best_match_country


def enrich_events(events: list[dict]) -> list[dict]:
    """
    Enrichit chaque événement de la liste avec son pays d'origine.
    """
    if not events:
        _log.warning("enrich_events appelé avec une liste vide")
        return []

    # S'assurer que la table est chargée
    if not _geo_table:
        load_geoip_table(GEOIP_FILE)

    enriched: list[dict] = []
    for ev in events:
        ip = ev.get("ip", "")
        country = get_country(ip)
        enriched.append({
            **ev,
            "country": country,
            "city": country,
            "org": country,
        })

    _log.info("Géolocalisation locale terminée pour %d événements", len(enriched))
    return enriched


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    load_geoip_table()
    test_ips = ["45.148.10.141", "94.232.41.236", "192.168.1.1", "127.0.0.1"]
    for test_ip in test_ips:
        print(f"{test_ip} -> {get_country(test_ip)}")
