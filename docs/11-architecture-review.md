# BioCycle Djerba — Architecture & Business Review

> **Rôle :** Senior Software Architect · **Type :** audit, pas d'implémentation.
> **Date :** 2026-07-08 · **Périmètre :** couche métier complète (backend + frontend).
> **Objectif :** identifier ce qui manque, est incohérent, dupliqué, ou pas
> production-ready — **avant** de brancher Firebase.

**Verdict global :** la couche métier est **fonctionnellement complète et bien
structurée** (Clean Architecture respectée, 132 tests verts). Elle n'est **pas
encore production-ready** : ~4 points de correction sérieux et un lot de dette de
surface (code mort, API obsolète exposée, secrets par défaut). Rien de
bloquant-critique ; tout est corrigeable en une passe ciblée.

Légende sévérité : 🔴 à corriger avant prod · 🟠 à améliorer · 🟢 mineur/cosmétique.

---

## 1. Domain Model

**État : bon.** Entités cohérentes, relations correctes, cycle de vie explicite.

| Constat | Sév. | Détail |
|---|---|---|
| Doublon conceptuel `WasteCollection` vs `CollectionRequest` | 🟠 | L'ancien `waste_collections` (+ `Prediction`) modélise une pesée a posteriori ; le produit tourne sur `CollectionRequest`. Les deux coexistent → confusion de domaine. Décision à acter : archiver/retirer l'ancien modèle. |
| `AIStatus.FAILED` annoncé « re-triable » mais pas de chemin de re-scoring | 🟠 | Le commentaire (models.py:39, state_machine.py:41) promet un re-scoring `AI_FAILED → PENDING`, mais aucun endpoint/méthode ne le déclenche. Soit l'implémenter (retry), soit retirer la promesse. Avec Firebase, un « refresh depuis Firebase » remplira ce rôle. |
| Champs `ai_*` : 10 colonnes sur l'agrégat | 🟢 | Acceptable (lecture directe pour le dashboard), mais envisager un sous-objet/`JSONB` `ai_analysis` si l'on veut alléger la table. Pas prioritaire. |
| Nommage `ai_*` vs modèle « pas d'IA backend » | 🟢 | Cohérent : ce sont des *résultats* d'IA stockés, pas un calcul. OK de garder le préfixe `ai_`. |
| `operator_notes` écrasé à chaque transition | 🟠 | `decide`/`transition` font `if data.notes: req.operator_notes = data.notes` → une note à l'étape *collected* écrase celle de l'*accept*. Envisager un append/historique ou un champ par étape. |

**Lifecycle** : la machine à états est une **vraie source unique de vérité**
(`state_machine.py`), testée, avec garde `assert_transition_allowed` → 409. États
terminaux corrects (`rejected`, `completed`). ✅

---

## 2. Database

**État : solide.** FK, cascades et index bien pensés.

| Constat | Sév. | Détail |
|---|---|---|
| FK & cascades | 🟢 | `collection_requests.hotel_id → hotels ON DELETE CASCADE`, `decided_by → users SET NULL`, `request_photos.request_id → CASCADE`, `notifications.user_id → CASCADE`, `request_id → SET NULL`. Cohérent et intentionnel. ✅ |
| Index | 🟢 | Présents sur `hotel_id`, `status`, `ai_status`, `ai_priority_score`, `distance_to_plant_km`, `decided_by`, `request_id`, `notifications.(user_id,is_read)`. ✅ |
| **Index composite manquant pour la file opérateur** | 🟠 | Le tri à 5 clés (`priority, quality, distance, weight, created_at`) n'a pas d'index composite. Au volume hackathon c'est OK ; en prod un index `(status, ai_priority_score DESC, ai_quality_score DESC)` accélérerait la file filtrée par statut. |
| **Pas de contrainte CHECK sur les bornes** | 🟠 | `declared_weight_kg > 0`, `ai_quality_score ∈ [0,100]`, etc. sont validés par Pydantic mais **pas** au niveau DB. Un import direct ou un bug pourrait insérer des valeurs hors bornes. Ajouter des `CHECK` en prod. |
| **Unique manquant : `hotels.firebase_device_id`** | 🟢 | Prévu au plan Firebase, pas encore en base (normal, Firebase reporté). À ne pas oublier. |
| Colonnes IoT résiduelles (`smart_bins`, `sensor_readings`, `waste_collections.bin_id`) | 🟠 | Tables/colonnes de l'ancien modèle IoT, non utilisées par le produit. Dette DB à trancher (garder masqué vs migration de suppression). |

