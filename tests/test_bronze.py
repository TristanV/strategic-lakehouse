"""
Tests pytest — Couche Bronze (src/bronze/ingest.py).

Couverture :
  - test_ingest_creates_parquet      : les fichiers Parquet Bronze sont créés
  - test_ingest_metadata_columns     : colonnes techniques _ingested_at, _source_file,
                                       _source_silo, _run_id présentes
  - test_ingest_no_transformation    : toutes les colonnes métier sont en str
  - test_ingest_idempotent           : deux exécutions successives = même résultat
  - test_ingest_row_count_consistent : le nb de lignes Bronze = nb de lignes CSV source
  - test_ingest_missing_file_skipped : un fichier manquant est ignoré sans crash

Auteur : Tristan Vanrullen — 2026
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import pytest

from src.bronze.ingest import ingest_csv_to_bronze


# ---------------------------------------------------------------------------
# Fixture : raw_dir minimal
# Crée un data/raw/ synthétique avec les 3 CSV sources attendus.
# ---------------------------------------------------------------------------

CSV_PRODUCTS = """product_id,product_name,category,cost
1,Widget A,Electronics,60
2,Gadget B,Electronics,80
3,Tool C,Hardware,30
"""

CSV_CUSTOMERS = """customer_id,first_name,last_name,country
101,Alice,Dupont,France
102,Bob,Martin,Germany
"""

CSV_FACT_SALES = """order_number,customer_id,product_id,due_date,sales,quantity
ORD001,101,1,2023-01-15,200,2
ORD002,101,2,2023-02-20,150,1
ORD003,102,1,2023-03-10,300,3
"""


@pytest.fixture(scope="module")
def raw_dir(tmp_path_factory) -> Path:
    """Crée un répertoire raw/ synthétique avec les CSV sources."""
    raw = tmp_path_factory.mktemp("raw")
    (raw / "erp").mkdir()
    (raw / "crm").mkdir()
    (raw / "analytics").mkdir()
    (raw / "erp" / "g_dim_products.csv").write_text(CSV_PRODUCTS, encoding="utf-8")
    (raw / "erp" / "g_fact_sales.csv").write_text(CSV_FACT_SALES, encoding="utf-8")
    (raw / "crm" / "g_dim_customers.csv").write_text(CSV_CUSTOMERS, encoding="utf-8")
    return raw


@pytest.fixture(scope="module")
def bronze_dir(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("bronze")


@pytest.fixture(scope="module")
def ingest_stats(raw_dir, bronze_dir) -> dict:
    """Exécute l'ingestion une fois et retourne les stats."""
    return ingest_csv_to_bronze(raw_dir=raw_dir, bronze_dir=bronze_dir)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_ingest_creates_parquet_files(ingest_stats, bronze_dir):
    """Les fichiers Parquet attendus sont créés dans bronze/."""
    expected = [
        bronze_dir / "erp" / "g_dim_products.parquet",
        bronze_dir / "erp" / "g_fact_sales.parquet",
        bronze_dir / "crm" / "g_dim_customers.parquet",
    ]
    for path in expected:
        assert path.exists(), f"Fichier Parquet manquant : {path}"
        assert path.stat().st_size > 0


def test_ingest_returns_stats(ingest_stats):
    """ingest_csv_to_bronze() retourne un dict non vide avec les nb de lignes."""
    assert isinstance(ingest_stats, dict)
    assert len(ingest_stats) >= 3
    for table, nb_rows in ingest_stats.items():
        assert nb_rows > 0, f"{table} : 0 lignes ingérées"


def test_ingest_metadata_columns(ingest_stats, bronze_dir):
    """Colonnes techniques d'ingération présentes dans chaque Parquet Bronze."""
    expected_meta = {"_ingested_at", "_source_file", "_source_silo", "_run_id"}
    for silo_folder in ("erp", "crm"):
        for parquet_path in (bronze_dir / silo_folder).glob("*.parquet"):
            df = pd.read_parquet(parquet_path)
            missing = expected_meta - set(df.columns)
            assert not missing, f"{parquet_path.name} : colonnes méta manquantes : {missing}"


def test_ingest_all_columns_string_type(ingest_stats, bronze_dir):
    """
    Bronze = aucune transformation métier.
    Toutes les colonnes métier (hors métadonnées) doivent être en dtype object (str).
    """
    meta_cols = {"_ingested_at", "_source_file", "_source_silo", "_run_id"}
    for silo_folder in ("erp", "crm"):
        for parquet_path in (bronze_dir / silo_folder).glob("*.parquet"):
            df = pd.read_parquet(parquet_path)
            biz_cols = [c for c in df.columns if c not in meta_cols]
            non_str = [
                c for c in biz_cols
                if str(df[c].dtype) not in ("object", "string")
            ]
            assert not non_str, (
                f"{parquet_path.name} : colonnes métier non-str (Bronze ne doit pas typer) : {non_str}"
            )


def test_ingest_idempotent(raw_dir, bronze_dir):
    """Deux ingéstions successives produisent le même nb de lignes (overwrite)."""
    stats1 = ingest_csv_to_bronze(raw_dir=raw_dir, bronze_dir=bronze_dir)
    stats2 = ingest_csv_to_bronze(raw_dir=raw_dir, bronze_dir=bronze_dir)
    assert stats1 == stats2, "Ingéstion non idempotente : nb de lignes différents"


def test_ingest_row_count_matches_csv(raw_dir, bronze_dir):
    """Le nb de lignes Bronze == nb de lignes CSV source (sans l'entête)."""
    stats = ingest_csv_to_bronze(raw_dir=raw_dir, bronze_dir=bronze_dir)
    csv_path = raw_dir / "erp" / "g_fact_sales.csv"
    expected_rows = len(pd.read_csv(csv_path, dtype=str))
    assert stats.get("g_fact_sales") == expected_rows


def test_ingest_missing_file_skipped(bronze_dir, tmp_path):
    """Un répertoire raw sans certains fichiers n'arrête pas l'ingéstion."""
    partial_raw = tmp_path / "partial_raw"
    (partial_raw / "erp").mkdir(parents=True)
    (partial_raw / "crm").mkdir()
    (partial_raw / "analytics").mkdir()
    # Seulement g_dim_products.csv, les autres sont manquants
    (partial_raw / "erp" / "g_dim_products.csv").write_text(CSV_PRODUCTS, encoding="utf-8")
    partial_bronze = tmp_path / "partial_bronze"
    partial_bronze.mkdir()
    # Ne doit pas lever d'exception
    stats = ingest_csv_to_bronze(raw_dir=partial_raw, bronze_dir=partial_bronze)
    assert "g_dim_products" in stats
    assert stats["g_dim_products"] == 3
