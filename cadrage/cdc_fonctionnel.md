# Cahier des Charges Fonctionnel — Strategic Lakehouse

> Auteur : Tristan Vanrullen — 2026  
> Version : 1.0 — À enrichir en Phase 2

## Contexte et objectifs

GlobalTrade Solutions souhaite consolider ses trois silos de données (ERP, CRM, analytique) au sein d'une plateforme unifiée de type Lakehouse, permettant :
- Une **vérité unique** sur les KPI transverses
- Une **exposition API** des agrégats métier
- Une **fondation** pour les usages IA et analytique avancée

## Exigences fonctionnelles (MoSCoW)

> *(Cf. cadrage/README.md pour la synthèse)*

### Must have

| ID | Exigence | Critère de validation |
|---|---|---|
| F01 | Ingestion des 3 silos vers Bronze | Fichiers présents, timestamp d'ingestion, aucune transformation |
| F02 | Transformation Bronze → Silver | Complétude > 95%, 0 doublon, typage strict |
| F03 | Construction de la couche Gold | 3 KPI minimum calculés, conformes au glossaire |
| F04 | Endpoint API `/kpi/<name>` | Réponse JSON en < 200 ms, code 200 |
| F05 | Documentation reproductible | README avec instructions, CI GitHub Actions |

### Should have

| ID | Exigence |
|---|---|
| F06 | Catalogue de données avec owner et SLA |
| F07 | Tests qualité automatisés |
| F08 | Lineage des transformations |
| F09 | Interface HTML accessible |

## Exigences non fonctionnelles

| Catégorie | Exigence |
|---|---|
| Performance | Pipeline full < 5 min sur dataset complet |
| Sécurité | Pseudonymisation PII en Silver |
| Maintenabilité | Code versionné, testé, documenté |
| Conformité | RGPD + WCAG 2.1 AA |

---

*Tristan Vanrullen — 2026*