---

## 3. API

**État : cohérent et propre**, enveloppe d'erreur uniforme, pagination standard.

| Constat | Sév. | Détail |
|---|---|---|
| Enveloppe d'erreur unique | 🟢 | `{error:{code,message,details}}` via handlers globaux ; 401/403/404/409/422/500 mappés depuis `AppException`. ✅ Excellent. |
| Pagination standard | 🟢 | `Page[T]` + `PaginationParams` (page/page_size, bornes). ✅ |
| **Surface API obsolète exposée** | 🔴 | `bins`, `collections`, `alerts` sont **toujours montés** (api/router.py:33-35) alors qu'ils sont retirés du produit. Ils exposent des endpoints publics sans usage, augmentent la surface d'attaque et polluent l'OpenAPI. À **démonter** du router (garder le code si voulu). |
| **Double export CSV divergent** | 🟠 | `/analytics/export` (ancien, basé `waste_collections`) coexiste avec `/reports/requests.csv` (nouveau). Le premier renvoie des données mortes. Retirer l'ancien. |
| Statuts HTTP | 🟢 | 201 sur création, 204 sur delete/read-all, 409 sur transition illégale, 413/422 sur upload. Cohérent. ✅ |
| `RequestValidationError` fuit `exc.errors()` | 🟢 | Les `details` renvoient la structure interne Pydantic (chemins de champs). Acceptable en interne ; à filtrer si l'API devient publique. |
| OpenAPI | 🟠 | Tags/summaries présents. Manque : exemples de réponses, schémas d'erreur documentés par endpoint, et le bruit des routers obsolètes. Nettoyer améliore fortement la doc. |
| Incohérence mineure de nommage | 🟢 | Query param `status` exposé via alias sur un param interne `status_filter` — OK mais à garder homogène partout. |

---

## 4. Business Logic — Pickup Request workflow

**État : correct et bien gardé.** Chaque transition passe par la state machine.

Flux vérifié : `create (PENDING + analyse) → decide (ACCEPTED/REJECTED) →
transition (ON_THE_WAY → COLLECTED[poids requis] → COMPLETED)`. États impossibles
**empêchés** (409). Règles métier (raison de rejet obligatoire, poids obligatoire
à la collecte) présentes. ✅

| Constat | Sév. | Détail |
|---|---|---|
| **Concurrence / double-décision** | 🟠 | Deux opérateurs peuvent lire une demande `PENDING` puis la décider en parallèle. `assert_transition_allowed` protège au niveau applicatif mais sans verrou DB (`SELECT ... FOR UPDATE`) une course reste possible. Ajouter un verrou optimiste/pessimiste sur `decide`/`transition`. |
| **Note d'analyse échouée** | 🟠 | Si le provider échoue, la demande passe `AI_FAILED` — mais reste **décidable** par l'opérateur alors qu'elle n'a **aucun score** (file : NULLS LAST). Comportement OK, mais l'UI n'indique pas clairement « analyse indisponible ». |
| Frontière transactionnelle | 🟢 | Le service détient `commit` ; notification créée en transaction, `deliver` après commit (best-effort). Design propre. ✅ |
| `ForbiddenError` importé, jamais utilisé | 🟢 | service.py:36 — import mort. |

---

## 5. Operator Workflow — algorithme de priorité

**État : conforme et testé exactement.**

Ordre implémenté = `priority DESC → quality DESC → distance ASC → weight DESC →
FIFO (created_at ASC)`, avec `NULLS LAST` sur les clés IA (repository.py:58-64).
Un **test d'ordre exact déterministe** (7 demandes isolant chaque critère) le
verrouille. ✅

