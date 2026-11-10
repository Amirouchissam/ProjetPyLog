"""
Module : serving/dashboard.py
Rôle   : Générer un dashboard visuel au format image PNG (dashboard.png)
         à partir des données stockées dans PostgreSQL.
         Utilise uniquement matplotlib (backend Agg non-interactif).

Graphiques demandés :
  1. Nombre de tentatives échouées par pays
  2. Nombre de tentatives réussies par utilisateur
  3. Tentatives échouées avec utilisateurs invalides (invalid user)
"""
import sys
from pathlib import Path
from typing import Optional

# Permettre l'exécution directe du script depuis n'importe quel dossier
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib
matplotlib.use("Agg")  # Mode sans interface graphique
import matplotlib.pyplot as plt

from logger.app_logger import get_logger

_log = get_logger("serving.dashboard")

OUTPUT_DIR: Path = Path(__file__).resolve().parent
OUTPUT_FILE: Path = OUTPUT_DIR / "dashboard.png"


def _plot_failed_by_country(ax: plt.Axes, data: list) -> None:
    """
    Trace le bar chart horizontal des tentatives échouées par pays.

    Paramètres
    ----------
    ax   : matplotlib.axes.Axes
    data : list[tuple(country, count)]
    """
    if not data:
        ax.text(
            0.5, 0.5, "Aucune tentative échouée",
            ha="center", va="center", color="#7f8c8d", fontsize=11
        )
        ax.set_title("Tentatives échouées par pays", fontsize=12, fontweight="bold")
        ax.axis("off")
        return

    # Limiter au top 15 pour la lisibilité
    top_data = data[:15]
    countries = [str(row[0]) for row in top_data][::-1]
    counts = [int(row[1]) for row in top_data][::-1]

    bars = ax.barh(countries, counts, color="#e74c3c", edgecolor="#c0392b", height=0.6)
    ax.set_title("1. Tentatives échouées par pays (Top 15)", fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel("Nombre d'échecs", fontsize=10)
    ax.bar_label(bars, padding=4, fontsize=9, fmt="%d")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", linestyle="--", alpha=0.4)


def _plot_success_by_user(ax: plt.Axes, data: list) -> None:
    """
    Trace le bar chart des connexions réussies par utilisateur.

    Paramètres
    ----------
    ax   : matplotlib.axes.Axes
    data : list[tuple(username, count)]
    """
    if not data:
        ax.text(
            0.5, 0.5, "Aucune connexion réussie",
            ha="center", va="center", color="#7f8c8d", fontsize=11
        )
        ax.set_title("Connexions réussies par utilisateur", fontsize=12, fontweight="bold")
        ax.axis("off")
        return

    top_data = data[:10]
    users = [str(row[0]) for row in top_data]
    counts = [int(row[1]) for row in top_data]

    bars = ax.bar(users, counts, color="#2ecc71", edgecolor="#27ae60", width=0.5)
    ax.set_title("2. Connexions réussies par utilisateur", fontsize=12, fontweight="bold", pad=10)
    ax.set_ylabel("Nombre de connexions", fontsize=10)
    ax.bar_label(bars, padding=3, fontsize=9, fmt="%d")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    if len(users) > 4:
        ax.tick_params(axis="x", rotation=25)


def _plot_invalid_users(ax: plt.Axes, data: list) -> None:
    """
    Trace le bar chart horizontal des utilisateurs invalides ciblés.

    Paramètres
    ----------
    ax   : matplotlib.axes.Axes
    data : list[tuple(username, count)]
    """
    if not data:
        ax.text(
            0.5, 0.5, "Aucune tentative avec utilisateur invalide",
            ha="center", va="center", color="#7f8c8d", fontsize=11
        )
        ax.set_title("Tentatives avec utilisateurs invalides", fontsize=12, fontweight="bold")
        ax.axis("off")
        return

    top_data = data[:12]
    users = [str(row[0]) for row in top_data][::-1]
    counts = [int(row[1]) for row in top_data][::-1]

    bars = ax.barh(users, counts, color="#e67e22", edgecolor="#d35400", height=0.6)
    ax.set_title("3. Tentatives échouées avec utilisateurs invalides (Top 12)", fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel("Nombre de tentatives", fontsize=10)
    ax.bar_label(bars, padding=4, fontsize=9, fmt="%d")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", linestyle="--", alpha=0.4)


def generate(conn) -> bool:
    """
    Récupère les données depuis PostgreSQL et génère le fichier image PNG :
    serving/dashboard.png

    Paramètres
    ----------
    conn : psycopg2.connection

    Retour
    ------
    bool : True si le fichier PNG a été généré avec succès, False sinon.
    """
    if conn is None:
        _log.error("generate() : connexion PostgreSQL None, impossible de générer le dashboard")
        return False

    _log.info("Extraction des données pour le dashboard PNG…")

    try:
        from storage.db import (
            query_failed_by_country,
            query_success_by_user,
            query_top_invalid_users,
        )

        data_country = query_failed_by_country(conn)
        data_user = query_success_by_user(conn)
        data_invalid = query_top_invalid_users(conn, limit=12)

    except Exception as exc:
        _log.error("Erreur lors de la récupération des données pour le dashboard : %s", exc)
        return False

    # Calcul des métriques globales
    total_failed = sum(row[1] for row in data_country) if data_country else 0
    total_success = sum(row[1] for row in data_user) if data_user else 0
    total_invalid = sum(row[1] for row in data_invalid) if data_invalid else 0
    total_countries = len(data_country) if data_country else 0

    _log.info(
        "Statistiques résumées : %d échecs, %d succès, %d invalides, %d pays",
        total_failed, total_success, total_invalid, total_countries
    )

    try:
        # Création de la figure globale (2 lignes x 2 colonnes, le 3ème graphique s'étend sur la 2ème ligne)
        fig = plt.figure(figsize=(15, 10), constrained_layout=True)
        fig.patch.set_facecolor("#f8f9fa")

        # Titre général du dashboard
        title_text = (
            "TABLEAU DE BORD - ANALYSE DES LOGS SSH\n"
            f"Total échecs : {total_failed}   |   Total succès : {total_success}   |   "
            f"Tentatives invalid user : {total_invalid}   |   Pays distincts : {total_countries}"
        )
        fig.suptitle(title_text, fontsize=14, fontweight="bold", color="#2c3e50", y=1.02)

        # Grille de 2 lignes x 2 colonnes
        gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.1])
        ax_country = fig.add_subplot(gs[0, 0])
        ax_user = fig.add_subplot(gs[0, 1])
        ax_invalid = fig.add_subplot(gs[1, :])  # Occupe toute la largeur en bas

        # Stylisation du fond des axes
        for ax in (ax_country, ax_user, ax_invalid):
            ax.set_facecolor("#ffffff")

        # Tracer les 3 graphiques demandés
        _plot_failed_by_country(ax_country, data_country)
        _plot_success_by_user(ax_user, data_user)
        _plot_invalid_users(ax_invalid, data_invalid)

        # Sauvegarde du fichier PNG
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        fig.savefig(OUTPUT_FILE, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)

        _log.info("✓ Dashboard PNG généré avec succès : %s", OUTPUT_FILE)
        return True

    except (OSError, PermissionError) as exc:
        _log.error("Erreur système lors de l'enregistrement du dashboard PNG : %s", exc)
        plt.close("all")
        return False
    except Exception as exc:
        _log.critical("Exception inattendue lors de la génération du dashboard PNG : %s", exc)
        plt.close("all")
        return False


if __name__ == "__main__":
    from storage.db import get_connection

    connection = get_connection()
    if connection:
        ok = generate(connection)
        connection.close()
        if ok:
            print(f"Dashboard PNG créé avec succès : {OUTPUT_FILE}")
    else:
        print("Erreur : impossible de se connecter à la base PostgreSQL.")
