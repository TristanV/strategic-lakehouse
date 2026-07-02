"""
Tests pytest — Orchestrateur pipeline (src/pipeline.py).

Couverture :
  - test_pipeline_bronze_only     : --layer bronze produit des Parquet Bronze
  - test_pipeline_silver_only     : --layer silver produit des Parquet Silver
  - test_pipeline_gold_only       : --layer gold produit des Parquet Gold
  - test_pipeline_all             : --layer all exécute les 3 couches en séquence
  - test_pipeline_invalid_layer   : ValueError sur layer invalide
  - test_pipeline_returns_stats   : résultat dict avec nb_lignes > 0
  - test_pipeline_idempotent      : deux exécutions all → même nb de lignes

Note : les couches Silver et Gold dépendent de la présence de Parquet amont.
Les fixtures construisent la chaîne complète Bronze→Silver→Gold en temp.

Auteur : Tristan Vanrullen — 2026
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from src.pipeline import run_pipeline


# ---------------------------------------------------------------------------
# Données synthétiques (mêmes CSV que test_silver.py)
# ---------------------------------------------------------------------------

CSV_PRODUCTS = """product_id,product_name,category_id,category,unit_price,cost_price
1,Widget A,10,Electronics,99.99,60.00
2,Gadget B,10,Electronics,149.99,80.00
3,Tool C,20,Hardware,49.99,30.00
"""

CSV_CUSTOMERS = """customer_id,customer_name,email,phone,age,loyalty_score,country
101,Alice Dupont,alice@example.com,+33600000001,32,85,France
102,Bob Martin,bob@example.com,+33600000002,45,72,Germany
"""

CSV_FACT_SALES = """sale_id,customer_id,product_id,sale_date,quantity,unit_price,total_amount,discount
1001,101,1,2023-01-15,2,99.99,199.98,0
1002,101,2,2023-02-20,1,149.99,149.99,5
1003,102,1,2023-03-10,3,99.99,299.97,0
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def raw_dir(tmp_path_factory) -> Path:
    """Crée data/raw/ synthétique avec les 3 CSV GlobalTrade."""
    root = tmp_path_factory.mktemp("raw")
    (root / "erp").mkdir()
    (root / "crm").mkdir()
    (root / "analytics").mkdir()
    (root / "erp" / "g_dim_products.csv").write_text(CSV_PRODUCTS, encoding="utf-8")
    (root / "erp" / "g_fact_sales.csv").write_text(CSV_FACT_SALES, encoding="utf-8")
    (root / "crm" / "g_dim_customers.csv").write_text(CSV_CUSTOMERS, encoding="utf-8")
    return root


