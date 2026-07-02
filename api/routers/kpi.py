"""
Router KPI — Strategic Lakehouse Gold API.

Endpoints :
  GET /kpi                  Liste des KPI disponibles avec métadonnées
  GET /kpi/{name}           Données d'un KPI Gold en JSON
  GET /kpi/{name}/schema    Schéma (colonnes + types) du KPI

Paramètres de requête pour GET /kpi/{name} :
  limit    int    (optionnel) Nombre maximum de lignes retournées (défaut : toutes)
  format   str    (optionnel) 'records' (défaut) | 'columns'

Exemples :
  GET /kpi/kpi_revenue_by_period
  GET /kpi/kpi_top_products?limit=10
  GET /kpi/kpi_avg_basket?limit=50&format=columns
  GET /kpi/kpi_revenue_by_period/schema

Auteur : Tristan Vanrullen — 2026
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Optional

import duckdb
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
GOLD_DIR = PROJECT_ROOT / "data" / "gold"

KPI_CATALOG: dict[str, str] = {
    "kpi_revenue_by_period":  "CA total par année et par mois",
    "kpi_revenue_by_segment": "CA et panier moyen par pays et statut marital",
    "kpi_avg_basket":          "Panier moyen et fréquence d'achat par client",
    "kpi_top_products":        "Top produits par CA et par volume de ventes",
    "kpi_crm_engagement":      "Engagement CRM par canal et pays client",
}

router = APIRouter(prefix="/kpi", tags=["kpi"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gold_path(name: str) -> Path:
    """Retourne le chemin Parquet Gold pour un KPI donné."""
    return GOLD_DIR / f"{name}.parquet"


def _available_kpis() -> list[str]:
    """Retourne la liste des KPI disponibles (fichiers Parquet présents)."""
    if not GOLD_DIR.exists():
        return []
    return [p.stem for p in sorted(GOLD_DIR.glob("kpi_*.parquet"))]


def _sanitize(value: Any) -> Any:
    """
    Convertit les types non-sérialisables JSON (NaN, Inf, numpy int/float)
    en valeurs JSON valides.
    """
    if value is None:
        return None
    # NaN / Inf float Python
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    # numpy / pandas scalar — conversion via int/float Python natif
    try:
        import numpy as np  # optionnel — présent si pandas est installé
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            v = float(value)
            return None if (math.isnan(v) or math.isinf(v)) else v
        if isinstance(value, np.bool_):
            return bool(value)
    except ImportError:
        pass
    return value


def _df_to_records(df, limit: int | None) -> list[dict]:
    """Convertit un DataFrame en liste de dicts JSON-safe, avec limit optionnel."""
    if limit is not None and limit > 0:
        df = df.head(limit)
    records = df.to_dict(orient="records")
    return [
        {k: _sanitize(v) for k, v in row.items()}
        for row in records
    ]


def _df_to_columns(df, limit: int | None) -> dict[str, list]:
    """Convertit un DataFrame en dict {colonne: [valeurs]} JSON-safe."""
    if limit is not None and limit > 0:
        df = df.head(limit)
    return {
        col: [_sanitize(v) for v in df[col].tolist()]
        for col in df.columns
    }


def _read_parquet(name: str) -> Any:
    """Lit un Parquet Gold via DuckDB et retourne un DataFrame."""
    path = _gold_path(name)
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"KPI '{name}' introuvable. "
                f"Fichier attendu : {path}. "
                f"KPI disponibles : {_available_kpis()}"
            ),
        )
    conn = duckdb.connect()
    try:
        df = conn.execute(f"SELECT * FROM read_parquet('{path}')").df()
    finally:
        conn.close()
    return df


# ---------------------------------------------------------------------------
# GET /kpi — catalogue
# ---------------------------------------------------------------------------

@router.get("", summary="Liste des KPI disponibles")
def list_kpi() -> JSONResponse:
    """
    Retourne la liste des KPI Gold disponibles avec leurs métadonnées.
    Seuls les KPI dont le fichier Parquet est présent sont listés.
    """
    available = _available_kpis()
    kpis = []
    for name in available:
        path = _gold_path(name)
        meta: dict[str, Any] = {
            "name":        name,
            "description": KPI_CATALOG.get(name, "KPI Gold"),
            "endpoint":    f"/kpi/{name}",
            "schema":      f"/kpi/{name}/schema",
            "size_bytes":  path.stat().st_size,
        }
        # Nombre de lignes via DuckDB (rapide — lit uniquement les métadonnées Parquet)
        try:
            conn = duckdb.connect()
            meta["nb_rows"] = conn.execute(
                f"SELECT COUNT(*) FROM read_parquet('{path}')"
            ).fetchone()[0]
            conn.close()
        except Exception:  # noqa: BLE001
            meta["nb_rows"] = None
        kpis.append(meta)

    return JSONResponse({"count": len(kpis), "kpis": kpis})


# ---------------------------------------------------------------------------
# GET /kpi/{name} — données
# ---------------------------------------------------------------------------

@router.get(
    "/{name}",
    summary="Données d'un KPI Gold",
    response_description="Liste de lignes JSON issues du Parquet Gold",
)
def get_kpi(
    name: str,
    limit: Optional[int] = Query(
        default=None,
        ge=1,
        le=100_000,
        description="Nombre maximum de lignes retournées (défaut : toutes)",
    ),
    format: Optional[str] = Query(
        default="records",
        description="Format de sortie : 'records' (liste de dicts) ou 'columns' (dict de listes)",
    ),
) -> JSONResponse:
    """
    Retourne les données d'un KPI Gold en JSON.

    - **name** : identifiant du KPI (ex. `kpi_revenue_by_period`)
    - **limit** : optionnel — tronque le résultat aux N premières lignes
    - **format** : `records` (défaut) ou `columns`
    """
    if format not in ("records", "columns"):
        raise HTTPException(
            status_code=422,
            detail="Paramètre 'format' invalide. Valeurs acceptées : 'records', 'columns'.",
        )

    df = _read_parquet(name)
    total_rows = len(df)

    if format == "columns":
        data = _df_to_columns(df, limit)
        returned = len(next(iter(data.values()), []))
    else:
        data = _df_to_records(df, limit)
        returned = len(data)

    return JSONResponse({
        "kpi":          name,
        "description":  KPI_CATALOG.get(name, "KPI Gold"),
        "total_rows":   total_rows,
        "returned_rows": returned,
        "limit":        limit,
        "format":       format,
        "data":         data,
    })


# ---------------------------------------------------------------------------
# GET /kpi/{name}/schema — schéma
# ---------------------------------------------------------------------------

@router.get(
    "/{name}/schema",
    summary="Schéma (colonnes + types) d'un KPI",
)
def get_kpi_schema(name: str) -> JSONResponse:
    """
    Retourne le schéma du KPI : nom de colonne, type DuckDB, nullable.
    """
    path = _gold_path(name)
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"KPI '{name}' introuvable. KPI disponibles : {_available_kpis()}",
        )
    conn = duckdb.connect()
    try:
        rows = conn.execute(f"DESCRIBE SELECT * FROM read_parquet('{path}')").fetchall()
    finally:
        conn.close()

    columns = [
        {"name": r[0], "type": r[1], "nullable": r[2] == "YES"}
        for r in rows
    ]
    return JSONResponse({
        "kpi":     name,
        "columns": columns,
        "count":   len(columns),
    })
