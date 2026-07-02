"""
Tests pytest — API FastAPI (api/routers/kpi.py).

Couverture :
  - test_root_health           : GET / retourne status=ok et liste les KPI
  - test_list_kpi              : GET /kpi retourne count >= 0 et liste structurée
  - test_get_kpi_not_found     : GET /kpi/inexistant retourne 404
  - test_get_kpi_format_invalid: GET /kpi/{name}?format=bad retourne 422
  - test_get_kpi_records       : GET /kpi/{name} retourne total_rows > 0
  - test_get_kpi_limit         : ?limit=3 retourne au plus 3 lignes
  - test_get_kpi_columns       : ?format=columns retourne un dict de listes
  - test_get_kpi_schema        : GET /kpi/{name}/schema retourne colonnes+types
  - test_kpi_response_time     : réponse en < 500 ms (assouplit l'exigence F04 < 200 ms)

Auteur : Tristan Vanrullen — 2026
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

GOLD_DIR = Path(__file__).resolve().parents[1] / "data" / "gold"


def _available_kpis() -> list[str]:
    """Liste les KPI Gold disponibles sur disque."""
    if not GOLD_DIR.exists():
        return []
    return [p.stem for p in sorted(GOLD_DIR.glob("kpi_*.parquet"))]


def _first_kpi() -> str | None:
    """Retourne le premier KPI disponible ou None."""
    kpis = _available_kpis()
    return kpis[0] if kpis else None


# ---------------------------------------------------------------------------
# Health / root
# ---------------------------------------------------------------------------

def test_root_health():
    """GET / : status ok, champs attendus présents."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "kpi_available" in data
    assert "endpoints" in data
    assert isinstance(data["kpi_available"], list)


# ---------------------------------------------------------------------------
# GET /kpi — catalogue
# ---------------------------------------------------------------------------

def test_list_kpi_structure():
    """GET /kpi : réponse JSON avec count et kpis liste."""
    response = client.get("/kpi")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "kpis" in data
    assert isinstance(data["kpis"], list)
    assert data["count"] == len(data["kpis"])


def test_list_kpi_fields():
    """GET /kpi : chaque entrée a les champs name, description, endpoint, nb_rows."""
    response = client.get("/kpi")
    data = response.json()
    for entry in data["kpis"]:
        assert "name" in entry
        assert "description" in entry
        assert "endpoint" in entry
        assert "nb_rows" in entry


# ---------------------------------------------------------------------------
# Erreurs
# ---------------------------------------------------------------------------

def test_get_kpi_not_found():
    """GET /kpi/inexistant : 404 avec message explicite."""
    response = client.get("/kpi/kpi_inexistant_xyz")
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "kpi_inexistant_xyz" in detail


def test_get_kpi_format_invalid():
    """GET /kpi/{name}?format=bad : 422 format invalide."""
    kpi = _first_kpi()
    if kpi is None:
        pytest.skip("Aucun KPI Gold disponible sur disque")
    response = client.get(f"/kpi/{kpi}?format=bad")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /kpi/{name} — données
# ---------------------------------------------------------------------------

def test_get_kpi_records_format():
    """GET /kpi/{name} : total_rows > 0, data est une liste, format=records."""
    kpi = _first_kpi()
    if kpi is None:
        pytest.skip("Aucun KPI Gold disponible sur disque")
    response = client.get(f"/kpi/{kpi}")
    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] > 0
    assert data["format"] == "records"
    assert isinstance(data["data"], list)
    assert len(data["data"]) == data["returned_rows"]


def test_get_kpi_limit():
    """GET /kpi/{name}?limit=3 : returned_rows <= 3."""
    kpi = _first_kpi()
    if kpi is None:
        pytest.skip("Aucun KPI Gold disponible sur disque")
    response = client.get(f"/kpi/{kpi}?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert data["returned_rows"] <= 3
    assert len(data["data"]) <= 3


def test_get_kpi_columns_format():
    """GET /kpi/{name}?format=columns : data est un dict de listes."""
    kpi = _first_kpi()
    if kpi is None:
        pytest.skip("Aucun KPI Gold disponible sur disque")
    response = client.get(f"/kpi/{kpi}?format=columns")
    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "columns"
    assert isinstance(data["data"], dict)
    for col_values in data["data"].values():
        assert isinstance(col_values, list)


def test_get_kpi_data_no_none_key():
    """GET /kpi/{name} : aucune clé None dans les records (sérialisation JSON propre)."""
    kpi = _first_kpi()
    if kpi is None:
        pytest.skip("Aucun KPI Gold disponible sur disque")
    response = client.get(f"/kpi/{kpi}?limit=10")
    assert response.status_code == 200
    for record in response.json()["data"]:
        assert None not in record.keys()


def test_get_all_kpis_accessible():
    """GET /kpi/{name} : tous les KPI Gold disponibles retournent 200."""
    for kpi in _available_kpis():
        response = client.get(f"/kpi/{kpi}?limit=1")
        assert response.status_code == 200, f"KPI {kpi} inaccessible : {response.status_code}"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def test_get_kpi_schema():
    """GET /kpi/{name}/schema : retourne une liste de colonnes avec name et type."""
    kpi = _first_kpi()
    if kpi is None:
        pytest.skip("Aucun KPI Gold disponible sur disque")
    response = client.get(f"/kpi/{kpi}/schema")
    assert response.status_code == 200
    data = response.json()
    assert "columns" in data
    assert data["count"] == len(data["columns"])
    for col in data["columns"]:
        assert "name" in col
        assert "type" in col


def test_get_kpi_schema_not_found():
    """GET /kpi/inexistant/schema : 404."""
    response = client.get("/kpi/kpi_inexistant_xyz/schema")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Performance (exigence F04 : < 200 ms, test à 500 ms pour CI)
# ---------------------------------------------------------------------------

def test_kpi_response_time():
    """Performance : réponse en < 500 ms (F04 cible < 200 ms en prod)."""
    kpi = _first_kpi()
    if kpi is None:
        pytest.skip("Aucun KPI Gold disponible sur disque")
    start = time.perf_counter()
    response = client.get(f"/kpi/{kpi}")
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert response.status_code == 200
    assert elapsed_ms < 500, f"Réponse trop lente : {elapsed_ms:.1f} ms (seuil CI : 500 ms)"
