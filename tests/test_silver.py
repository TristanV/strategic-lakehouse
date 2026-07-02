"""
Tests pytest — Couche Silver (src/silver/transform.py).

Couverture :
  - test_silver_creates_parquet          : les 3 Parquet Silver sont créés
  - test_silver_returns_stats            : run_silver_transformations() retourne un dict non vide
  - test_dim_products_typing             : product_id Int64, unit_price/cost_price float64
  - test_dim_customers_typing            : customer_id Int64, age/loyalty_score Int64
  - test_fact_sales_typing               : sale_id/customer_id/product_id Int64,
                                           quantity/total_amount float64, sale_date datetime
  - test_pii_pseudonymised               : customer_name/email/phone ≠ valeurs sources
  - test_no_duplicates_products          : product_id unique dans dim_products
  - test_no_duplicates_customers         : customer_id unique dans dim_customers
  - test_no_duplicates_sales             : sale_id unique dans fact_sales
  - test_silver_lineage_columns          : _source_silo, _run_id, _silver_processed_at présents (×3)
  - test_referential_integrity_products  : tout product_id de fact_sales ∈ dim_products
  - test_referential_integrity_customers : tout customer_id de fact_sales ∈ dim_customers
  - test_silver_idempotent               : deux exécutions = même nb de lignes
  - test_no_null_primary_keys            : clés métier non nulles (dim_products, dim_customers)
  - test_total_amount_positive           : total_amount > 0 pour toutes les lignes fact_sales

Note sur les dtypes Silver :
  Le Silver applique pd.to_numeric(...).astype("Int64") ou astype("float64").
  Les assertions vérifient les types Pandas attendus après transformation.

Auteur : Tristan Vanrullen — 2026
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from src.silver.transform import (
    run_silver_transformations,
    transform_dim_customers,
    transform_dim_products,
    transform_fact_sales,
)


# ---------------------------------------------------------------------------
# CSV sources synthétiques (colonnes réelles du dataset GlobalTrade)
# ---------------------------------------------------------------------------

CSV_PRODUCTS = """product_id,product_name,category_id,category,unit_price,cost_price
1,Widget A,10,Electronics,99.99,60.00
2,Gadget B,10,Electronics,149.99,80.00
3,Tool C,20,Hardware,49.99,30.00
2,Gadget B Duplicate,10,Electronics,149.99,80.00
"""

CSV_CUSTOMERS = """customer_id,customer_name,email,phone,age,loyalty_score,country
101,Alice Dupont,alice@example.com,+33600000001,32,85,France
102,Bob Martin,bob@example.com,+33600000002,45,72,Germany
101,Alice Dupont Dup,alice@example.com,+33600000001,32,90,France
"""

CSV_FACT_SALES = """sale_id,customer_id,product_id,sale_date,quantity,unit_price,total_amount,discount
1001,101,1,2023-01-15,2,99.99,199.98,0
1002,101,2,2023-02-20,1,149.99,149.99,5
1003,102,1,2023-03-10,3,99.99,299.97,0
1003,102,1,2023-03-10,3,99.99,299.97,0
"""

# Valeurs PII sources (avant pseudonymisation) — utilisées pour vérifier leur absence
_PII_SOURCE = {
    "customer_name": ["Alice Dupont", "Bob Martin", "Alice Dupont Dup"],
    "email": ["alice@example.com", "bob@example.com"],
    "phone": ["+33600000001", "+33600000002"],
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def bronze_dir(tmp_path_factory) -> Path:
    """
    Crée un bronze/ synthétique avec les 3 Parquet sources du dataset GlobalTrade.
    Simule l'ingestion Bronze en écrivant directement les Parquet avec métadonnées.
    """
    root = tmp_path_factory.mktemp("bronze_silver")
    (root / "erp").mkdir()
    (root / "crm").mkdir()
    (root / "analytics").mkdir()

    meta_erp = {
        "_ingested_at": datetime.now(timezone.utc).isoformat(),
        "_source_file": "synthetic",
        "_source_silo": "ERP_ONPREMISE",
        "_run_id": str(uuid.uuid4()),
    }
    meta_crm = dict(meta_erp, _source_silo="CRM_SAAS")

    # dim_products Bronze
    df_prod = pd.read_csv(pd.io.common.StringIO(CSV_PRODUCTS), dtype=str)
    for k, v in meta_erp.items():
        df_prod[k] = v
    df_prod.to_parquet(root / "erp" / "g_dim_products.parquet", index=False)

    # fact_sales Bronze
    df_sales = pd.read_csv(pd.io.common.StringIO(CSV_FACT_SALES), dtype=str)
    for k, v in meta_erp.items():
        df_sales[k] = v
    df_sales["_source_file"] = "g_fact_sales.csv"
    df_sales.to_parquet(root / "erp" / "g_fact_sales.parquet", index=False)

    # dim_customers Bronze
    df_cust = pd.read_csv(pd.io.common.StringIO(CSV_CUSTOMERS), dtype=str)
    for k, v in meta_crm.items():
        df_cust[k] = v
    df_cust.to_parquet(root / "crm" / "g_dim_customers.parquet", index=False)

    return root


@pytest.fixture(scope="module")
def silver_dir(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("silver_out")


@pytest.fixture(scope="module")
def silver_stats(bronze_dir, silver_dir) -> dict:
    """Exécute run_silver_transformations() une seule fois pour le module."""
    return run_silver_transformations(bronze_dir=bronze_dir, silver_dir=silver_dir)


@pytest.fixture(scope="module")
def df_products(bronze_dir) -> pd.DataFrame:
    return transform_dim_products(bronze_dir)


@pytest.fixture(scope="module")
def df_customers(bronze_dir) -> pd.DataFrame:
    return transform_dim_customers(bronze_dir)


@pytest.fixture(scope="module")
def df_sales(bronze_dir) -> pd.DataFrame:
    return transform_fact_sales(bronze_dir)


# ---------------------------------------------------------------------------
# Tests généraux
# ---------------------------------------------------------------------------

def test_silver_creates_parquet(silver_stats, silver_dir):
    """Les Parquet Silver attendus sont créés et non vides."""
    for name in ("dim_products", "dim_customers", "fact_sales"):
        path = silver_dir / f"{name}.parquet"
        assert path.exists(), f"Parquet Silver manquant : {path}"
        assert path.stat().st_size > 0


def test_silver_returns_stats(silver_stats):
    """run_silver_transformations() retourne un dict avec nb lignes > 0 par table."""
    assert isinstance(silver_stats, dict)
    assert len(silver_stats) >= 3
    for table, nb in silver_stats.items():
        assert nb > 0, f"{table} : 0 lignes en Silver"


# ---------------------------------------------------------------------------
# Typage des colonnes
# ---------------------------------------------------------------------------

def test_dim_products_typing(df_products):
    """dim_products Silver : product_id → Int64, unit_price/cost_price → float64."""
    assert str(df_products["product_id"].dtype) == "Int64", (
        f"product_id dtype attendu Int64, obtenu {df_products['product_id'].dtype}"
    )
    for col in ("unit_price", "cost_price"):
        if col in df_products.columns:
            assert df_products[col].dtype == "float64", (
                f"{col} dtype attendu float64, obtenu {df_products[col].dtype}"
            )


def test_dim_customers_typing(df_customers):
    """dim_customers Silver : customer_id → Int64, age/loyalty_score → Int64."""
    assert str(df_customers["customer_id"].dtype) == "Int64"
    for col in ("age", "loyalty_score"):
        if col in df_customers.columns:
            assert str(df_customers[col].dtype) == "Int64", (
                f"{col} dtype attendu Int64, obtenu {df_customers[col].dtype}"
            )


def test_fact_sales_typing(df_sales):
    """
    fact_sales Silver :
      sale_id / customer_id / product_id → Int64
      quantity / unit_price / total_amount → float64
      sale_date → datetime64
    """
    for col in ("sale_id", "customer_id", "product_id"):
        if col in df_sales.columns:
            assert str(df_sales[col].dtype) == "Int64", (
                f"{col} dtype attendu Int64, obtenu {df_sales[col].dtype}"
            )
    for col in ("quantity", "unit_price", "total_amount"):
        if col in df_sales.columns:
            assert df_sales[col].dtype == "float64", (
                f"{col} dtype attendu float64, obtenu {df_sales[col].dtype}"
            )
    if "sale_date" in df_sales.columns:
        assert pd.api.types.is_datetime64_any_dtype(df_sales["sale_date"]), (
            f"sale_date dtype attendu datetime, obtenu {df_sales['sale_date'].dtype}"
        )


# ---------------------------------------------------------------------------
# Pseudonymisation PII
# ---------------------------------------------------------------------------

def test_pii_pseudonymised(df_customers):
    """
    customer_name, email, phone ne doivent plus contenir les valeurs
    sources en clair après pseudonymisation SHA-256.
    """
    for pii_col, raw_values in _PII_SOURCE.items():
        if pii_col not in df_customers.columns:
            continue
        silver_values = set(df_customers[pii_col].dropna().tolist())
        for raw in raw_values:
            assert raw not in silver_values, (
                f"{pii_col} : valeur PII en clair détectée en Silver : '{raw}'"
            )


# ---------------------------------------------------------------------------
# Dédoublonnage
# ---------------------------------------------------------------------------

def test_no_duplicates_products(df_products):
    """dim_products Silver : product_id unique (dédup sur clé métier)."""
    dupes = df_products[df_products.duplicated(subset=["product_id"], keep=False)]
    assert len(dupes) == 0, f"{len(dupes)} doublons sur product_id en Silver"


def test_no_duplicates_customers(df_customers):
    """dim_customers Silver : customer_id unique."""
    dupes = df_customers[df_customers.duplicated(subset=["customer_id"], keep=False)]
    assert len(dupes) == 0, f"{len(dupes)} doublons sur customer_id en Silver"


def test_no_duplicates_sales(df_sales):
    """fact_sales Silver : sale_id unique."""
    if "sale_id" not in df_sales.columns:
        pytest.skip("sale_id absent de fact_sales")
    dupes = df_sales[df_sales.duplicated(subset=["sale_id"], keep=False)]
    assert len(dupes) == 0, f"{len(dupes)} doublons sur sale_id en Silver"


# ---------------------------------------------------------------------------
# Colonnes de linéage Silver
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("df_fixture", ["df_products", "df_customers", "df_sales"])
def test_silver_lineage_columns(df_fixture, request):
    """_source_silo, _run_id et _silver_processed_at présents dans chaque Silver."""
    df = request.getfixturevalue(df_fixture)
    for col in ("_source_silo", "_run_id", "_silver_processed_at"):
        assert col in df.columns, f"{col} absent de {df_fixture}"
        assert df[col].notna().any(), f"{col} complètement null dans {df_fixture}"


# ---------------------------------------------------------------------------
# Intégrité référentielle
# ---------------------------------------------------------------------------

def test_referential_integrity_product_ids(df_sales, df_products):
    """
    Tout product_id de fact_sales doit exister dans dim_products.
    Garantit que la jointure Gold ne produit pas de NaN silencieux.
    """
    if "product_id" not in df_sales.columns or "product_id" not in df_products.columns:
        pytest.skip("product_id absent")
    sales_ids = set(df_sales["product_id"].dropna().tolist())
    product_ids = set(df_products["product_id"].dropna().tolist())
    orphans = sales_ids - product_ids
    assert not orphans, (
        f"fact_sales contient des product_id orphelins (absent de dim_products) : {orphans}"
    )


def test_referential_integrity_customer_ids(df_sales, df_customers):
    """Tout customer_id de fact_sales doit exister dans dim_customers."""
    if "customer_id" not in df_sales.columns or "customer_id" not in df_customers.columns:
        pytest.skip("customer_id absent")
    sales_cust = set(df_sales["customer_id"].dropna().tolist())
    cust_ids = set(df_customers["customer_id"].dropna().tolist())
    orphans = sales_cust - cust_ids
    assert not orphans, (
        f"fact_sales contient des customer_id orphelins (absent de dim_customers) : {orphans}"
    )


# ---------------------------------------------------------------------------
# Idempotence
# ---------------------------------------------------------------------------

def test_silver_idempotent(bronze_dir, tmp_path):
    """Deux exécutions successives de run_silver_transformations() = même nb de lignes."""
    stats1 = run_silver_transformations(bronze_dir=bronze_dir, silver_dir=tmp_path / "s1")
    stats2 = run_silver_transformations(bronze_dir=bronze_dir, silver_dir=tmp_path / "s2")
    assert stats1 == stats2, f"Silver non idempotent : {stats1} != {stats2}"


# ---------------------------------------------------------------------------
# Clés métier non nulles
# ---------------------------------------------------------------------------

def test_no_null_primary_keys(df_products, df_customers):
    """
    Les clés métier principales ne doivent pas contenir de NULL en Silver.
    Les lignes avec clé nulle sont censées avoir été rejetées lors du transform.
    """
    for df, key_col in ((df_products, "product_id"), (df_customers, "customer_id")):
        if key_col not in df.columns:
            continue
        null_count = df[key_col].isna().sum()
        assert null_count == 0, (
            f"{key_col} : {null_count} valeurs nulles en Silver (clé métier obligatoire)"
        )


# ---------------------------------------------------------------------------
# Règles métier — qualité des montants
# ---------------------------------------------------------------------------

def test_total_amount_positive(df_sales):
    """
    fact_sales Silver : total_amount doit être strictement positif (> 0)
    pour toutes les lignes non nulles.

    Règle métier : une vente avec montant nul ou négatif est une anomalie
    qui doit être rejetée ou corrigée avant Silver.
    """
    if "total_amount" not in df_sales.columns:
        pytest.skip("total_amount absent de fact_sales")

    non_positive = df_sales[
        df_sales["total_amount"].notna() & (df_sales["total_amount"] <= 0)
    ]
    assert len(non_positive) == 0, (
        f"fact_sales : {len(non_positive)} ligne(s) avec total_amount ≤ 0 :\n"
        f"{non_positive[['sale_id', 'total_amount']].to_string(index=False)}"
    )