| Edge case | Couvert ? | Détail |
|---|---|---|
| Demande sans score IA (NULL) | ✅ | NULLS LAST → jamais en tête ; départagée par distance/poids/FIFO. |
| Hôtel sans coordonnées (distance NULL) | ✅ | Testé, distance NULL sort en dernier sur ce critère. |
| Égalité parfaite sur 4 clés | ✅ | FIFO tranche déterministiquement. |
| **Pagination + tri** | 🟠 | Le tri est en SQL (global) donc correct à travers les pages. ✅ Mais **pas d'index composite** (cf. §2) → coût en prod sur gros volume. |
| **Demandes terminales dans la file** | 🟠 | La file par défaut inclut `completed`/`rejected` (pas de filtre statut par défaut). L'opérateur voit du bruit terminal en tête si priorité haute. Envisager un défaut « file active » (exclure terminaux) côté opérateur. |

---

## 6. Hotel Workflow

**État : complet et simple.** Parcours : login → créer demande (quantité) →
voir statut/scores → notifications → photos (upload/suppression sur le détail).

| Constat | Sév. | Détail |
|---|---|---|
| Actions toutes nécessaires | 🟢 | Rien de superflu. Le formulaire de création ne demande que la quantité (photos séparées). ✅ |
| **Manque : annuler une demande** | 🟠 | Un hôtel ne peut pas **annuler** une demande qu'il a créée par erreur (avant décision opérateur). Ajouter un statut `CANCELLED` (transition `PENDING → CANCELLED` par l'hôtel). |
| **Manque : voir la raison de rejet clairement** | 🟢 | `rejection_reason` est dans le détail, mais pas mis en avant dans la liste hôtel. Amélioration UX mineure. |
| Multi-hôtels par manager | 🟢 | Géré (résolution explicite du `hotel_id` si plusieurs). ✅ Cohérent mais peu utilisé — vérifier que le besoin existe. |
| Simplification possible | 🟢 | Le détail (dialog) mélange infos + photos ; OK pour le MVP. |

---

## 7. Admin Dashboard

**État : refondu sur les Collection Requests, pertinent.**

KPIs actuels : total demandes, poids déclaré, méthane/énergie/CO₂ estimés,
qualité moyenne, taux d'acceptation, counts par statut, classement hôtels
(méthane), classement opérateurs. ✅ Tous **signifiants**.

| Statistique manquante suggérée | Sév. | Détail |
|---|---|---|
| **Délai moyen de traitement** | 🟠 | Temps `created → decided` et `accepted → completed`. KPI opérationnel clé pour un vrai produit (SLA). Données disponibles (`created_at`, `decided_at`, `completed_at`). |
| **Écart déclaré vs collecté** | 🟠 | `declared_weight_kg` vs `collected_weight_kg` agrégé → mesure la fiabilité des déclarations hôtel. Fort intérêt métier. |
| **Taux de rejet par hôtel** | 🟢 | Identifier les hôtels au tri de mauvaise qualité (RSE/incitation). |
| **Objectif quotidien 16,4 t** | 🟠 | Le brief métier fixe 16,4 t/jour ; le dashboard ne montre pas la **progression vers l'objectif du jour**. KPI très parlant pour la démo. |
| Santé système (AI/WS) | 🟢 | Présent (SystemStatusBar). ✅ |

---

## 8. Notifications

**État : ciblées, persistées, temps réel.** Bon socle.

Déclencheurs actuels (→ **hôtel** uniquement) : `accepted`, `rejected`,
`completed`. Ciblage par user via WebSocket + persistance DB. ✅

| Événement manquant | Destinataire | Sév. |
|---|---|---|
| **Nouvelle demande créée** | Opérateur/Admin | 🟠 | Aujourd'hui l'opérateur doit rafraîchir la file. Une notif « nouvelle demande à trier » fermerait la boucle. |
| **Demande en attente trop longtemps** (SLA) | Opérateur/Admin | 🟢 | Rappel si une demande stagne en `PENDING`. |
| `on_the_way` / `collected` | Hôtel | 🟢 | Volontairement exclus (bruit) — décision assumée, OK. |
| **Analyse IA échouée** | Admin | 🟢 | Signaler `AI_FAILED` pour intervention. |
| Notifications Admin (aucune) | Admin | 🟠 | L'admin ne reçoit **aucune** notification. Au minimum : incidents système / échecs d'analyse. |

