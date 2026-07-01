"""Bronze Layer — Profilage rapide des fichiers ingérés.

Fournit un rapport de qualité basique (valeurs manquantes, doublons,
types inférés) sur chaque table Bronze, sans modifier les données.

Auteur : Tristan Vanrullen — 2026
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_META_COLS = {"_ingested_at", "_source_file", "_source_silo", "_run_id"}


def profile_parquet(parquet_path: Path) -> dict:
    """Retourne un dictionnaire de statistiques qualité sur un fichier Parquet Bronze."""
    df = pd.read_parquet(parquet_path)
    business_cols = [c for c in df.columns if c not in _META_COLS]
    biz_df = df[business_cols]

    null_counts = biz_df.isnull().sum() + (biz_df == "").sum()
    null_pct = (null_counts / len(df) * 100).round(2)

    return {
        "table": parquet_path.stem,
        "rows": len(df),
        "columns": len(business_cols),
        "duplicate_rows": int(biz_df.duplicated().sum()),
        "null_summary": null_pct[null_pct > 0].to_dict(),
        "inferred_dtypes": biz_df.infer_objects().dtypes.astype(str).to_dict(),
    }


def profile_bronze_layer(bronze_dir: Path) -> list[dict]:
    """Profile tous les fichiers Parquet de la couche Bronze."""
    reports = []
    for parquet_file in sorted(bronze_dir.rglob("*.parquet")):
        report = profile_parquet(parquet_file)
        reports.append(report)
        logger.info(
            "[PROFILING] %s — %d lignes, %d colonnes, %d doublons",
            report["table"],
            report["rows"],
            report["columns"],
            report["duplicate_rows"],
        )
    return reports


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    project_root = Path(__file__).resolve().parents[2]
    reports = profile_bronze_layer(project_root / "data" / "bronze")
    print(json.dumps(reports, indent=2, default=str))
