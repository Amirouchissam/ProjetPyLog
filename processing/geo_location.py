"""
Module : processing/geo_location.py
Rôle   : Résoudre la géolocalisation d'une adresse IP via l'API ipinfo.io.

Optimisations :
  - Cache PERSISTANT JSON (data/geo_cache.json) :
      première exécution = appels réseau,
      toutes les suivantes = lecture fichier (quasi-instantané).
  - Cache mémoire : évite de relire le JSON à chaque IP.
  - Timeout global via socket.setdefaulttimeout() (SSL handshake compris).
  - IPs privées ignorées immédiatement.
  - Interruption propre sur KeyboardInterrupt.
"""
import json
import socket
import urllib.request
import urllib.error
from pathlib import Path

from logger.app_logger import get_logger

_log = get_logger("processing.geo_location")

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
_IPINFO_URL     = "https://ipinfo.io/{ip}/json"
_TIMEOUT        = 2          # secondes (SSL handshake compris)

# Cache persistant sur disque
_CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "geo_cache.json"

# Cache mémoire (chargé une seule fois depuis le fichier)
_cache: dict = {}
_cache_loaded: bool = False

_PRIVATE_PREFIXES = (
    "127.", "10.", "192.168.",
    "172.16.", "172.17.", "172.18.", "172.19.", "172.20.",
    "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
    "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
    "::1",
)


# ------------------------------------------------------------------
# Cache persistant
# ------------------------------------------------------------------

def _load_cache() -> None:
    """
    Charge le cache JSON depuis le disque dans _cache (mémoire).
    Appelé une seule fois au premier accès.

    Erreurs possibles loggées
    -------------------------
    - Fichier JSON corrompu → WARNING (cache ignoré, repart de zéro)
    - Erreur lecture OS     → WARNING
    """
    global _cache, _cache_loaded
    if _cache_loaded:
        return

    if _CACHE_FILE.exists():
        try:
            with open(_CACHE_FILE, encoding="utf-8") as fh:
                _cache = json.load(fh)
            _log.info("Cache géo chargé : %d IPs connues (%s)", len(_cache), _CACHE_FILE.name)
        except json.JSONDecodeError as exc:
            _log.warning("Cache JSON corrompu, ignoré : %s", exc)
            _cache = {}
        except OSError as exc:
            _log.warning("Impossible de lire le cache géo : %s", exc)
            _cache = {}
    else:
        _log.info("Pas de cache géo existant, il sera créé après la résolution.")
        _cache = {}

    _cache_loaded = True


def _save_cache() -> None:
    """
    Sauvegarde le cache mémoire vers le fichier JSON.

    Erreurs possibles loggées
    -------------------------
    - Erreur écriture OS → ERROR
    """
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_CACHE_FILE, "w", encoding="utf-8") as fh:
            json.dump(_cache, fh, ensure_ascii=False, indent=2)
        _log.info("Cache géo sauvegardé : %d IPs → %s", len(_cache), _CACHE_FILE.name)
    except OSError as exc:
        _log.error("Impossible de sauvegarder le cache géo : %s", exc)


# ------------------------------------------------------------------
# Géolocalisation
# ------------------------------------------------------------------

def _is_private(ip: str) -> bool:
    return any(ip.startswith(p) for p in _PRIVATE_PREFIXES)


