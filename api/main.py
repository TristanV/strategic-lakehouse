"""
API FastAPI — Strategic Lakehouse Gold Layer.

Expose les 5 KPI Gold en endpoints JSON READ-ONLY.
Les données sont lues depuis les fichiers Parquet de data/gold/ via DuckDB.

Endpoints disponibles :
  GET /                             health-check + liste des KPI disponibles
  GET /kpi/{name}                   données complètes d'un KPI (JSON)
  GET /kpi/{name}?limit=N           données limitées à N lignes
  GET /kpi/{name}?format=records    format par défaut (liste de dict)
  GET /kpi/{name}?format=columns    format orienté colonnes
  GET /kpi                          liste des KPI disponibles avec métadonnées

Usage :
  uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
  # ou depuis la racine du projet :
  python -m uvicorn api.main:app --reload

Auteur : Tristan Vanrullen — 2026
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routers import kpi as kpi_router

# ---------------------------------------------------------------------------
# Chemins
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD_DIR = PROJECT_ROOT / "data" / "gold"

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Strategic Lakehouse API",
    description=(
        "API READ-ONLY exposant les KPI Gold de GlobalTrade Solutions. "
        "Données issues de l'architecture Medallion Bronze → Silver → Gold."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS ouvert (usage pédagogique — restreindre en production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(kpi_router.router)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------
@app.get("/", tags=["health"], summary="Health-check + catalogue des KPI")
def root() -> JSONResponse:
    """Retourne le statut de l'API et la liste des KPI disponibles."""
    available = [
        p.stem for p in sorted(GOLD_DIR.glob("kpi_*.parquet"))
    ] if GOLD_DIR.exists() else []

    return JSONResponse({
        "status": "ok",
        "service": "Strategic Lakehouse API",
        "version": "1.0.0",
        "gold_dir": str(GOLD_DIR),
        "kpi_available": available,
        "endpoints": {
            "list_kpi":  "/kpi",
            "get_kpi":   "/kpi/{name}",
            "docs":      "/docs",
            "redoc":     "/redoc",
        },
    })


# ---------------------------------------------------------------------------
# Point d'entrée direct
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
