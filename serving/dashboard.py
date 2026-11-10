"""
Module : serving/dashboard.py
Rôle   : Générer un dashboard PNG avec 3 graphiques matplotlib
         à partir des données PostgreSQL.

Graphiques produits dans serving/dashboard.png :
  1. Tentatives échouées par pays        (bar chart horizontal)
  2. Connexions réussies par utilisateur (bar chart vertical)
  3. Tentatives avec utilisateur invalide (bar chart horizontal, top 15 users)
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")          # Backend non-interactif (pas d'écran requis)
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from logger.app_logger import get_logger

_log = get_logger("serving.dashboard")

OUTPUT_DIR  = Path(__file__).resolve().parent
OUTPUT_FILE = OUTPUT_DIR / "dashboard.png"


# ---------------------------------------------------------------------------
# Sous-graphiques
# ---------------------------------------------------------------------------

def _plot_failed_by_country(ax, data: list) -> None:
    """
    Graphique 1 : tentatives échouées par pays.

    Paramètres
    ----------
    ax   : matplotlib.axes.Axes
    data : list[tuple(country, nb_failed)]

    Erreurs possibles loggées
    -------------------------
    - data vide → WARNING
    """
    if not data:
        _log.warning("Graphique 1 : aucune donnée 'failed by country'")
        ax.text(0.5, 0.5, "Aucune donnée", ha="center", va="center",
                transform=ax.transAxes, fontsize=12, color="grey")
        ax.set_title("Tentatives échouées par pays", fontweight="bold")
        return

    top = data[:15]                         # top 15 pays
    pays   = [str(r[0]) for r in top][::-1]
    counts = [int(r[1]) for r in top][::-1]

    bars = ax.barh(pays, counts, color="#e74c3c", edgecolor="white", linewidth=0.5)
    ax.bar_label(bars, padding=4, fontsize=8, color="#2c3e50")
    ax.set_xlabel("Nombre de tentatives", fontsize=9)
    ax.set_title("① Tentatives échouées par pays (Top 15)", fontweight="bold", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=9)
    _log.info("Graphique 1 'failed_by_country' tracé (%d pays)", len(top))


def _plot_success_by_user(ax, data: list) -> None:
    """
    Graphique 2 : connexions réussies par utilisateur.

    Paramètres
    ----------
    ax   : matplotlib.axes.Axes
    data : list[tuple(username, nb_success)]

    Erreurs possibles loggées
    -------------------------
    - data vide → WARNING
    """
    if not data:
        _log.warning("Graphique 2 : aucune donnée 'success by user'")
        ax.text(0.5, 0.5, "Aucune donnée", ha="center", va="center",
                transform=ax.transAxes, fontsize=12, color="grey")
        ax.set_title("Connexions réussies par utilisateur", fontweight="bold")
        return

    top = data[:12]
    users  = [str(r[0]) for r in top]
    counts = [int(r[1]) for r in top]

    bars = ax.bar(users, counts, color="#2ecc71", edgecolor="white", linewidth=0.5)
    ax.bar_label(bars, padding=3, fontsize=8, color="#2c3e50")
    ax.set_ylabel("Connexions réussies", fontsize=9)
    ax.set_title("② Connexions réussies par utilisateur (Top 12)", fontweight="bold", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", rotation=30, labelsize=8)
    ax.tick_params(axis="y", labelsize=9)
    _log.info("Graphique 2 'success_by_user' tracé (%d users)", len(top))


def _plot_invalid_users(ax, data: list) -> None:
    """
    Graphique 3 : tentatives échouées avec utilisateurs invalides.

    Paramètres
    ----------
    ax   : matplotlib.axes.Axes
    data : list[tuple(username, ip, country, nb_attempts)]

    Erreurs possibles loggées
    -------------------------
    - data vide → WARNING
    """
    if not data:
        _log.warning("Graphique 3 : aucune donnée 'invalid users'")
        ax.text(0.5, 0.5, "Aucune donnée", ha="center", va="center",
                transform=ax.transAxes, fontsize=12, color="grey")
        ax.set_title("Tentatives invalides par utilisateur", fontweight="bold")
        return

    top = data[:15]
    # Label : "user (pays)"
    labels = [f"{str(r[0])} ({str(r[2])})" for r in top][::-1]
    counts = [int(r[3]) for r in top][::-1]

    bars = ax.barh(labels, counts, color="#e67e22", edgecolor="white", linewidth=0.5)
    ax.bar_label(bars, padding=4, fontsize=8, color="#2c3e50")
    ax.set_xlabel("Nombre de tentatives", fontsize=9)
    ax.set_title("③ Tentatives avec utilisateur invalide (Top 15)", fontweight="bold", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=8)
    _log.info("Graphique 3 'invalid_users' tracé (%d entrées)", len(top))


# ---------------------------------------------------------------------------
# Génération du PNG
# ---------------------------------------------------------------------------

def generate(conn) -> bool:
    """
    Génère le fichier dashboard.png (3 graphiques matplotlib).

    Paramètres
    ----------
    conn : psycopg2.connection

    Retour
    ------
    bool : True si l'image a été sauvegardée avec succès.

    Erreurs possibles loggées
    -------------------------
    - conn None                  → ERROR
    - Données vides pour un axe  → WARNING (géré dans chaque _plot_*)
    - Erreur sauvegarde fichier  → ERROR
    - Exception inattendue       → ERROR
    """
    if conn is None:
        _log.error("generate() : connexion PostgreSQL None, dashboard non généré")
        return False

    _log.info("Début de la génération du dashboard PNG…")

    # Import local pour éviter la circularité
    from storage.db import (
        query_failed_by_country,
        query_success_by_user,
        query_failed_invalid_users,
    )

    # --- Récupération des données ---
    try:
        data_country = query_failed_by_country(conn)
        data_user    = query_success_by_user(conn)
        data_invalid = query_failed_invalid_users(conn)
    except Exception as exc:
        _log.error("Erreur lors de la récupération des données : %s", exc)
        return False

    # --- KPI console ---
    total_failed  = sum(r[1] for r in data_country)
    total_success = sum(r[1] for r in data_user)
    total_invalid = sum(r[3] for r in data_invalid)
    _log.info(
        "KPI → Échecs: %d | Succès: %d | Invalides: %d | Pays: %d",
        total_failed, total_success, total_invalid, len(data_country)
    )

    # --- Construction de la figure ---
    try:
        fig = plt.figure(figsize=(18, 14))
        fig.suptitle(
            "SSH Log Analysis Dashboard",
            fontsize=16, fontweight="bold", y=0.98, color="#2c3e50"
        )

        # Sous-titre KPI
        kpi_text = (
            f"Échecs: {total_failed}   |   "
            f"Succès: {total_success}   |   "
            f"Utilisateurs invalides: {total_invalid}   |   "
            f"Pays distincts: {len(data_country)}"
        )
        fig.text(0.5, 0.945, kpi_text, ha="center", fontsize=10,
                 color="#7f8c8d", style="italic")

        # Mise en page : graphique 1 en haut, 2 et 3 en bas
        gs = gridspec.GridSpec(2, 2, figure=fig,
                               hspace=0.45, wspace=0.35,
                               top=0.92, bottom=0.07,
                               left=0.08, right=0.97)

        ax1 = fig.add_subplot(gs[0, :])   # Ligne 0, toute la largeur
        ax2 = fig.add_subplot(gs[1, 0])   # Ligne 1, colonne gauche
        ax3 = fig.add_subplot(gs[1, 1])   # Ligne 1, colonne droite

        _plot_failed_by_country(ax1, data_country)
        _plot_success_by_user(ax2, data_user)
        _plot_invalid_users(ax3, data_invalid)

        # Fond général
        fig.patch.set_facecolor("#f8f9fa")
        for ax in (ax1, ax2, ax3):
            ax.set_facecolor("#ffffff")

    except Exception as exc:
        _log.error("Erreur lors de la construction des graphiques : %s", exc)
        plt.close("all")
        return False

    # --- Sauvegarde PNG ---
    try:
        fig.savefig(OUTPUT_FILE, dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        _log.info("Dashboard PNG sauvegardé : %s", OUTPUT_FILE)
        return True
    except OSError as exc:
        _log.error("Impossible d'écrire le dashboard PNG : %s", exc)
        plt.close(fig)
        return False
    except Exception as exc:
        _log.error("Erreur inattendue lors de la sauvegarde : %s", exc)
        plt.close(fig)
        return False


# ---------------------------------------------------------------------------
# Test rapide si exécuté directement
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from storage.db import get_connection
    conn = get_connection()
    if conn:
        ok = generate(conn)
        conn.close()
        print(f"Dashboard PNG : {OUTPUT_FILE}" if ok else "Échec")
    else:
        print("Connexion PostgreSQL impossible.")
