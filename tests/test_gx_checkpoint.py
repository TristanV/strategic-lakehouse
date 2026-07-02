"""Tests pytest — Great Expectations checkpoint Silver.

Couvre :
  - run_gx_checkpoint sur Silver synthétique minimal (happy path)
  - Chaque expectation unitairement sur un DataFrame de test
  - Rapport HTML généré et non-vide
  - RuntimeError levée en cas d'échec d'expectation
  - Tolérance Silver absent (warning, pas d'erreur)

Auteur : Tristan Vanrullen — 2026
"""

from __future__ import annotations

import pandas as pd
import pytest
from pathlib import Path

from src.quality.gx_checkpoint import (
    _build_fact_sales_suite,
    _build_dim_products_suite,
    _run_suite,
    run_gx_checkpoint,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def minimal_fact_sales() -> pd.DataFrame:
    """DataFrame fact_sales minimal qui passe toutes les expectations."""
    return pd.DataFrame({
        "sale_id": [1, 2, 3],
        "customer_id": [10, 11, 12],
        "product_id": [100, 101, 102],
        "quantity": [1.0, 2.0, 3.0],
        "total_amount": [9.99, 49.99, 15.0],
        "_source_silo": ["ERP_ONPREMISE"] * 3,
        "_silver_processed_at": ["2026-07-02T00:00:00Z"] * 3,
    })


@pytest.fixture()
def minimal_dim_products() -> pd.DataFrame:
    """DataFrame dim_products minimal qui passe toutes les expectations."""
    return pd.DataFrame({
        "product_id": [100, 101, 102],
        "product_name": ["Alpha", "Beta", "Gamma"],
        "unit_price": [9.99, 24.99, 5.0],
        "_source_silo": ["ERP_ONPREMISE"] * 3,
        "_silver_processed_at": ["2026-07-02T00:00:00Z"] * 3,
    })


@pytest.fixture()
def silver_dir(tmp_path, minimal_fact_sales, minimal_dim_products) -> Path:
    """Silver temporaire avec les deux Parquet."""
    (tmp_path / "fact_sales.parquet").parent.mkdir(parents=True, exist_ok=True)
    minimal_fact_sales.to_parquet(tmp_path / "fact_sales.parquet", index=False)
    minimal_dim_products.to_parquet(tmp_path / "dim_products.parquet", index=False)
    return tmp_path


@pytest.fixture()
def report_dir(tmp_path) -> Path:
    d = tmp_path / "reports" / "gx"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGxCheckpointHappyPath:
    """Checkpoint complet sur Silver synthétique minimal."""

    def test_checkpoint_runs_without_error(self, silver_dir, report_dir):
        results = run_gx_checkpoint(silver_dir, report_dir)
        assert "fact_sales" in results
        assert "dim_products" in results

    def test_all_expectations_pass(self, silver_dir, report_dir):
        results = run_gx_checkpoint(silver_dir, report_dir)
        for table, r in results.items():
            assert r["failed"] == 0, (
                f"{table}: {r['failed']} expectation(s) échouée(s) : {r['failures']}"
            )

    def test_html_reports_generated(self, silver_dir, report_dir):
        run_gx_checkpoint(silver_dir, report_dir)
        html_files = list(report_dir.glob("*.html"))
        assert len(html_files) >= 2, "Deux rapports HTML attendus (fact_sales + dim_products)"
        for f in html_files:
            assert f.stat().st_size > 500, f"Rapport HTML vide ou trop petit : {f}"

    def test_html_report_contains_passed_badge(self, silver_dir, report_dir):
        run_gx_checkpoint(silver_dir, report_dir)
        html_files = list(report_dir.glob("*.html"))
        for f in html_files:
            content = f.read_text(encoding="utf-8")
            assert "passed" in content
            assert "✅" in content


class TestGxExpectationsUnitaires:
    """Chaque expectation testée séparément."""

    def test_fact_sales_suite_has_expected_rules(self):
        suite = _build_fact_sales_suite()
        types = [r["expectation_type"] for r in suite]
        assert "expect_column_values_to_not_be_null" in types
        assert "expect_column_values_to_be_unique" in types
        assert "expect_column_values_to_be_between" in types
        assert "expect_table_row_count_to_be_between" in types

    def test_dim_products_suite_has_expected_rules(self):
        suite = _build_dim_products_suite()
        cols_checked = [r["kwargs"].get("column") for r in suite]
        assert "product_id" in cols_checked
        assert "unit_price" in cols_checked
        assert "product_name" in cols_checked

    def test_fact_sales_total_amount_must_be_positive(
        self, minimal_fact_sales, report_dir
    ):
        """Injecte une ligne avec total_amount=0 — doit échouer."""
        bad_df = minimal_fact_sales.copy()
        bad_df.loc[0, "total_amount"] = 0.0
        suite = _build_fact_sales_suite()
        result = _run_suite(bad_df, suite, "fact_sales_bad", report_dir)
        failed_names = [f["expectation"] for f in result["failures"]]
        assert "expect_column_values_to_be_between" in failed_names

    def test_fact_sales_duplicate_sale_id_fails(
        self, minimal_fact_sales, report_dir
    ):
        """Injecte un doublon sur sale_id — expect_unique doit échouer."""
        bad_df = minimal_fact_sales.copy()
        bad_df.loc[1, "sale_id"] = bad_df.loc[0, "sale_id"]
        suite = _build_fact_sales_suite()
        result = _run_suite(bad_df, suite, "fact_sales_dup", report_dir)
        failed_names = [f["expectation"] for f in result["failures"]]
        assert "expect_column_values_to_be_unique" in failed_names

    def test_dim_products_null_product_id_fails(
        self, minimal_dim_products, report_dir
    ):
        """product_id null doit faire échouer l'expectation not_be_null."""
        bad_df = minimal_dim_products.copy()
        bad_df.loc[0, "product_id"] = None
        suite = _build_dim_products_suite()
        result = _run_suite(bad_df, suite, "dim_products_null", report_dir)
        failed_names = [f["expectation"] for f in result["failures"]]
        assert "expect_column_values_to_not_be_null" in failed_names


class TestGxEdgeCases:
    """Cas limites et dégradations."""

    def test_missing_silver_table_is_tolerated(self, tmp_path, report_dir):
        """Silver dir vide → pas de RuntimeError, résultat dict vide."""
        results = run_gx_checkpoint(tmp_path, report_dir)
        assert results == {}, "Aucun Parquet présent → dict vide attendu"

    def test_runtime_error_raised_on_failure(self, report_dir, minimal_fact_sales, tmp_path):
        """Silver avec total_amount=0 → RuntimeError levée par run_gx_checkpoint."""
        bad_df = minimal_fact_sales.copy()
        bad_df["total_amount"] = 0.0  # toutes les lignes invalides
        silver_dir = tmp_path / "silver_bad"
        silver_dir.mkdir()
        bad_df.to_parquet(silver_dir / "fact_sales.parquet", index=False)
        with pytest.raises(RuntimeError, match="expectation"):
            run_gx_checkpoint(silver_dir, report_dir)
