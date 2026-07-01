"""Bronze Layer — Génération synthétique de g_crm_interactions.

Contexte :
    Le dataset source Kaggle (GlobalTrade) ne fournit pas de table
    d'interactions CRM. Ce script génère des interactions fictives
    mais cohérentes avec les customer_id existants dans g_dim_customers,
    puis les dépose directement en Bronze (Parquet) selon les conventions
    du pipeline.

Conventions Bronze respectées :
    - Toutes les colonnes sont stockées en str (typage en Silver uniquement)
    - Métadonnées techniques : _ingested_at, _source_file, _source_silo, _run_id
    - Idempotent : ré-exécutable (overwrite)
    - Aucune transformation métier

Schéma généré :
    interaction_id      str  — identifiant unique séquentiel
    customer_id         str  — FK vers g_dim_customers (tirage pondéré)
    interaction_date    str  — date ISO 8601 (2022-01-01 → 2024-12-31)
    channel             str  — email | phone | chat | in_store | social_media
    interaction_type    str  — complaint | inquiry | purchase | feedback | support
    resolution_status   str  — resolved | pending | escalated | no_action
    agent_id            str  — identifiant anonyme de l'agent CRM
    duration_minutes    str  — durée en minutes (1–120, null possible)
    satisfaction_score  str  — 1–5 ou vide (NPS simplifié)
    notes               str  — texte libre court (peut être vide)

Usage :
    python src/bronze/generate_crm_interactions.py
    # → data/bronze/crm/g_crm_interactions.parquet  (~20 000 lignes)

    python src/bronze/generate_crm_interactions.py --n 50000 --seed 99

Auteur : Tristan Vanrullen — 2026
"""

from __future__ import annotations

import argparse
import logging
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes métier (valeurs réalistes CRM GlobalTrade)
# ---------------------------------------------------------------------------

CHANNELS = ["email", "phone", "chat", "in_store", "social_media"]
CHANNEL_WEIGHTS = [0.30, 0.25, 0.20, 0.15, 0.10]

INTERACTION_TYPES = ["complaint", "inquiry", "purchase", "feedback", "support"]
TYPE_WEIGHTS = [0.15, 0.30, 0.25, 0.15, 0.15]

RESOLUTION_STATUS = ["resolved", "pending", "escalated", "no_action"]
STATUS_WEIGHTS = [0.55, 0.20, 0.10, 0.15]

NOTE_TEMPLATES = [
    "Customer contacted regarding order status.",
    "Issue resolved after verification.",
    "Follow-up required within 48h.",
    "Customer satisfied with resolution.",
    "Escalated to tier-2 support.",
    "Product return initiated.",
    "Loyalty points query resolved.",
    "Technical issue reported on mobile app.",
    "Promotional code applied successfully.",
    "Complaint logged, investigation ongoing.",
    "Repeat contact — second occurrence.",
    "Customer requested callback.",
    "",  # champ vide (cas réel fréquent)
    "",
    "",
]

DATE_START = datetime(2022, 1, 1)
DATE_END = datetime(2024, 12, 31)
DATE_RANGE_DAYS = (DATE_END - DATE_START).days


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _random_date(rng: random.Random) -> str:
    """Retourne une date ISO aléatoire entre DATE_START et DATE_END."""
    return (DATE_START + timedelta(days=rng.randint(0, DATE_RANGE_DAYS))).strftime(
        "%Y-%m-%d"
    )


def _random_duration(rng: random.Random) -> str:
    """Durée en minutes (1-120), 8 % de valeurs vides (données manquantes réalistes)."""
    if rng.random() < 0.08:
        return ""
    return str(rng.randint(1, 120))


def _random_satisfaction(rng: random.Random) -> str:
    """Score satisfaction 1-5, 12 % de valeurs vides."""
    if rng.random() < 0.12:
        return ""
    return str(rng.randint(1, 5))


def _load_customer_ids(bronze_dir: Path) -> list[str]:
    """Charge les customer_id depuis le Bronze CRM existant."""
    crm_path = bronze_dir / "crm" / "g_dim_customers.parquet"
    if not crm_path.exists():
        raise FileNotFoundError(
            f"g_dim_customers introuvable : {crm_path}\n"
            "Lancez d'abord : python src/bronze/ingest.py"
        )
    df = pd.read_parquet(crm_path, columns=["customer_id"])
    ids = df["customer_id"].dropna().unique().tolist()
    logger.info("[CRM_GEN] %d customer_id chargés depuis Bronze.", len(ids))
    return ids


