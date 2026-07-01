"""Bronze Layer — Ingestion brute des sources CSV vers Parquet.

Principes Bronze :
  - Aucune transformation métier
  - Conservation du contenu verbatim
  - Ajout de métadonnées techniques d'ingestion (_ingested_at, _source_file, _source_silo)
  - Schéma tolérant (toutes colonnes en str avant typage en Silver)
  - Idempotent : ré-exécutable sans duplication (overwrite)

Auteur : Tristan Vanrullen — 2026
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapping sources → silos
# ---------------------------------------------------------------------------
SOURCE_MAP: dict[str, dict] = {
    "erp": {
        "files": ["g_dim_products.csv", "g_fact_sales.csv"],
        "silo": "ERP_ONPREMISE",
    },
    "crm": {
        "files": ["g_dim_customers.csv", "g_crm_interactions.csv"],
        "silo": "CRM_SAAS",
    },
    "analytics": {
        "files": ["g_sales_aggregated.csv"],
        "silo": "ANALYTICS_EXPORTS",
    },
}


def ingest_csv_to_bronze(
    raw_dir: Path,
    bronze_dir: Path,
    *,
    run_id: str | None = None,
) -> dict[str, int]:
    """Ingère tous les CSV sources vers la couche Bronze (Parquet).

    Args:
        raw_dir:    Chemin vers data/raw/
        bronze_dir: Chemin vers data/bronze/
        run_id:     Identifiant de run (pour traçabilité). Auto-généré si None.

    Returns:
        Dictionnaire {table_name: nb_rows_ingested}
    """
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ingested_at = datetime.now(timezone.utc).isoformat()
    stats: dict[str, int] = {}

    bronze_dir.mkdir(parents=True, exist_ok=True)

    for silo_folder, config in SOURCE_MAP.items():
        silo_raw = raw_dir / silo_folder
        silo_bronze = bronze_dir / silo_folder
        silo_bronze.mkdir(parents=True, exist_ok=True)

        for filename in config["files"]:
            src_path = silo_raw / filename
            if not src_path.exists():
                logger.warning("Fichier source introuvable, ignoré : %s", src_path)
                continue

            table_name = src_path.stem  # g_dim_products
            dest_path = silo_bronze / f"{table_name}.parquet"

            logger.info("[BRONZE] Ingestion de %s ...", src_path)

            # Lecture verbatim — toutes colonnes en str pour préserver la donnée brute
            df = pd.read_csv(src_path, dtype=str, keep_default_na=False)

            # Métadonnées techniques d'ingestion
            df["_ingested_at"] = ingested_at
            df["_source_file"] = str(src_path)
            df["_source_silo"] = config["silo"]
            df["_run_id"] = run_id

            df.to_parquet(dest_path, index=False, engine="pyarrow")
            stats[table_name] = len(df)
            logger.info("[BRONZE] → %s (%d lignes)", dest_path, len(df))

    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    project_root = Path(__file__).resolve().parents[2]
    result = ingest_csv_to_bronze(
        raw_dir=project_root / "data" / "raw",
        bronze_dir=project_root / "data" / "bronze",
    )
    for table, nb in result.items():
        print(f"  {table}: {nb} lignes ingérées")