@pytest.fixture(scope="module")
def bronze_dir(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("bronze")


@pytest.fixture(scope="module")
def silver_dir(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("silver")


@pytest.fixture(scope="module")
def gold_dir(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("gold")


@pytest.fixture(scope="module")
def pipeline_all_results(raw_dir, bronze_dir, silver_dir, gold_dir) -> dict:
    """Exécute run_pipeline(all) une seule fois pour tout le module."""
    return run_pipeline(
        layer="all",
        raw_dir=raw_dir,
        bronze_dir=bronze_dir,
        silver_dir=silver_dir,
        gold_dir=gold_dir,
    )


# ---------------------------------------------------------------------------
# Tests couche Bronze
# ---------------------------------------------------------------------------

def test_pipeline_bronze_only(raw_dir, tmp_path):
    """--layer bronze crée des Parquet Bronze dans bronze_dir."""
    bdir = tmp_path / "bronze"
    results = run_pipeline(
        layer="bronze",
        raw_dir=raw_dir,
        bronze_dir=bdir,
        silver_dir=tmp_path / "silver",
        gold_dir=tmp_path / "gold",
    )
    assert "bronze" in results
    assert len(results["bronze"]) >= 1
    parquets = list(bdir.rglob("*.parquet"))
    assert len(parquets) >= 1, "Aucun Parquet Bronze généré"


# ---------------------------------------------------------------------------
# Tests couche Silver
# ---------------------------------------------------------------------------

def test_pipeline_silver_only(bronze_dir, tmp_path):
    """--layer silver produit les 3 Parquet Silver."""
    # Bronze doit avoir été produit ; on le génère si le dossier est vide.
    if not list(bronze_dir.rglob("*.parquet")):
        raw = tmp_path / "raw"
        (raw / "erp").mkdir(parents=True)
        (raw / "crm").mkdir(parents=True)
        (raw / "analytics").mkdir(parents=True)
        (raw / "erp" / "g_dim_products.csv").write_text(CSV_PRODUCTS, encoding="utf-8")
        (raw / "erp" / "g_fact_sales.csv").write_text(CSV_FACT_SALES, encoding="utf-8")
        (raw / "crm" / "g_dim_customers.csv").write_text(CSV_CUSTOMERS, encoding="utf-8")
        run_pipeline(
            layer="bronze",
            raw_dir=raw,
            bronze_dir=bronze_dir,
            silver_dir=tmp_path / "silver_unused",
            gold_dir=tmp_path / "gold_unused",
        )

    sdir = tmp_path / "silver"
    results = run_pipeline(
        layer="silver",
        raw_dir=tmp_path / "raw",
        bronze_dir=bronze_dir,
        silver_dir=sdir,
        gold_dir=tmp_path / "gold",
    )
    assert "silver" in results
    for name in ("dim_products", "dim_customers", "fact_sales"):
        assert (sdir / f"{name}.parquet").exists(), f"{name}.parquet absent de Silver"


# ---------------------------------------------------------------------------
# Tests couche Gold
# ---------------------------------------------------------------------------

def test_pipeline_gold_only(silver_dir, tmp_path):
    """--layer gold produit au moins un Parquet Gold."""
    # Silver doit être peuplé ; on vérifie silencieusement.
    silver_parquets = list(silver_dir.rglob("*.parquet"))
    if not silver_parquets:
        pytest.skip("Silver vide — dépendance amont non satisfaite")

    gdir = tmp_path / "gold"
    results = run_pipeline(
        layer="gold",
        raw_dir=tmp_path / "raw",
        bronze_dir=tmp_path / "bronze",
        silver_dir=silver_dir,
        gold_dir=gdir,
    )
    assert "gold" in results
    assert len(list(gdir.rglob("*.parquet"))) >= 1, "Aucun Parquet Gold généré"


# ---------------------------------------------------------------------------
# Tests layer=all
# ---------------------------------------------------------------------------

def test_pipeline_all_runs_three_layers(pipeline_all_results):
    """--layer all retourne des stats pour bronze, silver et gold."""
    for layer in ("bronze", "silver", "gold"):
        assert layer in pipeline_all_results, f"Couche {layer} absente des résultats"
        assert len(pipeline_all_results[layer]) >= 1


def test_pipeline_all_returns_positive_row_counts(pipeline_all_results):
    """Chaque table de chaque couche contient au moins une ligne."""
    for layer_name, stats in pipeline_all_results.items():
        for table, nb in stats.items():
            assert nb > 0, f"{layer_name}/{table} : 0 lignes"


# ---------------------------------------------------------------------------
# Test layer invalide
# ---------------------------------------------------------------------------

def test_pipeline_invalid_layer(tmp_path):
    """Un layer invalide lève ValueError."""
    with pytest.raises(ValueError, match="invalide"):
        run_pipeline(
            layer="platinum",
            raw_dir=tmp_path,
            bronze_dir=tmp_path,
            silver_dir=tmp_path,
            gold_dir=tmp_path,
        )


# ---------------------------------------------------------------------------
# Test idempotence
# ---------------------------------------------------------------------------

def test_pipeline_idempotent(raw_dir, tmp_path):
    """Deux exécutions all sur les mêmes sources produisent les mêmes stats."""
    dirs1 = {"bronze_dir": tmp_path / "b1", "silver_dir": tmp_path / "s1", "gold_dir": tmp_path / "g1"}
    dirs2 = {"bronze_dir": tmp_path / "b2", "silver_dir": tmp_path / "s2", "gold_dir": tmp_path / "g2"}

    r1 = run_pipeline(layer="all", raw_dir=raw_dir, **dirs1)
    r2 = run_pipeline(layer="all", raw_dir=raw_dir, **dirs2)

    for layer in ("bronze", "silver", "gold"):
        assert r1[layer] == r2[layer], (
            f"Pipeline non idempotent sur couche {layer} : {r1[layer]} != {r2[layer]}"
        )
