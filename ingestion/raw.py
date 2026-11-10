"""
Module : ingestion/raw.py
Rôle   : Lire tous les fichiers de logs du répertoire data/.
         Prend en charge les fichiers texte bruts (.log, .1, .2 …)
         et les fichiers compressés (.gz).
         Retourne une liste de lignes (str) prêtes à être parsées.
"""
import gzip
import os
from pathlib import Path

from logger.app_logger import get_logger

_log = get_logger("ingestion.raw")


def to_rows(path: str) -> list[str]:
    """
    Lit tous les fichiers du répertoire 'path' et retourne leurs lignes.

    Paramètres
    ----------
    path : str
        Chemin vers le répertoire contenant les fichiers de logs.

    Retour
    ------
    list[str]
        Liste de toutes les lignes lues (strip du newline effectué).

    Erreurs possibles loggées
    -------------------------
    - Paramètre invalide         → ERROR
    - Répertoire introuvable     → ERROR
    - Fichier illisible          → ERROR  (on continue avec les suivants)
    - Aucune ligne lue           → WARNING
    - Erreur inattendue          → CRITICAL
    """
    all_rows: list[str] = []

    if not path or not isinstance(path, (str, Path)):
        _log.error("Chemin invalide fourni à to_rows : %r", path)
        return all_rows

    try:
        data_dir = Path(path)
    except Exception as exc:
        _log.critical("Impossible de résoudre le chemin '%s' : %s", path, exc)
        return all_rows

    # --- Vérification du répertoire ---
    if not data_dir.exists():
        _log.error("Répertoire introuvable : %s", data_dir.resolve())
        return all_rows

    if not data_dir.is_dir():
        _log.error("Le chemin n'est pas un répertoire : %s", data_dir.resolve())
        return all_rows

    # --- Listage des fichiers ---
    try:
        files = sorted(os.listdir(data_dir))
    except PermissionError as exc:
        _log.error("Permission refusée pour lister %s : %s", data_dir, exc)
        return all_rows
    except OSError as exc:
        _log.error("Erreur système lors du listage de %s : %s", data_dir, exc)
        return all_rows

    if not files:
        _log.warning("Aucun fichier trouvé dans : %s", data_dir.resolve())
        return all_rows

    _log.info("Lecture de %d fichier(s) dans %s", len(files), data_dir.resolve())

    # --- Lecture fichier par fichier ---
    for filename in files:
        file_path = data_dir / filename
        if not file_path.is_file():
            _log.debug("Ignoré (n'est pas un fichier) : %s", filename)
            continue

        try:
            if filename.endswith(".gz"):
                opener = gzip.open(file_path, mode="rt", encoding="utf-8", errors="replace")
            else:
                opener = open(file_path, encoding="utf-8", errors="replace")

            with opener as fh:
                lines = fh.readlines()
                all_rows.extend(lines)
                _log.debug("Fichier '%s' lu : %d lignes", filename, len(lines))

        except (OSError, gzip.BadGzipFile) as exc:
            _log.error("Erreur lecture fichier '%s' : %s", filename, exc)
            continue

    if not all_rows:
        _log.warning("Aucune ligne lue dans %s", data_dir.resolve())
    else:
        _log.info("Total lignes lues : %d", len(all_rows))

    return all_rows


# ---------------------------------------------------------------------------
# Test rapide si exécuté directement
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    data = to_rows("./data")
    if data:
        print(f"Exemple (ligne 1) : {data[0].strip()}")
        print(f"Total             : {len(data)} lignes")
