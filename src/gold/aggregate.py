"""
Gold Layer — Agrégation des KPI métier depuis Silver via DuckDB.

KPI implémentés :
  1. kpi_revenue_by_period   : CA total agrégé par année et par mois
  2. kpi_revenue_by_segment  : CA et panier moyen par pays / statut marital
  3. kpi_avg_basket           : Panier moyen et fréquence d'achat par client
  4. kpi_top_products         : Top produits par CA et par volume de ventes
  5. kpi_crm_engagement       : Score d'engagement CRM par canal et pays

Conventions Gold :
  - Lecture des Parquet Silver via DuckDB (SQL analytique, zéro copie)
  - Colonnes de linéage ajoutées : _gold_computed_at, _source_layer, _kpi_name
  - Écriture en Parquet dans data/gold/{kpi_name}.parquet
  - Schéma tolérant : colonnes résolues dynamiquement au runtime
  - if __name__ == "__main__" exécutable directement

Schéma Silver confirmé (introspection 2026-07-02) :
  fact_sales      : customer_key, product_key, order_number, due_date, order_date,
                    quantity, sales, price, shipping_date
  dim_products    : product_key, product_id, product_name, category, sub_category,
                    cost, start_date
  dim_customers   : customer_key, customer_id, first_name, last_name, country,
                    marital_status, gender, birth_date
  crm_interactions: interaction_id, customer_id, channel, resolution_status,
                    interaction_type, interaction_date

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


def _resolve_col(cols: set[str], *candidates: str, default: str | None = None) -> str | None:
    """Retourne le premier candidat présent dans cols, ou default."""
    for c in candidates:
        if c.lower() in cols:
            return c
    if default is not None:
        logger.warning("[GOLD] Aucune colonne parmi %s trouvée → fallback '%s'", candidates, default)
    else:
        logger.warning("[GOLD] Aucune colonne parmi %s trouvée → NULL", candidates)
    return default  # None = colonne absente, à gérer par l'appelant


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


# ---------------------------------------------------------------------------
# KPI 1 — CA par période (année / mois)
# État schéma confirmé : due_date (VARCHAR), sales (DOUBLE), order_number (VARCHAR)
# ---------------------------------------------------------------------------

def compute_kpi_revenue_by_period(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """
    KPI 1 : CA total agrégé par année et par mois.

    Colonnes produites :
        year (INT), month (INT), month_label (VARCHAR),
        total_revenue (DOUBLE), nb_orders (BIGINT), avg_order_value (DOUBLE)
    """
    cols = _get_columns(conn, "fact_sales")

    date_col = _resolve_col(cols, "due_date", "order_date", "sale_date", "date")
    amt_col  = _resolve_col(cols, "sales", "total_amount", "amount", "revenue")
    id_col   = _resolve_col(cols, "order_number", "sale_id", "order_id", "transaction_id")

    if not all([date_col, amt_col, id_col]):
        raise ValueError(f"Colonnes manquantes dans fact_sales : date={date_col}, amt={amt_col}, id={id_col}")

    sql = f"""
    SELECT
        YEAR(TRY_CAST({date_col} AS DATE))                  AS year,
        MONTH(TRY_CAST({date_col} AS DATE))                 AS month,
        STRFTIME(TRY_CAST({date_col} AS DATE), '%Y-%m')     AS month_label,
        ROUND(SUM(TRY_CAST({amt_col} AS DOUBLE)), 2)        AS total_revenue,
        COUNT(DISTINCT {id_col})                             AS nb_orders,
        ROUND(AVG(TRY_CAST({amt_col} AS DOUBLE)), 2)        AS avg_order_value
    FROM fact_sales
    WHERE TRY_CAST({date_col} AS DATE) IS NOT NULL
      AND TRY_CAST({amt_col}  AS DOUBLE) IS NOT NULL
      AND TRY_CAST({amt_col}  AS DOUBLE) >= 0
    GROUP BY year, month, month_label
    ORDER BY year, month
    """
    df = conn.execute(sql).df()
    logger.info("[GOLD] kpi_revenue_by_period : %d lignes", len(df))
    return _add_lineage(df, "kpi_revenue_by_period")


# ---------------------------------------------------------------------------
# KPI 2 — CA par pays et statut marital (proxy segment)
# État schéma confirmé : dim_customers.country, marital_status (pas de customer_segment)
# ---------------------------------------------------------------------------

def compute_kpi_revenue_by_segment(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """
    KPI 2 : CA et panier moyen par pays et statut marital client.

    dim_customers ne contient pas customer_segment — country et marital_status
    servent d'axes de segmentation.

    Colonnes produites :
        country (VARCHAR), marital_status (VARCHAR),
        total_revenue (DOUBLE), nb_orders (BIGINT),
        nb_customers (BIGINT), avg_order_value (DOUBLE)
    """
    cols_s = _get_columns(conn, "fact_sales")
    cols_c = _get_columns(conn, "dim_customers")

    amt_col  = _resolve_col(cols_s, "sales", "total_amount", "amount", "revenue")
    id_col   = _resolve_col(cols_s, "order_number", "sale_id", "order_id", "transaction_id")
    fk_cust  = _resolve_col(cols_s, "customer_key", "customer_id", "cust_id")
    pk_cust  = _resolve_col(cols_c, "customer_key", "customer_id", "cust_id")

    if not all([amt_col, fk_cust, pk_cust]):
        raise ValueError(f"Colonnes jointure manquantes : amt={amt_col}, fk={fk_cust}, pk={pk_cust}")

    country_expr     = "COALESCE(c.country, 'Unknown')"        if "country"        in cols_c else "'Unknown'"
    marital_expr     = "COALESCE(c.marital_status, 'Unknown')" if "marital_status" in cols_c else "'Unknown'"
    id_count_expr    = f"COUNT(DISTINCT s.{id_col})"           if id_col else "COUNT(*)"

    sql = f"""
    SELECT
        {country_expr}                                      AS country,
        {marital_expr}                                      AS marital_status,
        ROUND(SUM(TRY_CAST(s.{amt_col} AS DOUBLE)), 2)     AS total_revenue,
        {id_count_expr}                                     AS nb_orders,
        COUNT(DISTINCT s.{fk_cust})                         AS nb_customers,
        ROUND(AVG(TRY_CAST(s.{amt_col} AS DOUBLE)), 2)     AS avg_order_value
    FROM fact_sales s
    LEFT JOIN dim_customers c
        ON s.{fk_cust}::VARCHAR = c.{pk_cust}::VARCHAR
    WHERE TRY_CAST(s.{amt_col} AS DOUBLE) IS NOT NULL
      AND TRY_CAST(s.{amt_col} AS DOUBLE) >= 0
    GROUP BY country, marital_status
    ORDER BY total_revenue DESC
    """
    df = conn.execute(sql).df()
    logger.info("[GOLD] kpi_revenue_by_segment : %d lignes", len(df))
    return _add_lineage(df, "kpi_revenue_by_segment")


# ---------------------------------------------------------------------------
# KPI 3 — Panier moyen et fréquence d'achat par client
# État schéma confirmé : customer_key, order_number, due_date, sales
# ---------------------------------------------------------------------------

def compute_kpi_avg_basket(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """
    KPI 3 : Panier moyen, fréquence d'achat et lifetime value simplifiée par client.

    Colonnes produites :
        customer_key (VARCHAR), nb_orders (BIGINT),
        total_revenue (DOUBLE), avg_basket (DOUBLE),
        first_order_date (DATE), last_order_date (DATE),
        active_days (INT)
    """
    cols = _get_columns(conn, "fact_sales")
    amt_col  = _resolve_col(cols, "sales", "total_amount", "amount", "revenue")
    id_col   = _resolve_col(cols, "order_number", "sale_id", "order_id", "transaction_id")
    date_col = _resolve_col(cols, "due_date", "order_date", "sale_date", "date")
    cust_col = _resolve_col(cols, "customer_key", "customer_id", "cust_id")

    if not all([amt_col, date_col, cust_col]):
        raise ValueError(f"Colonnes manquantes dans fact_sales : amt={amt_col}, date={date_col}, cust={cust_col}")

    id_expr = f"COUNT(DISTINCT {id_col})" if id_col else "COUNT(*)"

    sql = f"""
    SELECT
        {cust_col}::VARCHAR                                         AS customer_key,
        {id_expr}                                                    AS nb_orders,
        ROUND(SUM(TRY_CAST({amt_col} AS DOUBLE)), 2)                AS total_revenue,
        ROUND(AVG(TRY_CAST({amt_col} AS DOUBLE)), 2)                AS avg_basket,
        MIN(TRY_CAST({date_col} AS DATE))                           AS first_order_date,
        MAX(TRY_CAST({date_col} AS DATE))                           AS last_order_date,
        DATEDIFF('day',
            MIN(TRY_CAST({date_col} AS DATE)),
            MAX(TRY_CAST({date_col} AS DATE)))                       AS active_days
    FROM fact_sales
    WHERE {cust_col} IS NOT NULL
      AND TRY_CAST({amt_col}  AS DOUBLE) IS NOT NULL
      AND TRY_CAST({amt_col}  AS DOUBLE) >= 0
      AND TRY_CAST({date_col} AS DATE)   IS NOT NULL
    GROUP BY {cust_col}
    ORDER BY total_revenue DESC
    """
    df = conn.execute(sql).df()
    logger.info("[GOLD] kpi_avg_basket : %d lignes (clients)", len(df))
    return _add_lineage(df, "kpi_avg_basket")


# ---------------------------------------------------------------------------
# KPI 4 — Top produits par CA et par volume
# État schéma confirmé : product_key (fact+dim), product_name, category, quantity, sales
# ---------------------------------------------------------------------------

def compute_kpi_top_products(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """
    KPI 4 : Top produits classés par CA décroissant et par volume de ventes.

    Colonnes produites :
        product_key (VARCHAR), product_name (VARCHAR), category (VARCHAR),
        sub_category (VARCHAR), total_revenue (DOUBLE), total_quantity (DOUBLE),
        nb_orders (BIGINT), avg_unit_price (DOUBLE),
        revenue_rank (INT), volume_rank (INT)
    """
    cols_s = _get_columns(conn, "fact_sales")
    cols_p = _get_columns(conn, "dim_products")

    amt_col   = _resolve_col(cols_s, "sales", "total_amount", "amount", "revenue")
    id_col    = _resolve_col(cols_s, "order_number", "sale_id", "order_id", "transaction_id")
    qty_col   = _resolve_col(cols_s, "quantity", "qty", "order_quantity", "units")
    price_col = _resolve_col(cols_s, "price", "unit_price", "sale_price")
    fk_prod   = _resolve_col(cols_s, "product_key", "product_id", "prod_id")
    pk_prod   = _resolve_col(cols_p, "product_key", "product_id", "prod_id")

    if not all([amt_col, fk_prod, pk_prod]):
        raise ValueError(f"Colonnes produit manquantes : amt={amt_col}, fk={fk_prod}, pk={pk_prod}")

    name_expr    = "COALESCE(p.product_name, 'Produit #' || s." + fk_prod + "::VARCHAR)" if "product_name" in cols_p else "('Produit #' || s." + fk_prod + "::VARCHAR)"
    cat_expr     = "COALESCE(p.category, 'Unknown')"     if "category"     in cols_p else "'Unknown'"
    subcat_expr  = "COALESCE(p.sub_category, 'Unknown')" if "sub_category" in cols_p else "'Unknown'"
    qty_expr     = f"ROUND(SUM(TRY_CAST(s.{qty_col} AS DOUBLE)), 0)" if qty_col else "NULL::DOUBLE"
    price_expr   = f"ROUND(AVG(TRY_CAST(s.{price_col} AS DOUBLE)), 2)" if price_col else "NULL::DOUBLE"
    id_count     = f"COUNT(DISTINCT s.{id_col})" if id_col else "COUNT(*)"

    sql = f"""
    WITH base AS (
        SELECT
            s.{fk_prod}::VARCHAR                                AS product_key,
            {name_expr}                                         AS product_name,
            {cat_expr}                                          AS category,
            {subcat_expr}                                       AS sub_category,
            ROUND(SUM(TRY_CAST(s.{amt_col} AS DOUBLE)), 2)     AS total_revenue,
            {qty_expr}                                          AS total_quantity,
            {id_count}                                          AS nb_orders,
            {price_expr}                                        AS avg_unit_price
        FROM fact_sales s
        LEFT JOIN dim_products p
            ON s.{fk_prod}::VARCHAR = p.{pk_prod}::VARCHAR
        WHERE s.{fk_prod} IS NOT NULL
          AND TRY_CAST(s.{amt_col} AS DOUBLE) IS NOT NULL
          AND TRY_CAST(s.{amt_col} AS DOUBLE) >= 0
        GROUP BY s.{fk_prod}, product_name, category, sub_category
    )
    SELECT
        *,
        ROW_NUMBER() OVER (ORDER BY total_revenue DESC)  AS revenue_rank,
        ROW_NUMBER() OVER (ORDER BY total_quantity DESC) AS volume_rank
    FROM base
    ORDER BY revenue_rank
    """
    df = conn.execute(sql).df()
    logger.info("[GOLD] kpi_top_products : %d produits", len(df))
    return _add_lineage(df, "kpi_top_products")


# ---------------------------------------------------------------------------
# KPI 5 — Engagement CRM par canal et pays
# État schéma confirmé : resolution_status, channel, customer_id (interactions + dim)
# ---------------------------------------------------------------------------

def compute_kpi_crm_engagement(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """
    KPI 5 : Score d'engagement CRM agrégé par canal d'interaction et pays client.

    Colonnes produites :
        channel (VARCHAR), country (VARCHAR),
        nb_interactions (BIGINT), nb_customers (BIGINT),
        avg_interactions_per_customer (DOUBLE), resolved_rate_pct (DOUBLE)
    """
    cols_i = _get_columns(conn, "crm_interactions")
    cols_c = _get_columns(conn, "dim_customers")

    inter_id   = _resolve_col(cols_i, "interaction_id", "id", "crm_id")
    cust_fk    = _resolve_col(cols_i, "customer_id", "customer_key", "cust_id")
    status_col = _resolve_col(cols_i, "resolution_status", "status", "interaction_status")
    pk_cust    = _resolve_col(cols_c, "customer_id", "customer_key", "cust_id")

    if not all([inter_id, cust_fk, pk_cust]):
        raise ValueError(f"Colonnes CRM manquantes : inter_id={inter_id}, cust_fk={cust_fk}, pk={pk_cust}")

    country_expr = "COALESCE(c.country, 'Unknown')" if "country" in cols_c else "'Unknown'"
    resolved_vals = "('resolved', 'closed', 'done')"
    status_expr = (
        f"LOWER(COALESCE(i.{status_col}::VARCHAR, ''))"
        if status_col
        else "''"
    )

    sql = f"""
    SELECT
        COALESCE(i.channel, 'Unknown')                          AS channel,
        {country_expr}                                          AS country,
        COUNT(i.{inter_id})                                     AS nb_interactions,
        COUNT(DISTINCT i.{cust_fk})                             AS nb_customers,
        ROUND(
            COUNT(i.{inter_id})::DOUBLE
            / NULLIF(COUNT(DISTINCT i.{cust_fk}), 0),
            2
        )                                                       AS avg_interactions_per_customer,
        ROUND(
            100.0 * SUM(
                CASE WHEN {status_expr} IN {resolved_vals}
                     THEN 1 ELSE 0 END
            )::DOUBLE / NULLIF(COUNT(i.{inter_id}), 0),
            2
        )                                                       AS resolved_rate_pct
    FROM crm_interactions i
    LEFT JOIN dim_customers c
        ON i.{cust_fk}::VARCHAR = c.{pk_cust}::VARCHAR
    WHERE i.{inter_id} IS NOT NULL
    GROUP BY channel, country
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
