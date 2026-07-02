"""
Tests pytest — Couche Gold (src/gold/aggregate.py).

Couverture :
  - test_get_columns            : _get_columns() retourne bien les colonnes attendues
  - test_resolve_col            : _resolve_col() résout le bon candidat
  - test_kpi_revenue_by_period  : structure, types, pas de NULL sur year/month
  - test_kpi_revenue_by_segment : colonnes country + marital_status présentes
  - test_kpi_avg_basket         : une ligne par client, total_revenue >= 0
  - test_kpi_top_products       : revenue_rank commence à 1, pas de doublon
  - test_kpi_crm_engagement     : resolved_rate_pct entre 0 et 100
  - test_run_gold_aggregations  : orchestrateur produit 5 fichiers Parquet
  - test_lineage_columns        : colonnes _kpi_name, _source_layer, _gold_computed_at

Auteur : Tristan Vanrullen — 2026
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from src.gold.aggregate import (
    _get_columns,
    _resolve_col,
    compute_kpi_avg_basket,
    compute_kpi_crm_engagement,
    compute_kpi_revenue_by_period,
    compute_kpi_revenue_by_segment,
    compute_kpi_top_products,
    run_gold_aggregations,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

LINEAGE_COLS = {"_kpi_name", "_source_layer", "_gold_computed_at"}


# ---------------------------------------------------------------------------
# Tests utilitaires
# ---------------------------------------------------------------------------

def test_get_columns(duckdb_conn):
    """_get_columns() retourne un ensemble non vide contenant les colonnes attendues."""
    cols = _get_columns(duckdb_conn, "fact_sales")
    assert isinstance(cols, set)
    assert "customer_key" in cols
    assert "sales" in cols
    assert "due_date" in cols


def test_resolve_col_found(duckdb_conn):
    """_resolve_col() retourne le premier candidat présent."""
    cols = _get_columns(duckdb_conn, "fact_sales")
    result = _resolve_col(cols, "total_amount", "sales", "revenue")
    assert result == "sales"


def test_resolve_col_not_found(duckdb_conn):
    """_resolve_col() retourne None si aucun candidat n'est présent."""
    cols = _get_columns(duckdb_conn, "fact_sales")
    result = _resolve_col(cols, "nonexistent_col", "another_missing")
    assert result is None


def test_resolve_col_with_default(duckdb_conn):
    """_resolve_col() retourne le default si spécifié et aucun candidat trouvé."""
    cols = _get_columns(duckdb_conn, "fact_sales")
    result = _resolve_col(cols, "missing", default="fallback_value")
    assert result == "fallback_value"


# ---------------------------------------------------------------------------
# KPI 1 — revenue_by_period
# ---------------------------------------------------------------------------

def test_kpi_revenue_by_period_structure(duckdb_conn):
    """KPI 1 : colonnes attendues, pas de NULL sur year/month/total_revenue."""
    df = compute_kpi_revenue_by_period(duckdb_conn)
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    for col in ("year", "month", "month_label", "total_revenue", "nb_orders", "avg_order_value"):
        assert col in df.columns, f"Colonne manquante : {col}"
    assert df["year"].notna().all()
    assert df["month"].notna().all()
    assert df["total_revenue"].notna().all()


def test_kpi_revenue_by_period_values(duckdb_conn):
    """KPI 1 : total_revenue > 0, nb_orders >= 1, month dans [1..12]."""
    df = compute_kpi_revenue_by_period(duckdb_conn)
    assert (df["total_revenue"] > 0).all()
    assert (df["nb_orders"] >= 1).all()
    assert df["month"].between(1, 12).all()


def test_kpi_revenue_by_period_lineage(duckdb_conn):
    """KPI 1 : colonnes de linéage présentes."""
    df = compute_kpi_revenue_by_period(duckdb_conn)
    assert LINEAGE_COLS.issubset(set(df.columns))
    assert (df["_source_layer"] == "silver").all()
    assert (df["_kpi_name"] == "kpi_revenue_by_period").all()


# ---------------------------------------------------------------------------
# KPI 2 — revenue_by_segment
# ---------------------------------------------------------------------------

def test_kpi_revenue_by_segment_structure(duckdb_conn):
    """KPI 2 : colonnes country, marital_status, total_revenue présentes."""
    df = compute_kpi_revenue_by_segment(duckdb_conn)
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    for col in ("country", "marital_status", "total_revenue", "nb_orders", "nb_customers"):
        assert col in df.columns, f"Colonne manquante : {col}"


def test_kpi_revenue_by_segment_no_negative(duckdb_conn):
    """KPI 2 : aucun total_revenue négatif."""
    df = compute_kpi_revenue_by_segment(duckdb_conn)
    assert (df["total_revenue"] >= 0).all()


def test_kpi_revenue_by_segment_sorted(duckdb_conn):
    """KPI 2 : tri décroissant par total_revenue."""
    df = compute_kpi_revenue_by_segment(duckdb_conn)
    if len(df) > 1:
        assert df["total_revenue"].is_monotonic_decreasing


