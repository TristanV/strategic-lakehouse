"""
Gold Layer — Agrégation des KPI métier depuis Silver via DuckDB.

KPI implémentés :
  1. kpi_revenue_by_period   : CA total agrégé par année et par mois
  2. kpi_revenue_by_segment  : CA et panier moyen par segment/région client
  3. kpi_avg_basket           : Panier moyen et fréquence d'achat par client
  4. kpi_top_products         : Top produits par CA et par volume de ventes
  5. kpi_crm_engagement       : Score d'engagement CRM par canal et par segment

Conventions Gold :
  - Lecture des Parquet Silver via DuckDB (SQL analytique, zéro copie)
  - Colonnes de linéage ajoutées : _gold_computed_at, _source_layer
  - Écriture en Parquet dans data/gold/{kpi_name}.parquet
  - if __name__ == "__main__" exécutable directement

Auteur : Tristan Vanrullen — 2026
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)

_GOLD_COMPUTED_AT = datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_lineage(df: pd.DataFrame, kpi_name: str) -> pd.DataFrame:
    """Ajoute les colonnes de linéage Gold."""
    df["_kpi_name"] = kpi_name
    df["_source_layer"] = "silver"
    df["_gold_computed_at"] = _GOLD_COMPUTED_AT
    return df


def _save_parquet(df: pd.DataFrame, gold_dir: Path, kpi_name: str) -> Path:
    """Sauvegarde un DataFrame Gold en Parquet."""
    gold_dir.mkdir(parents=True, exist_ok=True)
    dest = gold_dir / f"{kpi_name}.parquet"
    df.to_parquet(dest, index=False, engine="pyarrow")
    logger.info("[GOLD] %s → %s (%d lignes)", kpi_name, dest, len(df))
    return dest


def _connect(silver_dir: Path) -> duckdb.DuckDBPyConnection:
    """Crée une connexion DuckDB in-memory et enregistre les Parquet Silver."""
    conn = duckdb.connect()
    tables = {
        "fact_sales": silver_dir / "fact_sales.parquet",
        "dim_products": silver_dir / "dim_products.parquet",
        "dim_customers": silver_dir / "dim_customers.parquet",
        "crm_interactions": silver_dir / "crm_interactions.parquet",
    }
    for name, path in tables.items():
        if path.exists():
            conn.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{path}')")
            logger.info("[GOLD] Vue DuckDB enregistrée : %s", name)
        else:
            logger.warning("[GOLD] Silver absent, vue non créée : %s", path)
    return conn


# ---------------------------------------------------------------------------
# KPI 1 — CA par période (année / mois)
# ---------------------------------------------------------------------------

def compute_kpi_revenue_by_period(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """
    KPI 1 : Chiffre d'affaires total agrégé par année et par mois.

    Colonnes produites :
        year (INT), month (INT), month_label (VARCHAR),
        total_revenue (DOUBLE), nb_orders (BIGINT), avg_order_value (DOUBLE)
    """
    sql = """
    SELECT
        YEAR(sale_date)                                     AS year,
        MONTH(sale_date)                                    AS month,
        STRFTIME(sale_date, '%Y-%m')                        AS month_label,
        ROUND(SUM(total_amount), 2)                         AS total_revenue,
        COUNT(DISTINCT sale_id)                             AS nb_orders,
        ROUND(AVG(total_amount), 2)                         AS avg_order_value
    FROM fact_sales
    WHERE sale_date IS NOT NULL
      AND total_amount IS NOT NULL
      AND total_amount >= 0
    GROUP BY year, month, month_label
    ORDER BY year, month
    """
    df = conn.execute(sql).df()
    logger.info("[GOLD] kpi_revenue_by_period : %d lignes", len(df))
    return _add_lineage(df, "kpi_revenue_by_period")


# ---------------------------------------------------------------------------
# KPI 2 — CA par segment / région client
# ---------------------------------------------------------------------------

def compute_kpi_revenue_by_segment(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """
    KPI 2 : CA et panier moyen par segment client et par région (si disponible).

    Jointure fact_sales → dim_customers.
    Colonnes produites :
        segment (VARCHAR), region (VARCHAR),
        total_revenue (DOUBLE), nb_orders (BIGINT),
        nb_customers (BIGINT), avg_order_value (DOUBLE)
    """
    sql = """
    SELECT
        COALESCE(c.customer_segment, 'Unknown')             AS segment,
        COALESCE(c.region, 'Unknown')                       AS region,
        ROUND(SUM(s.total_amount), 2)                       AS total_revenue,
        COUNT(DISTINCT s.sale_id)                           AS nb_orders,
        COUNT(DISTINCT s.customer_id)                       AS nb_customers,
        ROUND(AVG(s.total_amount), 2)                       AS avg_order_value
    FROM fact_sales s
    LEFT JOIN dim_customers c
        ON s.customer_id = c.customer_id
    WHERE s.total_amount IS NOT NULL
      AND s.total_amount >= 0
    GROUP BY segment, region
    ORDER BY total_revenue DESC
    """
    df = conn.execute(sql).df()
    logger.info("[GOLD] kpi_revenue_by_segment : %d lignes", len(df))
    return _add_lineage(df, "kpi_revenue_by_segment")


# ---------------------------------------------------------------------------
# KPI 3 — Panier moyen et fréquence d'achat par client
# ---------------------------------------------------------------------------

def compute_kpi_avg_basket(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """
    KPI 3 : Panier moyen, fréquence d'achat et LTV (lifetime value simplifiée) par client.

    Colonnes produites :
        customer_id (BIGINT), nb_orders (BIGINT),
        total_revenue (DOUBLE), avg_basket (DOUBLE),
        first_order_date (DATE), last_order_date (DATE),
        active_days (INT)
    """
    sql = """
    SELECT
        customer_id,
        COUNT(DISTINCT sale_id)                             AS nb_orders,
        ROUND(SUM(total_amount), 2)                         AS total_revenue,
        ROUND(AVG(total_amount), 2)                         AS avg_basket,
        MIN(sale_date)::DATE                                AS first_order_date,
        MAX(sale_date)::DATE                                AS last_order_date,
        DATEDIFF('day', MIN(sale_date), MAX(sale_date))     AS active_days
    FROM fact_sales
    WHERE customer_id IS NOT NULL
      AND total_amount IS NOT NULL
      AND total_amount >= 0
      AND sale_date IS NOT NULL
    GROUP BY customer_id
    ORDER BY total_revenue DESC
    """
    df = conn.execute(sql).df()
    logger.info("[GOLD] kpi_avg_basket : %d lignes (clients)", len(df))
    return _add_lineage(df, "kpi_avg_basket")


# ---------------------------------------------------------------------------
# KPI 4 — Top produits par CA et par volume
# ---------------------------------------------------------------------------

def compute_kpi_top_products(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """
    KPI 4 : Top produits classés par CA décroissant et par volume de ventes.

    Jointure fact_sales → dim_products pour enrichir avec nom et catégorie.
    Colonnes produites :
        product_id (BIGINT), product_name (VARCHAR), category (VARCHAR),
        total_revenue (DOUBLE), total_quantity (DOUBLE),
        nb_orders (BIGINT), avg_unit_price (DOUBLE),
        revenue_rank (INT), volume_rank (INT)
    """
    sql = """
    WITH base AS (
        SELECT
            s.product_id,
            COALESCE(p.product_name, 'Produit #' || s.product_id::VARCHAR) AS product_name,
            COALESCE(p.category, 'Unknown')                                AS category,
            ROUND(SUM(s.total_amount), 2)                                  AS total_revenue,
            ROUND(SUM(s.quantity), 2)                                      AS total_quantity,
            COUNT(DISTINCT s.sale_id)                                      AS nb_orders,
            ROUND(AVG(s.unit_price), 2)                                    AS avg_unit_price
        FROM fact_sales s
        LEFT JOIN dim_products p
            ON s.product_id = p.product_id
        WHERE s.product_id IS NOT NULL
          AND s.total_amount IS NOT NULL
          AND s.total_amount >= 0
        GROUP BY s.product_id, product_name, category
    )
    SELECT
        *,
        ROW_NUMBER() OVER (ORDER BY total_revenue  DESC) AS revenue_rank,
        ROW_NUMBER() OVER (ORDER BY total_quantity DESC) AS volume_rank
    FROM base
    ORDER BY revenue_rank
    """
    df = conn.execute(sql).df()
    logger.info("[GOLD] kpi_top_products : %d produits", len(df))
    return _add_lineage(df, "kpi_top_products")


# ---------------------------------------------------------------------------
# KPI 5 — Engagement CRM par canal et segment
# ---------------------------------------------------------------------------

def compute_kpi_crm_engagement(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """
    KPI 5 : Score d'engagement CRM agrégé par canal d'interaction et par segment client.

    Jointure crm_interactions → dim_customers.
    Colonnes produites :
        channel (VARCHAR), segment (VARCHAR),
        nb_interactions (BIGINT), nb_customers (BIGINT),
        avg_interactions_per_customer (DOUBLE),
        resolved_rate (DOUBLE)   -- taux d'interactions résolues (si colonne 'resolved')
    """
    sql = """
    SELECT
        COALESCE(i.channel, 'Unknown')                          AS channel,
        COALESCE(c.customer_segment, 'Unknown')                 AS segment,
        COUNT(i.interaction_id)                                 AS nb_interactions,
        COUNT(DISTINCT i.customer_id)                           AS nb_customers,
        ROUND(
            COUNT(i.interaction_id)::DOUBLE
            / NULLIF(COUNT(DISTINCT i.customer_id), 0),
            2
        )                                                       AS avg_interactions_per_customer,
        ROUND(
            100.0 * SUM(
                CASE WHEN LOWER(COALESCE(i.status, '')) IN ('resolved', 'closed', 'done')
                     THEN 1 ELSE 0 END
            )::DOUBLE / NULLIF(COUNT(i.interaction_id), 0),
            2
        )                                                       AS resolved_rate_pct
    FROM crm_interactions i
    LEFT JOIN dim_customers c
        ON i.customer_id = c.customer_id
    WHERE i.interaction_id IS NOT NULL
    GROUP BY channel, segment
    ORDER BY nb_interactions DESC
    """
    df = conn.execute(sql).df()
    logger.info("[GOLD] kpi_crm_engagement : %d lignes", len(df))
    return _add_lineage(df, "kpi_crm_engagement")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_gold_aggregations(
    silver_dir: Path,
    gold_dir: Path,
) -> dict[str, int]:
    """
    Exécute les 5 agrégations Gold et écrit les Parquet résultants.

    Returns:
        Dict {kpi_name: nb_lignes} pour chaque KPI produit.
    """
    conn = _connect(silver_dir)
    stats: dict[str, int] = {}

    kpis = [
        ("kpi_revenue_by_period",  compute_kpi_revenue_by_period),
        ("kpi_revenue_by_segment", compute_kpi_revenue_by_segment),
        ("kpi_avg_basket",          compute_kpi_avg_basket),
        ("kpi_top_products",        compute_kpi_top_products),
        ("kpi_crm_engagement",      compute_kpi_crm_engagement),
    ]

    for kpi_name, fn in kpis:
        try:
            df = fn(conn)
            _save_parquet(df, gold_dir, kpi_name)
            stats[kpi_name] = len(df)
        except Exception as exc:  # noqa: BLE001
            logger.error("[GOLD] Échec %s : %s", kpi_name, exc)

    conn.close()
    return stats


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )
    project_root = Path(__file__).resolve().parents[2]
    silver_dir = project_root / "data" / "silver"
    gold_dir   = project_root / "data" / "gold"

    print(f"\n🐙 Strategic Lakehouse — Gold Layer")
    print(f"   Silver source : {silver_dir}")
    print(f"   Gold output   : {gold_dir}\n")

    stats = run_gold_aggregations(silver_dir=silver_dir, gold_dir=gold_dir)

    print("\n✅ KPI Gold produits :")
    for kpi, nb in stats.items():
        print(f"   {kpi:<30} {nb:>6} lignes")
    print()