# ---------------------------------------------------------------------------
# Génération principale
# ---------------------------------------------------------------------------

def generate_crm_interactions(
    bronze_dir: Path,
    *,
    n: int = 20_000,
    seed: int = 42,
    run_id: str | None = None,
) -> pd.DataFrame:
    """Génère n interactions CRM synthétiques cohérentes avec les clients Bronze.

    Args:
        bronze_dir: Chemin vers data/bronze/ (pour lire les customer_id).
        n:          Nombre de lignes à générer (défaut 20 000).
        seed:       Graine aléatoire pour reproductibilité.
        run_id:     Identifiant de run (traçabilité Bronze).

    Returns:
        DataFrame prêt à être écrit en Parquet Bronze.
    """
    rng = random.Random(seed)
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ingested_at = datetime.now(timezone.utc).isoformat()

    customer_ids = _load_customer_ids(bronze_dir)

    # Pondération : les clients récurrents interagissent plus souvent
    # (distribution de Zipf simplifiée — 20 % des clients = 60 % des interactions)
    top_n = max(1, len(customer_ids) // 5)
    top_customers = customer_ids[:top_n]
    other_customers = customer_ids[top_n:]

    rows = []
    for i in range(1, n + 1):
        # Sélection client (60 % top, 40 % autres)
        if rng.random() < 0.60 and top_customers:
            cid = rng.choice(top_customers)
        else:
            cid = rng.choice(customer_ids)

        channel = rng.choices(CHANNELS, weights=CHANNEL_WEIGHTS, k=1)[0]
        itype = rng.choices(INTERACTION_TYPES, weights=TYPE_WEIGHTS, k=1)[0]
        status = rng.choices(RESOLUTION_STATUS, weights=STATUS_WEIGHTS, k=1)[0]
        agent_id = f"AGT{rng.randint(1, 50):03d}"

        rows.append(
            {
                "interaction_id": str(i),
                "customer_id": str(cid),
                "interaction_date": _random_date(rng),
                "channel": channel,
                "interaction_type": itype,
                "resolution_status": status,
                "agent_id": agent_id,
                "duration_minutes": _random_duration(rng),
                "satisfaction_score": _random_satisfaction(rng),
                "notes": rng.choice(NOTE_TEMPLATES),
            }
        )

    df = pd.DataFrame(rows)

    # Métadonnées Bronze (toutes en str, convention pipeline)
    df["_ingested_at"] = ingested_at
    df["_source_file"] = "synthetic:generate_crm_interactions.py"
    df["_source_silo"] = "CRM_SAAS"
    df["_run_id"] = run_id

    logger.info(
        "[CRM_GEN] %d interactions générées (seed=%d, run_id=%s).", n, seed, run_id
    )
    return df


# ---------------------------------------------------------------------------
# Persistance Bronze
# ---------------------------------------------------------------------------

def write_to_bronze(df: pd.DataFrame, bronze_dir: Path) -> Path:
    """Écrit le DataFrame en Parquet dans data/bronze/crm/."""
    dest = bronze_dir / "crm" / "g_crm_interactions.parquet"
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(dest, index=False, engine="pyarrow")
    logger.info("[CRM_GEN] Sauvegardé : %s (%d lignes)", dest, len(df))
    return dest


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Génère g_crm_interactions synthétique et le dépose en Bronze."
    )
    parser.add_argument(
        "--n",
        type=int,
        default=20_000,
        help="Nombre d'interactions à générer (défaut : 20 000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Graine aléatoire pour reproductibilité (défaut : 42)",
    )
    parser.add_argument(
        "--bronze-dir",
        type=Path,
        default=None,
        help="Chemin vers data/bronze/ (défaut : auto-détecté depuis __file__)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args()

    project_root = Path(__file__).resolve().parents[2]
    bronze_dir = args.bronze_dir or (project_root / "data" / "bronze")

    df = generate_crm_interactions(bronze_dir, n=args.n, seed=args.seed)
    dest = write_to_bronze(df, bronze_dir)

    print(f"\n✓ g_crm_interactions généré : {dest}")
    print(f"  Lignes       : {len(df)}")
    print(f"  Colonnes     : {', '.join(df.columns.tolist())}")
    print(f"  Canaux       : {df['channel'].value_counts().to_dict()}")
    print(f"  Types        : {df['interaction_type'].value_counts().to_dict()}")
    print(
        f"  Score manquant : {(df['satisfaction_score'] == '').sum()} "
        f"({(df['satisfaction_score'] == '').mean():.1%})"
    )
    print(f"\nRelancez maintenant : python src/silver/transform.py")