---

## 9. Reports

**État : bon module, période + CSV + résumé.**

| Suggestion | Sév. | Détail |
|---|---|---|
| KPI « delivered vs declared » dans le résumé | 🟠 | Cf. §7 — ajouter l'écart poids déclaré/collecté. |
| **Export par hôtel / groupé** | 🟢 | Un export agrégé par hôtel (1 ligne/hôtel) en plus du détail par demande. |
| **Filtre période sur le CSV = created_at** | 🟢 | Le CSV filtre sur `created_at`. Pour un rapport de collecte, filtrer aussi sur `completed_at` serait utile (bilan des collectes *réalisées* sur la période). |
| PDF | 🟢 | Reporté sciemment (CSV suffit). OK. |
| Réutilisation | 🟠 | `ReportService` recalcule des agrégats proches de `RequestAnalyticsService`. Léger doublon (acceptable car périmètre différent : période vs live), à surveiller (DRY). |

---

## 10. Security

**État : fondations correctes**, mais **secrets par défaut = bloquant prod**.

| Constat | Sév. | Détail |
|---|---|---|
| **Secrets/défauts de dev** | 🔴 | `JWT_SECRET_KEY="change-me"`, DB `biocycle/biocycle`, admin `changeme123`. **Doivent** être surchargés en prod (env/secret manager) et le démarrage devrait **refuser** un secret par défaut en `ENVIRONMENT=production`. |
| RBAC | 🟢 | `require_role(...)` par endpoint ; rôle **relu depuis la DB** dans `get_current_user` (pas de confiance au claim JWT). ✅ Bon design. |
| Scoping / fuite d'existence | 🟢 | Les ressources d'autrui renvoient **404, pas 403** (pas de fuite). Appliqué partout (requests, photos, notifications). ✅ Excellent. |
| Auth WebSocket | 🟢 | JWT en query param (contrainte navigateur), validé avant `accept`. ✅ |
| Refresh token | 🟠 | Rotation ? Le refresh renvoie un access token ; vérifier qu'un refresh volé ne soit pas réutilisable indéfiniment (pas de liste de révocation). Acceptable MVP, à durcir. |
| Photos servies via JWT | 🟢 | Endpoint authentifié + contrôle d'accès, pas de statique public. ✅ |
| **Rate limiting absent** | 🟠 | Aucun throttling sur `/auth/login` → brute-force possible. Ajouter un rate limit en prod. |
| Upload : validation MIME | 🟢 | Allow-list + taille + quota, écriture atomique anti-traversal. ✅ Solide. Améliorable : vérifier les *magic bytes* réels (actuellement `content_type` déclaré). |
| CORS | 🟢 | Origines configurables. `allow_credentials=True` + origines explicites. ✅ |

---

## 11. Architecture (Clean / SOLID / DRY / patterns)

**État : très bonne conformité.** C'est le point fort du projet.

| Principe | Respect | Détail |
|---|---|---|
| Feature-based | ✅ | `features/<domain>/{models,schemas,repository,service,router}`. Cohérent partout. |
| Repository Pattern | ✅ | `BaseRepository` générique + repos spécialisés ; les repos ne committent pas (le service détient la transaction). |
| Service Layer | ✅ | Toute la logique métier dans les services ; routers fins. |
| Dependency Injection | ✅ | FastAPI `Depends` ; `RequestDataProvider` injecté (Adapter + DI) — **exemplaire**. |
| SOLID | ✅ (majoritaire) | DIP respecté (provider derrière interface). SRP bon. Léger accroc : `RequestService` fait beaucoup (création, scoring, décision, notif, scoping) → candidat à décomposition. |
| DRY | 🟠 | Duplication de la logique de **scoping manager** entre `RequestService`, `RequestAnalyticsService`, `ReportService` (`_manager_scope` répété 3×). À factoriser dans un helper partagé. |
| Dette technique | 🟠 | Requêtes **N+1** : `_owned_hotel_ids` re-requête les hôtels à chaque appel (parfois 2× dans un même `list`). À mémoïser/charger une fois. |

