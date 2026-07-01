"""Silver Layer — Transformation Bronze → Silver.

Principes Silver :
  - Typage strict de toutes les colonnes métier
  - Dédoublonnage avec stratégie déclarée (clé métier + keep=last)
  - Pseudonymisation PII (customer_name, email) par hash SHA-256 (irréversible)
  - Normalisation des valeurs (strip, case, valeurs nulles unifiées)
  - Jointure fact_sales → dim_products + dim_customers pour enrichissement
  - Conservation des colonnes de traçabilité Bronze (_run_id, _source_silo)
  - Ajout de _silver_processed_at

Auteur : Tristan Vanrullen — 2026
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_META_COLS = {"_ingested_at", "_source_file", "_source_silo", "_run_id"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash_pii(value: str) -> str:
    """Hash SHA-256 irréversible pour pseudonymisation PII."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _load_bronze(bronze_dir: Path, silo: str, table: str) -> pd.DataFrame:
    path = bronze_dir / silo / f"{table}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Bronze introuvable : {path}")
    return pd.read_parquet(path)


def _drop_meta(df: pd.DataFrame, keep_lineage: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Sépare les colonnes métier des colonnes de linéage."""
    lineage_cols = [c for c in df.columns if c in _META_COLS]
    business_cols = [c for c in df.columns if c not in _META_COLS]
    return df[business_cols].copy(), df[lineage_cols].copy()


# ---------------------------------------------------------------------------
# Transformations par table
# ---------------------------------------------------------------------------

def transform_dim_products(bronze_dir: Path) -> pd.DataFrame:
    """Bronze g_dim_products → Silver dim_products."""
    df, lineage = _drop_meta(_load_bronze(bronze_dir, "erp", "g_dim_products"))

    # Nettoyage
    df.columns = df.columns.str.strip().str.lower()
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    df.replace("", pd.NA, inplace=True)

    # Typage
    for col in ["product_id", "category_id"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in ["unit_price", "cost_price"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")

    # Dédoublonnage sur clé métier
    if "product_id" in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=["product_id"], keep="last")
        logger.info("[SILVER] dim_products: %d doublons supprimés", before - len(df))

    # Lineage
    df["_source_silo"] = lineage["_source_silo"].iloc[0] if len(lineage) > 0 else "ERP_ONPREMISE"
    df["_run_id"] = lineage["_run_id"].iloc[0] if "_run_id" in lineage.columns else None
    df["_silver_processed_at"] = datetime.now(timezone.utc).isoformat()

    logger.info("[SILVER] dim_products: %d lignes", len(df))
    return df


def transform_dim_customers(bronze_dir: Path) -> pd.DataFrame:
    """Bronze g_dim_customers → Silver dim_customers (avec pseudonymisation PII)."""
    df, lineage = _drop_meta(_load_bronze(bronze_dir, "crm", "g_dim_customers"))

    df.columns = df.columns.str.strip().str.lower()
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    df.replace("", pd.NA, inplace=True)

    # Typage
    if "customer_id" in df.columns:
        df["customer_id"] = pd.to_numeric(df["customer_id"], errors="coerce").astype("Int64")
    for col in ["age", "loyalty_score"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    # Pseudonymisation PII
    for pii_col in ["customer_name", "email", "phone"]:
        if pii_col in df.columns:
            df[pii_col] = df[pii_col].apply(
                lambda x: _hash_pii(str(x)) if pd.notna(x) else pd.NA
            )
            logger.info("[SILVER] PII pseudonymisée : %s", pii_col)

    # Dédoublonnage
    if "customer_id" in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=["customer_id"], keep="last")
        logger.info("[SILVER] dim_customers: %d doublons supprimés", before - len(df))

    df["_source_silo"] = lineage["_source_silo"].iloc[0] if len(lineage) > 0 else "CRM_SAAS"
    df["_run_id"] = lineage["_run_id"].iloc[0] if "_run_id" in lineage.columns else None
    df["_silver_processed_at"] = datetime.now(timezone.utc).isoformat()

    logger.info("[SILVER] dim_customers: %d lignes", len(df))
    return df


def transform_fact_sales(bronze_dir: Path) -> pd.DataFrame:
    """Bronze g_fact_sales → Silver fact_sales."""
    df, lineage = _drop_meta(_load_bronze(bronze_dir, "erp", "g_fact_sales"))

    df.columns = df.columns.str.strip().str.lower()
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    df.replace("", pd.NA, inplace=True)

    # Typage
    for col in ["sale_id", "customer_id", "product_id"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in ["quantity", "unit_price", "total_amount", "discount"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
    for col in ["sale_date", "order_date", "ship_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Filtre qualité : rejeter lignes sans clé métier
    if "sale_id" in df.columns:
        before = len(df)
        df = df.dropna(subset=["sale_id"])
        logger.info("[SILVER] fact_sales: %d lignes rejetées (sale_id null)", before - len(df))

    # Dédoublonnage
    if "sale_id" in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=["sale_id"], keep="last")
        logger.info("[SILVER] fact_sales: %d doublons supprimés", before - len(df))

    df["_source_silo"] = lineage["_source_silo"].iloc[0] if len(lineage) > 0 else "ERP_ONPREMISE"
    df["_run_id"] = lineage["_run_id"].iloc[0] if "_run_id" in lineage.columns else None
    df["_silver_processed_at"] = datetime.now(timezone.utc).isoformat()

    logger.info("[SILVER] fact_sales: %d lignes", len(df))
    return df


def transform_crm_interactions(bronze_dir: Path) -> pd.DataFrame:
    """Bronze g_crm_interactions → Silver crm_interactions."""
    df, lineage = _drop_meta(_load_bronze(bronze_dir, "crm", "g_crm_interactions"))

    df.columns = df.columns.str.strip().str.lower()
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    df.replace("", pd.NA, inplace=True)

    for col in ["interaction_id", "customer_id"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in ["interaction_date", "created_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    if "interaction_id" in df.columns:
        df = df.drop_duplicates(subset=["interaction_id"], keep="last")

    df["_source_silo"] = lineage["_source_silo"].iloc[0] if len(lineage) > 0 else "CRM_SAAS"
    df["_run_id"] = lineage["_run_id"].iloc[0] if "_run_id" in lineage.columns else None
    df["_silver_processed_at"] = datetime.now(timezone.utc).isoformat()

    logger.info("[SILVER] crm_interactions: %d lignes", len(df))
    return df


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_silver_transformations(
    bronze_dir: Path,
    silver_dir: Path,
) -> dict[str, int]:
    """Exécute toutes les transformations Silver et sauvegarde en Parquet."""
    silver_dir.mkdir(parents=True, exist_ok=True)
    stats: dict[str, int] = {}

    transformers = {
        "dim_products": transform_dim_products,
        "dim_customers": transform_dim_customers,
        "fact_sales": transform_fact_sales,
        "crm_interactions": transform_crm_interactions,
    }

    for table_name, fn in transformers.items():
        try:
            df = fn(bronze_dir)
            dest = silver_dir / f"{table_name}.parquet"
            df.to_parquet(dest, index=False, engine="pyarrow")
            stats[table_name] = len(df)
            logger.info("[SILVER] Sauvegardé : %s (%d lignes)", dest, len(df))
        except FileNotFoundError as e:
            logger.warning("[SILVER] Ignoré (Bronze absent) : %s", e)

    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    project_root = Path(__file__).resolve().parents[2]
    stats = run_silver_transformations(
        bronze_dir=project_root / "data" / "bronze",
        silver_dir=project_root / "data" / "silver",
    )
    for table, nb in stats.items():
        print(f"  {table}: {nb} lignes transformées")
