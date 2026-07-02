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
  - Colonnes optionnelles détectées dynamiquement (schéma tolérant)
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


def _get_columns(conn: duckdb.DuckDBPyConnection, view: str) -> set[str]:
    """Retourne l'ensemble des colonnes d'une vue DuckDB (minuscules)."""
    try:
        result = conn.execute(f"DESCRIBE {view}").fetchall()
        return {row[0].lower() for row in result}
    except Exception:  # noqa: BLE001
        return set()


def _connect(silver_dir: Path) -> duckdb.DuckDBPyConnection:
    """Crée une connexion DuckDB in-memory et enregistre les Parquet Silver comme vues."""
    conn = duckdb.connect()
    tables = {
        "fact_sales":       silver_dir / "fact_sales.parquet",
        "dim_products":     silver_dir / "dim_products.parquet",
        "dim_customers":    silver_dir / "dim_customers.parquet",
        "crm_interactions": silver_dir / "crm_interactions.parquet",
    }
    for name, path in tables.items():
        if path.exists():
            conn.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{path}')")
            cols = _get_columns(conn, name)
            logger.info("[GOLD] Vue DuckDB enregistrée : %-20s colonnes=%s", name, sorted(cols))
        else:
            logger.warning("[GOLD] Silver absent, vue non créée : %s", path)
    return conn


