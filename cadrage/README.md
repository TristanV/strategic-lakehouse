# 📋 Cadrage — Strategic Lakehouse

> Auteur : Tristan Vanrullen — 2026  
> Documents de spécification et cadrage du projet

---

## Contenu attendu de ce dossier

```
cadrage/
├── README.md                           ← Ce fichier
├── cdc_fonctionnel.md                  ← Cahier des Charges fonctionnel (MoSCoW)
├── matrice_risques.md                  ← Matrice des risques projet
├── specification_technique.md          ← Spécifications d'architecture
├── accessibilite_rgaa.md               ← Section accessibilité RGAA/WCAG
├── conformite_rgpd_aiact.md            ← Conformité réglementaire
└── glossaire_data.md                   ← Glossaire métier et data
```

---

## Cahier des Charges Fonctionnel (CDC)

Le CDC MoSCoW couvre les besoins fonctionnels et non fonctionnels du projet :

### Must have
- Pipeline d'ingestion des 3 silos (ERP, CRM, analytique) vers la couche Bronze
- Transformation Bronze → Silver avec règles de qualité documentées
- Construction de la couche Gold avec au moins 3 KPI métier
- API Flask/FastAPI exposant les KPI Gold en JSON
- Documentation reproductible (README + CI)

### Should have
- Catalogue de données avec description, owner et SLA
- Tests de qualité automatisés (Great Expectations / Soda)
- Lineage automatisé (OpenLineage ou équivalent)
- Interface HTML accessible (WCAG 2.1 AA / RGAA)
- Alertes de monitoring sur la fraîcheur et l'intégrité

### Could have
- Orchestration Airflow des pipelines
- Visualisation BI démo (Metabase, Grafana ou équivalent)
- Endpoint RAG / question-answering sur les KPI Gold
- Dashboard de data observability

### Won't have (périmètre POC)
- Mise en production cloud complète
- Streaming temps réel (Kafka)
- Habilitations fines multi-rôles

---

## Matrice des risques (synthèse)

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Qualité insuffisante des données sources | Élevée | Élevé | Règles de qualité dès la couche Bronze, tests CI |
| Dérive de périmètre (scope creep) | Moyenne | Moyen | MoSCoW strict, revues de sprint |
| Conflits de référentiels (MDM) | Élevée | Élevé | Glossaire et règles de déduplication documentées |
| Non-conformité RGPD | Faible | Très élevé | Pseudonymisation Silver, registre de traitement |
| Obsolescence du pipeline | Faible | Moyen | Versioning, CI/CD, tests de non-régression |

---

## Accessibilité

L'interface de consultation doit respecter les niveaux **A et AA du WCAG 2.1** (RGAA 4.1) :
- Structure sémantique HTML5 (`<main>`, `<nav>`, `<header>`, `<aside>`)
- Ratio de contraste minimum 4,5:1 pour le texte courant
- Navigation clavier complète
- Balises `aria-label` sur les éléments interactifs
- Textes alternatifs sur toutes les représentations graphiques

---

## Conformité réglementaire

### RGPD
- Pseudonymisation des données clients dès la couche Silver
- Registre de traitements à maintenir
- Durée de conservation et politique de purge documentées
- Privacy by design natif dans l'architecture

### AI Act (Règlement UE 2024/1689)
- Applicable à partir du 2 août 2025 (obligations générales) et 2 août 2026 (systèmes haut risque)
- Obligation de traçabilité des données d'entraînement (Art. 10)
- Documentation technique des systèmes IA déployés (Art. 11)
- Le data lineage répond à l'obligation d'auditabilité des modèles

---

## Glossaire (extrait)

| Terme | Définition |
|---|---|
| Bronze | Couche d'ingestion brute sans transformation |
| Silver | Couche de donnée nettoyée, normalisée et validée |
| Gold | Couche d'agrégats métier exposables à la BI et aux API |
| Data lineage | Traçabilité du parcours d'une donnée de la source à la consommation |
| Data steward | Responsable métier de la qualité d'un périmètre de données |
| CDC | Cahier Des Charges |
| KPI | Indicateur clé de performance |
| MoSCoW | Must / Should / Could / Won't — méthode de priorisation |
| RGPD | Règlement Général sur la Protection des Données |
| SLA | Niveau de service attendu sur un flux ou un produit de données |

---

*Tristan Vanrullen — 2026*
