"""Great Expectations — Checkpoint Silver.

Exécute une suite d'expectations sur les Parquet Silver :
  - fact_sales   : total_amount > 0, quantity >= 1, sale_id non-null + unique,
                   customer_id / product_id non-null
  - dim_products : unit_price > 0, product_id non-null + unique,
                   product_name non-null

Compatible GX Core v1.x — Validator via EphemeralDataContext + pandas datasource.
Rapport HTML généré dans reports/gx/{table}_{timestamp}.html

Auteur : Tristan Vanrullen — 2026
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------

def _get_validator(df: pd.DataFrame, suite_name: str):
    """Crée un Validator GX Core 1.x sur un DataFrame Pandas.

    Chemin GX 1.x :
      EphemeralDataContext
        → add_pandas_datasource
        → add_dataframe_asset
        → build_batch_request(dataframe=df)
        → add_or_update_expectation_suite
        → context.get_validator(batch_request, expectation_suite_name)

    Le Validator retourné expose les méthodes expect_* standard.
    """
    import great_expectations as gx
    from great_expectations.core.batch import RuntimeBatchRequest

    context = gx.get_context(mode="ephemeral")

    datasource_config = {
        "name": f"ds_{suite_name}",
        "class_name": "Datasource",
        "execution_engine": {"class_name": "PandasExecutionEngine"},
        "data_connectors": {
            "runtime_connector": {
                "class_name": "RuntimeDataConnector",
                "batch_identifiers": ["batch_id"],
            }
        },
    }
    context.add_datasource(**datasource_config)

    context.add_or_update_expectation_suite(expectation_suite_name=suite_name)

    batch_request = RuntimeBatchRequest(
        datasource_name=f"ds_{suite_name}",
        data_connector_name="runtime_connector",
        data_asset_name=suite_name,
        runtime_parameters={"batch_data": df},
        batch_identifiers={"batch_id": "default"},
    )

    validator = context.get_validator(
        batch_request=batch_request,
        expectation_suite_name=suite_name,
    )
    return validator


# ---------------------------------------------------------------------------
# Suites d'expectations
# ---------------------------------------------------------------------------

def _build_fact_sales_suite() -> list[dict]:
    """Règles métier sur fact_sales Silver."""
    return [
        {"fn": "expect_column_values_to_not_be_null",
         "kwargs": {"column": "sale_id"}},
        {"fn": "expect_column_values_to_not_be_null",
         "kwargs": {"column": "customer_id"}},
        {"fn": "expect_column_values_to_not_be_null",
         "kwargs": {"column": "product_id"}},
        {"fn": "expect_column_values_to_be_unique",
         "kwargs": {"column": "sale_id"}},
        {"fn": "expect_column_values_to_be_between",
         "kwargs": {"column": "total_amount", "min_value": 0.01}},
        {"fn": "expect_column_values_to_be_between",
         "kwargs": {"column": "quantity", "min_value": 1.0}},
        {"fn": "expect_column_to_exist",
         "kwargs": {"column": "_source_silo"}},
        {"fn": "expect_column_to_exist",
         "kwargs": {"column": "_silver_processed_at"}},
        {"fn": "expect_table_row_count_to_be_between",
         "kwargs": {"min_value": 1}},
    ]


def _build_dim_products_suite() -> list[dict]:
    """Règles métier sur dim_products Silver."""
    return [
        {"fn": "expect_column_values_to_not_be_null",
         "kwargs": {"column": "product_id"}},
        {"fn": "expect_column_values_to_be_unique",
         "kwargs": {"column": "product_id"}},
        {"fn": "expect_column_values_to_not_be_null",
         "kwargs": {"column": "product_name"}},
        {"fn": "expect_column_values_to_be_between",
         "kwargs": {"column": "unit_price", "min_value": 0.01}},
        {"fn": "expect_column_to_exist",
         "kwargs": {"column": "_source_silo"}},
        {"fn": "expect_column_to_exist",
         "kwargs": {"column": "_silver_processed_at"}},
        {"fn": "expect_table_row_count_to_be_between",
         "kwargs": {"min_value": 1}},
    ]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def _run_suite(
    df: pd.DataFrame,
    suite_rules: list[dict],
    table_name: str,
    report_dir: Path,
) -> dict:
    """Exécute une suite GX v1.x sur un DataFrame et génère le rapport HTML."""
    validator = _get_validator(df, suite_name=f"suite_{table_name}")
    results: list[dict] = []

    for rule in suite_rules:
        expectation_fn = getattr(validator, rule["fn"])
        gx_result = expectation_fn(**rule["kwargs"])
        passed = gx_result["success"]
        detail = getattr(gx_result, "result", {})
        results.append({
            "expectation": rule["fn"],
            "kwargs": rule["kwargs"],
            "success": passed,
            "result": detail,
        })
        status = "✅" if passed else "❌"
        logger.info("[GX] %s %s  %s", status, table_name, rule["fn"])

    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    html_path = report_dir / f"{table_name}_{ts}.html"
    _write_html_report(table_name, results, html_path)
    logger.info("[GX] Rapport HTML : %s", html_path)

    failed = [r for r in results if not r["success"]]
    return {
        "table": table_name,
        "total": len(results),
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "failures": [{"expectation": f["expectation"], "kwargs": f["kwargs"]} for f in failed],
        "html_report": str(html_path),
    }


def _write_html_report(table_name: str, results: list[dict], path: Path) -> None:
    """Génère un rapport HTML autonome (sans dépendance CDN)."""
    rows = []
    for r in results:
        icon = "✅" if r["success"] else "❌"
        bg = "#e6f4ea" if r["success"] else "#fce8e6"
        rows.append(
            f'<tr style="background:{bg}">'
            f"<td>{icon}</td>"
            f'<td><code>{r["expectation"]}</code></td>'
            f'<td><code>{r["kwargs"]}</code></td>'
            f'<td>{r["result"]}</td>'
            "</tr>"
        )
    rows_html = "\n".join(rows)
    ts = datetime.now(timezone.utc).isoformat()
    passed = sum(1 for r in results if r["success"])
    failed = len(results) - passed
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>GX Report — {table_name}</title>
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 2rem; color: #2B2B33; }}
    h1   {{ color: #1454F5; }}
    .summary {{ display: flex; gap: 2rem; margin-bottom: 1.5rem; }}
    .badge {{ padding: .4rem 1rem; border-radius: 6px; font-weight: 700; font-size: 1.1rem; }}
    .ok  {{ background: #e6f4ea; color: #137333; }}
    .ko  {{ background: #fce8e6; color: #c5221f; }}
    table {{ border-collapse: collapse; width: 100%; font-size: .92rem; }}
    th {{ background: #1454F5; color: #fff; padding: .5rem .8rem; text-align: left; }}
    td {{ padding: .45rem .8rem; border-bottom: 1px solid #e0e0e0; vertical-align: top; }}
    code {{ background: #f1f3f4; padding: .1rem .3rem; border-radius: 3px; }}
    footer {{ margin-top: 2rem; color: #888; font-size: .8rem; }}
  </style>
</head>
<body>
  <h1>🐙 GX Report — {table_name}</h1>
  <p>Strategic Lakehouse · Couche Silver · {ts}</p>
  <div class="summary">
    <span class="badge ok">✅ {passed} passed</span>
    <span class="badge ko">❌ {failed} failed</span>
    <span class="badge" style="background:#e8f0fe;color:#1967d2">{len(results)} total</span>
  </div>
  <table>
    <thead><tr><th></th><th>Expectation</th><th>Kwargs</th><th>Result detail</th></tr></thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
  <footer>Généré par src/quality/gx_checkpoint.py · GX Core v1.x API · Tristan Vanrullen · 2026</footer>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def run_gx_checkpoint(
    silver_dir: Path,
    report_dir: Path,
) -> dict[str, dict]:
    """Exécute les checkpoints GX sur les tables Silver cibles.

    Retourne un dict {table_name: résumé_checkpoint}.
    Lève RuntimeError si des expectations échouent.
    """
    targets = {
        "fact_sales": _build_fact_sales_suite,
        "dim_products": _build_dim_products_suite,
    }

    all_results: dict[str, dict] = {}
    failures_total = 0

    for table_name, suite_fn in targets.items():
        parquet_path = silver_dir / f"{table_name}.parquet"
        if not parquet_path.exists():
            logger.warning("[GX] Parquet Silver absent, ignoré : %s", parquet_path)
            continue

        df = pd.read_parquet(parquet_path)
        summary = _run_suite(df, suite_fn(), table_name, report_dir)
        all_results[table_name] = summary
        failures_total += summary["failed"]

    if failures_total > 0:
        failed_details = [
            f"{t}: {r['failures']}"
            for t, r in all_results.items() if r["failed"] > 0
        ]
        raise RuntimeError(
            f"[GX] {failures_total} expectation(s) échouée(s) : {failed_details}"
        )

    logger.info("[GX] Checkpoint Silver : SUCCÈS (%d tables)", len(all_results))
    return all_results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(
        description="Great Expectations Core v1.x — Checkpoint couche Silver"
    )
    parser.add_argument(
        "--silver-dir",
        default=str(Path(__file__).resolve().parents[2] / "data" / "silver"),
    )
    parser.add_argument(
        "--report-dir",
        default=str(Path(__file__).resolve().parents[2] / "reports" / "gx"),
    )
    args = parser.parse_args()

    results = run_gx_checkpoint(
        silver_dir=Path(args.silver_dir),
        report_dir=Path(args.report_dir),
    )
    print("\n🐙 GX Checkpoint Silver — Résumé")
    print("-" * 50)
    for table, r in results.items():
        status = "✅" if r["failed"] == 0 else "❌"
        print(f"  {status} {table:<25} {r['passed']}/{r['total']} passed")
        print(f"      └ Rapport : {r['html_report']}")
    print("-" * 50)
