"""
Configuration pytest — Strategic Lakehouse.

Fournit des fixtures partagées pour les tests Gold, API et Bronze :
  - silver_dir  : répertoire Silver réel du projet (si données présentes)
  - gold_dir    : répertoire Gold réel du projet
  - tmp_silver  : Silver synthtique en tmp (tests unitaires sans fichiers réels)
  - tmp_gold    : Gold vide dans tmp
  - duckdb_conn : connexion DuckDB avec vues Silver synthétiques injectées

Auteur : Tristan Vanrullen — 2026
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Chemins projet
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SILVER_DIR   = PROJECT_ROOT / "data" / "silver"
GOLD_DIR     = PROJECT_ROOT / "data" / "gold"


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def silver_dir() -> Path:
    return SILVER_DIR


@pytest.fixture(scope="session")
def gold_dir() -> Path:
    return GOLD_DIR


# ---------------------------------------------------------------------------
# Données synthétiques minimales (tests unitaires sans accès disque réel)
# ---------------------------------------------------------------------------

FACT_SALES_DATA = {
    "customer_key": ["C001", "C001", "C002", "C003", "C003"],
    "product_key":  ["P001", "P002", "P001", "P003", "P002"],
    "order_number": ["ORD001", "ORD002", "ORD003", "ORD004", "ORD005"],
    "due_date":     ["2023-01-15", "2023-02-20", "2023-01-25", "2023-03-10", "2023-03-15"],
    "order_date":   ["2023-01-10", "2023-02-15", "2023-01-20", "2023-03-05", "2023-03-10"],
    "quantity":     [2, 1, 3, 1, 2],
    "sales":        [200.0, 150.0, 300.0, 50.0, 180.0],
    "price":        [100.0, 150.0, 100.0, 50.0, 90.0],
    "shipping_date":["2023-01-17", "2023-02-22", "2023-01-27", "2023-03-12", "2023-03-17"],
    "_source_silo":        ["ERP"] * 5,
    "_silver_processed_at":["2026-07-01T10:00:00"] * 5,
    "_run_id":             ["TEST"] * 5,
}

DIM_CUSTOMERS_DATA = {
    "customer_key":  ["C001", "C002", "C003"],
    "customer_id":   [1, 2, 3],
    "first_name":    ["Alice", "Bob", "Carla"],
    "last_name":     ["Dupont", "Martin", "Rossi"],
    "country":       ["France", "Germany", "France"],
    "marital_status":["Single", "Married", "Married"],
    "gender":        ["F", "M", "F"],
    "birth_date":    ["1985-03-12", "1979-07-04", "1992-11-20"],
    "_source_silo":        ["CRM"] * 3,
    "_silver_processed_at":["2026-07-01T10:00:00"] * 3,
    "_run_id":             ["TEST"] * 3,
}

DIM_PRODUCTS_DATA = {
    "product_key":  ["P001", "P002", "P003"],
    "product_id":   [1, 2, 3],
    "product_name": ["Widget A", "Gadget B", "Tool C"],
    "category":     ["Electronics", "Electronics", "Hardware"],
    "sub_category": ["Sensors", "Displays", "Tools"],
    "cost":         [60.0, 80.0, 30.0],
    "start_date":   ["2020-01-01", "2020-06-01", "2021-03-01"],
    "_source_silo":        ["ERP"] * 3,
    "_silver_processed_at":["2026-07-01T10:00:00"] * 3,
    "_run_id":             ["TEST"] * 3,
}

CRM_INTERACTIONS_DATA = {
    "interaction_id":   ["I001", "I002", "I003", "I004", "I005"],
    "customer_id":      [1, 1, 2, 3, 3],
    "interaction_date": ["2023-02-01", "2023-03-15", "2023-01-10", "2023-02-20", "2023-04-05"],
    "channel":          ["email", "phone", "chat", "email", "in_store"],
    "interaction_type": ["complaint", "inquiry", "support", "feedback", "complaint"],
    "resolution_status":["resolved", "pending", "resolved", "resolved", "escalated"],
    "agent_id":         ["AGT001", "AGT002", "AGT001", "AGT003", "AGT002"],
    "duration_minutes": ["15", "30", "", "10", "45"],
    "satisfaction_score":["4", "", "5", "3", "2"],
    "notes":            ["OK", "", "Issue fixed", "Thanks", "Escalated"],
    "_source_silo":        ["CRM"] * 5,
    "_silver_processed_at":["2026-07-01T10:00:00"] * 5,
    "_run_id":             ["TEST"] * 5,
}


@pytest.fixture(scope="session")
def tmp_silver(tmp_path_factory) -> Path:
    """Crée un répertoire Silver temporaire avec les 4 Parquet synthétiques."""
    silver = tmp_path_factory.mktemp("silver")
    pd.DataFrame(FACT_SALES_DATA).to_parquet(silver / "fact_sales.parquet", index=False)
    pd.DataFrame(DIM_CUSTOMERS_DATA).to_parquet(silver / "dim_customers.parquet", index=False)
    pd.DataFrame(DIM_PRODUCTS_DATA).to_parquet(silver / "dim_products.parquet", index=False)
    pd.DataFrame(CRM_INTERACTIONS_DATA).to_parquet(silver / "crm_interactions.parquet", index=False)
    return silver


@pytest.fixture(scope="session")
def tmp_gold(tmp_path_factory) -> Path:
    """Crée un répertoire Gold temporaire vide."""
    return tmp_path_factory.mktemp("gold")


@pytest.fixture(scope="session")
def duckdb_conn(tmp_silver: Path) -> duckdb.DuckDBPyConnection:
    """Connexion DuckDB in-memory avec les 4 vues Silver synthétiques injectées."""
    conn = duckdb.connect()
    for table, filename in [
        ("fact_sales",       "fact_sales.parquet"),
        ("dim_customers",    "dim_customers.parquet"),
        ("dim_products",     "dim_products.parquet"),
        ("crm_interactions", "crm_interactions.parquet"),
    ]:
        path = tmp_silver / filename
        conn.execute(f"CREATE VIEW {table} AS SELECT * FROM read_parquet('{path}')")
    yield conn
    conn.close()