def _resolve_col(cols: set[str], *candidates: str, default: str = "NULL") -> str:
    """Retourne le premier candidat présent dans cols, ou default si aucun ne l'est."""
    for c in candidates:
        if c.lower() in cols:
            return c
    logger.warning("[GOLD] Aucune colonne parmi %s trouvée → %s utilisé", candidates, default)
    return default


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
    cols = _get_columns(conn, "fact_sales")

    # Colonne de date : sale_date ou due_date ou order_date
    date_col  = _resolve_col(cols, "sale_date", "due_date", "order_date", "date")
    # Colonne de montant : total_amount ou amount ou revenue
    amt_col   = _resolve_col(cols, "total_amount", "amount", "revenue", "sales_amount")
    # Clé de commande : sale_id ou order_id ou id
    id_col    = _resolve_col(cols, "sale_id", "order_id", "id", "transaction_id")

    sql = f"""
    SELECT
        YEAR({date_col})                                    AS year,
        MONTH({date_col})                                   AS month,
        STRFTIME({date_col}::DATE, '%Y-%m')                 AS month_label,
        ROUND(SUM({amt_col}::DOUBLE), 2)                    AS total_revenue,
        COUNT(DISTINCT {id_col})                            AS nb_orders,
        ROUND(AVG({amt_col}::DOUBLE), 2)                    AS avg_order_value
    FROM fact_sales
    WHERE {date_col} IS NOT NULL
      AND {amt_col}  IS NOT NULL
      AND {amt_col}::DOUBLE >= 0
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

    Colonnes produites :
        segment (VARCHAR), region (VARCHAR),
        total_revenue (DOUBLE), nb_orders (BIGINT),
        nb_customers (BIGINT), avg_order_value (DOUBLE)
    """
    cols_s = _get_columns(conn, "fact_sales")
    cols_c = _get_columns(conn, "dim_customers")

    amt_col      = _resolve_col(cols_s, "total_amount", "amount", "revenue", "sales_amount")
    id_col       = _resolve_col(cols_s, "sale_id", "order_id", "id", "transaction_id")
    # Clé de jointure côté fact_sales
    fk_cust      = _resolve_col(cols_s, "customer_id", "customer_key", "cust_id")
    # Clé de jointure côté dim_customers
    pk_cust      = _resolve_col(cols_c, "customer_id", "customer_key", "cust_id")

    # Colonnes optionnelles dans dim_customers
    seg_expr = (
        "COALESCE(c.customer_segment, 'Unknown')"
        if "customer_segment" in cols_c
        else "COALESCE(c.segment, 'Unknown')"
        if "segment" in cols_c
        else "'Unknown'"
    )
    region_expr = (
        "COALESCE(c.region, 'Unknown')"
        if "region" in cols_c
        else "COALESCE(c.country, 'Unknown')"
        if "country" in cols_c
        else "'Unknown'"
    )

    sql = f"""
    SELECT
        {seg_expr}                                          AS segment,
        {region_expr}                                       AS region,
        ROUND(SUM(s.{amt_col}::DOUBLE), 2)                 AS total_revenue,
        COUNT(DISTINCT s.{id_col})                          AS nb_orders,
        COUNT(DISTINCT s.{fk_cust})                         AS nb_customers,
        ROUND(AVG(s.{amt_col}::DOUBLE), 2)                  AS avg_order_value
    FROM fact_sales s
    LEFT JOIN dim_customers c
        ON s.{fk_cust}::VARCHAR = c.{pk_cust}::VARCHAR
    WHERE s.{amt_col} IS NOT NULL
      AND s.{amt_col}::DOUBLE >= 0
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
        customer_key (VARCHAR), nb_orders (BIGINT),
        total_revenue (DOUBLE), avg_basket (DOUBLE),
        first_order_date (DATE), last_order_date (DATE),
        active_days (INT)
    """
    cols = _get_columns(conn, "fact_sales")
    amt_col  = _resolve_col(cols, "total_amount", "amount", "revenue", "sales_amount")
    id_col   = _resolve_col(cols, "sale_id", "order_id", "id", "transaction_id")
    date_col = _resolve_col(cols, "sale_date", "due_date", "order_date", "date")
    cust_col = _resolve_col(cols, "customer_id", "customer_key", "cust_id")

    sql = f"""
    SELECT
        {cust_col}::VARCHAR                                 AS customer_key,
        COUNT(DISTINCT {id_col})                            AS nb_orders,
        ROUND(SUM({amt_col}::DOUBLE), 2)                    AS total_revenue,
        ROUND(AVG({amt_col}::DOUBLE), 2)                    AS avg_basket,
        MIN({date_col})::DATE                               AS first_order_date,
        MAX({date_col})::DATE                               AS last_order_date,
        DATEDIFF('day', MIN({date_col})::DATE,
                        MAX({date_col})::DATE)               AS active_days
    FROM fact_sales
    WHERE {cust_col} IS NOT NULL
      AND {amt_col}  IS NOT NULL
      AND {amt_col}::DOUBLE >= 0
      AND {date_col} IS NOT NULL
    GROUP BY {cust_col}
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

    Colonnes produites :
        product_key (VARCHAR), product_name (VARCHAR), category (VARCHAR),
        total_revenue (DOUBLE), total_quantity (DOUBLE),
        nb_orders (BIGINT), avg_unit_price (DOUBLE),
        revenue_rank (INT), volume_rank (INT)
    """
    cols_s = _get_columns(conn, "fact_sales")
    cols_p = _get_columns(conn, "dim_products")

    amt_col   = _resolve_col(cols_s, "total_amount", "amount", "revenue", "sales_amount")
    id_col    = _resolve_col(cols_s, "sale_id", "order_id", "id", "transaction_id")
    qty_col   = _resolve_col(cols_s, "quantity", "qty", "order_quantity", "units")
    price_col = _resolve_col(cols_s, "unit_price", "price", "sale_price", "amount")
    # Clé produit côté fact
    fk_prod   = _resolve_col(cols_s, "product_id", "product_key", "prod_id")
    # Clé produit côté dim
    pk_prod   = _resolve_col(cols_p, "product_id", "product_key", "prod_id")

    name_expr  = "COALESCE(p.product_name, 'Produit #' || s." + fk_prod + "::VARCHAR)" if "product_name" in cols_p else "('Produit #' || s." + fk_prod + "::VARCHAR)"
    cat_expr   = "COALESCE(p.category, 'Unknown')" if "category" in cols_p else "COALESCE(p.product_category, 'Unknown')" if "product_category" in cols_p else "'Unknown'"
    qty_expr   = f"ROUND(SUM(s.{qty_col}::DOUBLE), 2)" if qty_col != "NULL" else "NULL::DOUBLE"
    price_expr = f"ROUND(AVG(s.{price_col}::DOUBLE), 2)" if price_col != "NULL" else "NULL::DOUBLE"

    sql = f"""
    WITH base AS (
        SELECT
            s.{fk_prod}::VARCHAR                            AS product_key,
            {name_expr}                                     AS product_name,
            {cat_expr}                                      AS category,
            ROUND(SUM(s.{amt_col}::DOUBLE), 2)             AS total_revenue,
            {qty_expr}                                      AS total_quantity,
            COUNT(DISTINCT s.{id_col})                      AS nb_orders,
            {price_expr}                                    AS avg_unit_price
        FROM fact_sales s
        LEFT JOIN dim_products p
            ON s.{fk_prod}::VARCHAR = p.{pk_prod}::VARCHAR
        WHERE s.{fk_prod} IS NOT NULL
          AND s.{amt_col}  IS NOT NULL
          AND s.{amt_col}::DOUBLE >= 0
        GROUP BY s.{fk_prod}, product_name, category
    )
    SELECT
        *,
        ROW_NUMBER() OVER (ORDER BY total_revenue  DESC) AS revenue_rank,
        ROW_NUMBER() OVER (ORDER BY total_quantity DESC)  AS volume_rank
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

    Colonnes produites :
        channel (VARCHAR), segment (VARCHAR),
        nb_interactions (BIGINT), nb_customers (BIGINT),
        avg_interactions_per_customer (DOUBLE), resolved_rate_pct (DOUBLE)
    """
    cols_i = _get_columns(conn, "crm_interactions")
    cols_c = _get_columns(conn, "dim_customers")

    # Clés et colonnes CRM
    inter_id = _resolve_col(cols_i, "interaction_id", "id", "crm_id")
    cust_fk  = _resolve_col(cols_i, "customer_id", "customer_key", "cust_id")
    # Statut de résolution : resolution_status (généré) ou status
    status_col = _resolve_col(cols_i, "resolution_status", "status", "interaction_status")

    # Clé client dim
    pk_cust = _resolve_col(cols_c, "customer_id", "customer_key", "cust_id")

    # Segment client (optionnel)
    seg_expr = (
        "COALESCE(c.customer_segment, 'Unknown')"
        if "customer_segment" in cols_c
        else "COALESCE(c.segment, 'Unknown')"
        if "segment" in cols_c
        else "'Unknown'"
    )

    # Valeurs résolues connues : resolved | pending | escalated | no_action
    resolved_values = "('resolved', 'closed', 'done')"

    sql = f"""
    SELECT
        COALESCE(i.channel, 'Unknown')                          AS channel,
        {seg_expr}                                              AS segment,
        COUNT(i.{inter_id})                                     AS nb_interactions,
        COUNT(DISTINCT i.{cust_fk})                             AS nb_customers,
        ROUND(
            COUNT(i.{inter_id})::DOUBLE
            / NULLIF(COUNT(DISTINCT i.{cust_fk}), 0),
            2
        )                                                       AS avg_interactions_per_customer,
        ROUND(
            100.0 * SUM(
                CASE WHEN LOWER(COALESCE(i.{status_col}::VARCHAR, ''))
                          IN {resolved_values}
                     THEN 1 ELSE 0 END
            )::DOUBLE / NULLIF(COUNT(i.{inter_id}), 0),
            2
        )                                                       AS resolved_rate_pct
    FROM crm_interactions i
    LEFT JOIN dim_customers c
        ON i.{cust_fk}::VARCHAR = c.{pk_cust}::VARCHAR
    WHERE i.{inter_id} IS NOT NULL
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
    if not stats:
        print("   ⚠️  Aucun KPI produit — vérifiez que data/silver/ est peuplé.")
    print()