def get_location(ip: str) -> dict:
    """
    Retourne les infos de géolocalisation pour une IP.
    Utilise le cache mémoire/disque avant tout appel réseau.

    Paramètres
    ----------
    ip : str

    Retour
    ------
    dict  clés : ip, country, city, org

    Erreurs possibles loggées
    -------------------------
    - IP invalide          → ERROR
    - IP privée            → DEBUG
    - Erreur HTTP          → ERROR
    - Erreur réseau/timeout→ ERROR
    - JSON invalide        → ERROR
    - Exception inattendue → ERROR
    """
    _default = {"ip": ip, "country": "Unknown", "city": "Unknown", "org": "Unknown"}

    if not ip or not isinstance(ip, str):
        _log.error("IP invalide : %r", ip)
        return _default

    if _is_private(ip):
        _log.debug("IP privée ignorée : %s", ip)
        return {"ip": ip, "country": "Local", "city": "Local", "org": "Local"}

    # Charger le cache une seule fois
    _load_cache()

    # Cache hit ?
    if ip in _cache:
        _log.debug("Cache hit : %s", ip)
        return _cache[ip]

    # Appel réseau
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(_TIMEOUT)
    url = _IPINFO_URL.format(ip=ip)

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                _log.warning("ipinfo.io → %d pour %s", response.status, ip)
                return _default
            data = json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as exc:
        _log.error("HTTP %s pour %s : %s", exc.code, ip, exc.reason)
        return _default
    except urllib.error.URLError as exc:
        _log.error("Réseau pour %s : %s", ip, exc.reason)
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
        socket.setdefaulttimeout(old_timeout)

    result = {
        "ip":      data.get("ip", ip),
        "country": data.get("country", "Unknown"),
        "city":    data.get("city", "Unknown"),
        "org":     data.get("org", "Unknown"),
    }
    _cache[ip] = result
    _log.debug("Résolu : %s → %s / %s", ip, result["country"], result["city"])
    return result


def enrich_events(events: list) -> list:
    """
    Enrichit chaque événement avec sa géolocalisation.

    Algorithme
    ----------
    1. Charger le cache JSON existant.
    2. Identifier les IPs uniques NON encore en cache (nouvelles IPs seulement).
    3. Faire les appels réseau uniquement pour ces nouvelles IPs.
    4. Sauvegarder le cache mis à jour.
    5. Propager le résultat à tous les événements.

    Paramètres
    ----------
    events : list[dict]  — doit contenir la clé 'ip'

    Retour
    ------
    list[dict]  enrichi des clés country, city, org

    Erreurs possibles loggées
    -------------------------
    - events vide              → WARNING
    - Événement sans 'ip'      → WARNING
    - KeyboardInterrupt        → WARNING (arrêt propre)
    """
    if not events:
        _log.warning("Liste vide reçue dans enrich_events()")
        return []

    # Charger le cache
    _load_cache()

    # IPs uniques totales
    all_ips    = {ev.get("ip") for ev in events if ev.get("ip")}
    # Nouvelles IPs (pas encore dans le cache)
    new_ips    = {ip for ip in all_ips if ip not in _cache and not _is_private(ip)}

    _log.info(
        "%d événements | %d IPs uniques | %d dans le cache | %d à résoudre via réseau",
        len(events), len(all_ips), len(all_ips) - len(new_ips), len(new_ips)
    )

    if new_ips:
        done = 0
        try:
            for ip in new_ips:
                get_location(ip)   # met à jour _cache en interne
                done += 1
                if done % 50 == 0:
                    _log.info("  → %d / %d nouvelles IPs résolues…", done, len(new_ips))
        except KeyboardInterrupt:
            _log.warning(
                "Interrompu après %d / %d IPs. Les IPs non résolues → 'Unknown'.",
                done, len(new_ips)
            )
        finally:
            # Toujours sauvegarder le cache même si interrompu
            _save_cache()
    else:
        _log.info("Toutes les IPs sont dans le cache — aucun appel réseau nécessaire ✓")

    # Enrichissement de chaque événement depuis le cache
    enriched = []
    errors   = 0
    for ev in events:
        ip = ev.get("ip")
        if not ip:
            _log.warning("Événement sans 'ip' ignoré : %s", ev)
            errors += 1
            continue
        loc = _cache.get(ip, {"ip": ip, "country": "Unknown", "city": "Unknown", "org": "Unknown"})
        enriched.append({**ev, **loc})

    _log.info("Enrichissement terminé : %d enrichis, %d erreurs", len(enriched), errors)
    return enriched


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    for ip in ["45.148.10.152", "94.232.41.236", "127.0.0.1"]:
        print(get_location(ip))