---

## 12. Code Quality

| Constat | Sév. | Détail |
|---|---|---|
| **Code mort frontend (bins)** | 🔴 | `pages/Bins.tsx`, `hooks/useBins.ts`, `services/bins.ts`, `components/bins/BinForm.tsx` — orphelins (plus routés). À **supprimer**. |
| **Seed obsolète** | 🟠 | `scripts/seed_demo_data.py` crée encore des Smart Bins. À nettoyer ou retirer. |
| Imports morts / ordre | 🟢 | `ForbiddenError` inutilisé (service.py) ; imports `Text/DateTime` non triés (models.py). Cosmétique. |
| Organisation dossiers | 🟢 | Claire et homogène. ✅ |
| Nommage | 🟢 | Cohérent après le refactor `scorer → data_provider`. ✅ |
| Duplication scoping | 🟠 | Cf. §11 (DRY). |
| Scalabilité future | 🟠 | WS manager **process-local** (OK MVP) ; multi-worker nécessitera un backplane Redis (déjà anticipé dans le commentaire). Provider abstrait = Firebase branchable proprement. ✅ |
| Aucun TODO/FIXME/HACK | 🟢 | Base propre, pas de marqueurs de dette laissés. ✅ |

---

## 13. Missing Features — synthèse

| Feature | Status | Missing | Priority |
|---|---|---|---|
| Collection Request domain | **Complete** | Statut `CANCELLED` (annulation hôtel) ; re-scoring `AI_FAILED` | High |
| Hotel workflow | **Needs Improvement** | Annulation de demande ; mise en avant raison de rejet | Medium |
| Operator workflow | **Complete** | Défaut « file active » (exclure terminaux) ; verrou anti-double-décision | High |
| Priority algorithm | **Complete** | Index composite (perf) | Low |
| Admin dashboard | **Needs Improvement** | Progression vs objectif 16,4 t ; délai moyen ; écart déclaré/collecté | Medium |
| Notifications | **Needs Improvement** | Notif opérateur « nouvelle demande » ; notifs admin (incidents) | Medium |
| Reports | **Complete** | Écart déclaré/collecté ; export agrégé par hôtel | Low |
| Security | **Needs Improvement** | Refuser secrets par défaut en prod ; rate-limit login ; magic-bytes upload | **High** |
| API surface | **Needs Improvement** | Démonter bins/collections/alerts ; retirer ancien `/analytics/export` | **High** |
| DB constraints | **Needs Improvement** | CHECK bornes ; index composite file | Medium |
| Dead code / debt | **Needs Improvement** | Supprimer frontend bins ; nettoyer seed ; import mort | Medium |
| DRY / N+1 | **Needs Improvement** | Factoriser `_manager_scope` ; corriger N+1 `_owned_hotel_ids` | Medium |

---

## Plan de remédiation proposé (après validation)

**Lot A — Production-readiness (🔴, à faire avant prod)**
1. Refuser au démarrage les secrets par défaut si `ENVIRONMENT=production`.
2. Démonter les routers obsolètes (`bins`, `collections`, `alerts`) + retirer `/analytics/export`.
3. Supprimer le code mort frontend bins + nettoyer le seed.

**Lot B — Robustesse métier (🟠)**
4. Statut `CANCELLED` + annulation hôtel.
5. Verrou anti-double-décision (`SELECT … FOR UPDATE`) sur decide/transition.
6. Défaut « file active » côté opérateur (exclure terminaux).
7. Factoriser le scoping (`_manager_scope`) + corriger le N+1 `_owned_hotel_ids`.

**Lot C — Valeur produit (🟠)**
8. KPI progression vs objectif 16,4 t/jour + délai moyen + écart déclaré/collecté (dashboard & reports).
9. Notification opérateur « nouvelle demande à trier ».

**Lot D — Durcissement (🟠, si le temps)**
10. Rate-limit login ; CHECK bornes DB ; index composite file ; magic-bytes upload.

> **Ordre recommandé :** A → B → C → D, puis **seulement ensuite** l'intégration
> Firebase, sur une couche métier validée et durcie.
