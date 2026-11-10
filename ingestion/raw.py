"""
Module : ingestion/raw.py
Rôle   : Lire tous les fichiers de logs du dossier data/ (.log, .1, .gz).
         Retourne la liste des lignes brutes prêtes à être analysées.
"""
import gzip
import os

from logger.app_logger import get_logger

_log = get_logger("ingestion.raw")


def to_rows(data_dir: str = "data") -> list[str]:
    """
    Lit tous les fichiers de logs dans 'data_dir' et retourne leurs lignes.
    """
    all_rows: list[str] = []

    if not data_dir or not isinstance(data_dir, str):
        _log.error("Chemin invalide fourni : %r", data_dir)
        return all_rows

    if not os.path.exists(data_dir):
        _log.error("Dossier introuvable : %s", data_dir)
        return all_rows

    if not os.path.isdir(data_dir):
        _log.error("Le chemin spécifié n'est pas un dossier : %s", data_dir)
        return all_rows

    try:
        filenames = sorted(os.listdir(data_dir))
    except PermissionError as exc:
        _log.error("Permission refusée pour lister %s : %s", data_dir, exc)
        return all_rows
    except OSError as exc:
        _log.error("Erreur système lors du listage de %s : %s", data_dir, exc)
        return all_rows

    if not filenames:
        _log.warning("Aucun fichier trouvé dans %s", data_dir)
        return all_rows

    _log.info("Lecture de %d fichier(s) dans %s", len(filenames), data_dir)

    for filename in filenames:
        file_path = os.path.join(data_dir, filename)
        if not os.path.isfile(file_path):
            continue

        try:
            if filename.endswith(".gz"):
                fh = gzip.open(file_path, mode="rt", encoding="utf-8", errors="replace")
            else:
                fh = open(file_path, mode="r", encoding="utf-8", errors="replace")

            with fh:
                lines = fh.readlines()
                all_rows.extend(lines)
                _log.debug("Fichier '%s' lu : %d lignes", filename, len(lines))

        except (OSError, gzip.BadGzipFile) as exc:
            _log.error("Erreur lecture fichier '%s' : %s", filename, exc)
            continue

    if not all_rows:
        _log.warning("Aucune ligne lue dans %s", data_dir)
    else:
        _log.info("Total lignes lues : %d", len(all_rows))

    return all_rows


if __name__ == "__main__":
    rows = to_rows("data")
    print(f"Total lignes lues : {len(rows)}")