# ---------------------------------------------------------------------------
# KPI 3 — avg_basket
# ---------------------------------------------------------------------------

def test_kpi_avg_basket_structure(duckdb_conn):
    """KPI 3 : une ligne par client, colonnes attendues."""
    df = compute_kpi_avg_basket(duckdb_conn)
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    for col in ("customer_key", "nb_orders", "total_revenue", "avg_basket",
                "first_order_date", "last_order_date", "active_days"):
        assert col in df.columns, f"Colonne manquante : {col}"


def test_kpi_avg_basket_unique_customers(duckdb_conn):
    """KPI 3 : pas de doublon par customer_key."""
    df = compute_kpi_avg_basket(duckdb_conn)
    assert df["customer_key"].nunique() == len(df)


def test_kpi_avg_basket_positive_revenue(duckdb_conn):
    """KPI 3 : total_revenue >= 0 et avg_basket > 0."""
    df = compute_kpi_avg_basket(duckdb_conn)
    assert (df["total_revenue"] >= 0).all()
    assert (df["avg_basket"] > 0).all()


def test_kpi_avg_basket_active_days(duckdb_conn):
    """KPI 3 : active_days >= 0 (un seul achat = 0 jour)."""
    df = compute_kpi_avg_basket(duckdb_conn)
    assert (df["active_days"] >= 0).all()


# ---------------------------------------------------------------------------
# KPI 4 — top_products
# ---------------------------------------------------------------------------

def test_kpi_top_products_structure(duckdb_conn):
    """KPI 4 : colonnes attendues, revenue_rank commence à 1."""
    df = compute_kpi_top_products(duckdb_conn)
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    for col in ("product_key", "product_name", "category", "total_revenue",
                "nb_orders", "revenue_rank", "volume_rank"):
        assert col in df.columns, f"Colonne manquante : {col}"
    assert df["revenue_rank"].min() == 1


def test_kpi_top_products_no_duplicate_rank(duckdb_conn):
    """KPI 4 : revenue_rank sans doublon (ROW_NUMBER garantit l'unicité)."""
    df = compute_kpi_top_products(duckdb_conn)
    assert df["revenue_rank"].nunique() == len(df)


def test_kpi_top_products_sorted_by_rank(duckdb_conn):
    """KPI 4 : tri par revenue_rank croissant."""
    df = compute_kpi_top_products(duckdb_conn)
    assert df["revenue_rank"].is_monotonic_increasing


# ---------------------------------------------------------------------------
# KPI 5 — crm_engagement
# ---------------------------------------------------------------------------

def test_kpi_crm_engagement_structure(duckdb_conn):
    """KPI 5 : colonnes channel, country, nb_interactions présentes."""
    df = compute_kpi_crm_engagement(duckdb_conn)
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    for col in ("channel", "country", "nb_interactions", "nb_customers",
                "avg_interactions_per_customer", "resolved_rate_pct"):
        assert col in df.columns, f"Colonne manquante : {col}"


def test_kpi_crm_engagement_resolved_rate_range(duckdb_conn):
    """KPI 5 : resolved_rate_pct entre 0 et 100."""
    df = compute_kpi_crm_engagement(duckdb_conn)
    assert (df["resolved_rate_pct"] >= 0).all()
    assert (df["resolved_rate_pct"] <= 100).all()


def test_kpi_crm_engagement_avg_interactions_positive(duckdb_conn):
    """KPI 5 : avg_interactions_per_customer > 0."""
    df = compute_kpi_crm_engagement(duckdb_conn)
    assert (df["avg_interactions_per_customer"] > 0).all()


# ---------------------------------------------------------------------------
# Orchestrateur complet
# ---------------------------------------------------------------------------

def test_run_gold_aggregations_produces_files(tmp_silver, tmp_gold):
    """run_gold_aggregations() produit exactement 5 fichiers Parquet dans gold_dir."""
    stats = run_gold_aggregations(silver_dir=tmp_silver, gold_dir=tmp_gold)
    assert len(stats) == 5, f"Attendu 5 KPI, obtenu {len(stats)}"
    expected = {
        "kpi_revenue_by_period",
        "kpi_revenue_by_segment",
        "kpi_avg_basket",
        "kpi_top_products",
        "kpi_crm_engagement",
    }
    assert set(stats.keys()) == expected
    for kpi_name in expected:
        parquet_path = tmp_gold / f"{kpi_name}.parquet"
        assert parquet_path.exists(), f"Fichier manquant : {parquet_path}"
        assert parquet_path.stat().st_size > 0, f"Fichier vide : {parquet_path}"


def test_run_gold_aggregations_row_counts(tmp_silver, tmp_gold):
    """run_gold_aggregations() retourne des nb_lignes > 0 pour chaque KPI."""
    stats = run_gold_aggregations(silver_dir=tmp_silver, gold_dir=tmp_gold)
    for kpi_name, nb_rows in stats.items():
        assert nb_rows > 0, f"{kpi_name} : 0 lignes produits"
