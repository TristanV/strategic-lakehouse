"""
Orchestrate Bronze → Silver → Gold en une commande.

Usage :
    python -m src.pipeline               # exécute toutes les couches
    python -m src.pipeline --layer bronze
    python -m src.pipeline --layer silver
    python -m src.pipeline --layer gold
    python -m src.pipeline --layer all
    python src/pipeline.py --layer silver --bronze-dir /custom/bronze

Arguments optionnels :
    --raw-dir      Chemin vers data/raw/    (défaut : <project_root>/data/raw)
    --bronze-dir   Chemin vers data/bronze/ (défaut : <project_root>/data/bronze)
    --silver-dir   Chemin vers data/silver/ (défaut : <project_root>/data/silver)
    --gold-dir     Chemin vers data/gold/   (défaut : <project_root>/data/gold)
    --log-level    Niveau de log : DEBUG | INFO | WARNING (défaut : INFO)

Sorties :
    Logs structurés sur stdout.
    Code de retour 0 si toutes les couches demandées réussissent, 1 sinon.

Auteur : Tristan Vanrullen — 2026
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Callable

from src.bronze.ingest import ingest_csv_to_bronze
from src.gold.aggregate import run_gold_aggregations
from src.silver.transform import run_silver_transformations

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_LAYERS = ("bronze", "silver", "gold")
_OCTO = "🐙"


# ---------------------------------------------------------------------------
# Runner générique
# ---------------------------------------------------------------------------

def _run_layer(
    name: str,
    fn: Callable[..., dict[str, int]],
    **kwargs,
) -> dict[str, int]:
    """Exécute une couche, chronometre et logge les stats.

    Args:
        name:   Nom de la couche (bronze | silver | gold).
        fn:     Callable de la couche (retourne {table: nb_lignes}).
        kwargs: Arguments keyword passés à fn.

    Returns:
        Dictionnaire {table: nb_lignes} produit par la couche.

    Raises:
        RuntimeError: Si fn lève une exception (propagé avec contexte).
    """
    logger.info("%s [%s] Démarrage...", _OCTO, name.upper())
    t0 = time.perf_counter()
    try:
        stats = fn(**kwargs)
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        logger.error("%s [%s] ÉCHEC après %.2fs : %s", _OCTO, name.upper(), elapsed, exc)
        raise RuntimeError(f"Couche {name} en échec") from exc

    elapsed = time.perf_counter() - t0
    total_rows = sum(stats.values())
    logger.info(
        "%s [%s] Terminé en %.2fs — %d tables, %d lignes au total",
        _OCTO, name.upper(), elapsed, len(stats), total_rows,
    )
    for table, nb in stats.items():
        logger.info("     └ %-35s %6d lignes", table, nb)
    return stats


# ---------------------------------------------------------------------------
# Orchestrateur principal
# ---------------------------------------------------------------------------

def run_pipeline(
    layer: str = "all",
    *,
    raw_dir: Path,
    bronze_dir: Path,
    silver_dir: Path,
    gold_dir: Path,
) -> dict[str, dict[str, int]]:
    """
    Exécute les couches demandées dans l’ordre Bronze → Silver → Gold.

    Args:
        layer:      "bronze" | "silver" | "gold" | "all"
        raw_dir:    Chemin vers les CSV sources (data/raw/).
        bronze_dir: Chemin vers la couche Bronze (data/bronze/).
        silver_dir: Chemin vers la couche Silver (data/silver/).
        gold_dir:   Chemin vers la couche Gold   (data/gold/).

    Returns:
        Dict {layer_name: {table: nb_lignes}} pour chaque couche exécutée.

    Raises:
        ValueError:   Si layer n’est pas dans ("bronze", "silver", "gold", "all").
        RuntimeError: Propagé depuis _run_layer si une couche échoue.
    """
    if layer not in (*_LAYERS, "all"):
        raise ValueError(
            f"--layer invalide : '{layer}'. Valeurs acceptables : bronze, silver, gold, all."
        )

    run_bronze = layer in ("bronze", "all")
    run_silver = layer in ("silver", "all")
    run_gold   = layer in ("gold",   "all")

    results: dict[str, dict[str, int]] = {}

    if run_bronze:
        results["bronze"] = _run_layer(
            "bronze",
            ingest_csv_to_bronze,
            raw_dir=raw_dir,
            bronze_dir=bronze_dir,
        )

    if run_silver:
        results["silver"] = _run_layer(
            "silver",
            run_silver_transformations,
            bronze_dir=bronze_dir,
            silver_dir=silver_dir,
        )

    if run_gold:
        results["gold"] = _run_layer(
            "gold",
            run_gold_aggregations,
            silver_dir=silver_dir,
            gold_dir=gold_dir,
        )

    return results


# ---------------------------------------------------------------------------
# Affichage du résumé final
# ---------------------------------------------------------------------------

def _print_summary(results: dict[str, dict[str, int]], elapsed_total: float) -> None:
    """Affiche un résumé lisible des stats de toutes les couches exécutées."""
    print()
    print(f"{_OCTO}  Strategic Lakehouse — Résumé pipeline")
    print("-" * 52)
    for layer_name, stats in results.items():
        total = sum(stats.values())
        print(f"  {layer_name.upper():<10}  {len(stats)} tables  {total:>8} lignes")
        for table, nb in stats.items():
            print(f"    └ {table:<35} {nb:>6}")
    print("-" * 52)
    print(f"  Durée totale : {elapsed_total:.2f}s")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pipeline",
        description=f"{_OCTO} Strategic Lakehouse — Orchestrateur Bronze→Silver→Gold",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--layer",
        choices=[*_LAYERS, "all"],
        default="all",
        help="Couche(s) à exécuter (défaut : all)",
    )
    p.add_argument("--raw-dir",    type=Path, default=None, help="Chemin vers data/raw/")
    p.add_argument("--bronze-dir", type=Path, default=None, help="Chemin vers data/bronze/")
    p.add_argument("--silver-dir", type=Path, default=None, help="Chemin vers data/silver/")
    p.add_argument("--gold-dir",   type=Path, default=None, help="Chemin vers data/gold/")
    p.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Niveau de log (défaut : INFO)",
    )
    return p


if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    project_root = Path(__file__).resolve().parents[1]
    data = project_root / "data"

    raw_dir    = args.raw_dir    or data / "raw"
    bronze_dir = args.bronze_dir or data / "bronze"
    silver_dir = args.silver_dir or data / "silver"
    gold_dir   = args.gold_dir   or data / "gold"

    logger.info("%s Pipeline — layer=%s", _OCTO, args.layer)
    logger.info("   raw    : %s", raw_dir)
    logger.info("   bronze : %s", bronze_dir)
    logger.info("   silver : %s", silver_dir)
    logger.info("   gold   : %s", gold_dir)

    t_start = time.perf_counter()
    try:
        results = run_pipeline(
            layer=args.layer,
            raw_dir=raw_dir,
            bronze_dir=bronze_dir,
            silver_dir=silver_dir,
            gold_dir=gold_dir,
        )
    except (ValueError, RuntimeError) as exc:
        logger.error("Pipeline interrompu : %s", exc)
        sys.exit(1)

    _print_summary(results, time.perf_counter() - t_start)
    sys.exit(0)
