# Plan — Firebase Integration Layer (biodéchets par device)

> **Statut : IMPLÉMENTÉ (contre l'existant), pas encore activé en prod.**
> `FirebaseRealtimeReader` + `aggregator` sont construits ; le stub reste le
> provider actif (`FIREBASE_ENABLED=false`) jusqu'à ce que la clé soit
> régénérée et les règles RTDB verrouillées. Activer = mettre `FIREBASE_ENABLED=true`.

## 0. La donnée Firebase réelle (découverte 2026-07-14)

La structure réelle **diffère du plan initial**. Firebase RTDB contient un flux
de **vision par caméra**, pas une analyse déchets finie :

```
/AI_System = {
  camera, fps, resolution, objects_detected, time,
  detections: {
    "<pushId>": { prediction: "O" | "R", confidence: 0.0..1.0, time, camera },
    ...
  }
}
```

- `prediction: "O"` = organique, `"R"` = recyclable / non-organique.
- Le backend **agrège** ces détections (`integrations/firebase/aggregator.py`) :
  `purity = O/(O+R)×100`, contamination, quality (purity × avg confidence),
  confidence = moyenne ; méthane/énergie/CO₂/priorité dérivés de purity × la
  quantité déclarée (conteneurs × CONTAINER_WEIGHT_KG).
- **Un caméra = un hôtel** (mapping `hotel.firebase_device_id`) pour le mono-site.
- **Stratégie latest-snapshot** : à la création d'une demande, on lit l'état
  courant du nœud et on agrège les détections présentes.

> L'**abstraction est déjà en place** — le métier passe par l'interface
> `RequestDataProvider`, avec aujourd'hui le stub OU `FirebaseRealtimeReader`
> selon `FIREBASE_ENABLED`, injecté par DI. Aucun code métier ne change.

## 1. Contexte & changement de modèle

Révision de la source des données : elles **ne viennent plus d'une saisie
manuelle**. Chaque hôtel dispose d'un **Raspberry Pi** qui pousse ses **KPI**
dans **Firebase**. À la création d'une Collection Request, le backend récupère
**la dernière lecture Firebase** du device de l'hôtel et en fait un **snapshot**
dans PostgreSQL.

> ⚠️ **Le Raspberry pousse des KPI, JAMAIS d'images.** Les photos restent une
> chose distincte : l'hôtel les upload manuellement (feature photos déjà en
> place), indépendamment du Raspberry.

### 1.1. Ce que Firebase contient (contrat cible)

Le Raspberry (et/ou un traitement en amont côté hardware/IA de l'autre équipe)
écrit dans Firebase **deux catégories** de KPI :

- **Mesures capteurs brutes** : poids (kg), humidité, température, densité… (ce
  que le capteur relève physiquement).
- **Scores déjà calculés en amont** : qualité, pureté organique, contamination,
  méthane estimé, énergie, CO₂, priorité. **Ces scores sont calculés hors de
  notre backend** (côté device / équipe IA), pas par nous.

**Conséquence architecturale majeure : le backend ne calcule AUCUN score.** Il
est un **pur lecteur** de Firebase. Il n'y a **pas d'appel à une IA externe côté
backend** dans le modèle cible.

> 🔻 **Le stub IA (`backend/app/features/requests/ai_stub.py`) devient obsolète**
> une fois Firebase branché : les scores ne seront plus calculés localement mais
> lus depuis Firebase. Il est conservé aujourd'hui uniquement pour faire tourner
> la démo tant que Firebase n'est pas implémenté ; à retirer lors du branchement.

> ⚠️ Ce modèle réintroduit de l'IoT (Raspberry → Firebase), différent de l'IoT
> MQTT précédemment retiré. Firebase agit comme **buffer découplé** : le backend
> lit Firebase, il ne parle jamais directement au Raspberry.

## 2. Principe directeur : **lecture seule, jamais d'écriture**

La couche `integrations/firebase/` est **strictement read-only**. Le backend ne
crée, ne modifie et ne supprime **jamais** de données dans Firebase — c'est le
Raspberry Pi qui écrit. Toute écriture est un bug d'architecture. Le snapshot
vit uniquement dans PostgreSQL (source de vérité applicative).

```
  Raspberry Pi (hôtel)                Firebase (buffer)            Backend (nous)
  ───────────────────      push       ─────────────────   read-only   ───────────
  mesure poids/qualité  ───────────►  /devices/{id}/…   ◄───────────  snapshot → PG
                          (WRITE)                          (READ ONLY)
```

## 3. Structure de fichiers cible

```
backend/app/features/requests/
└── data_provider.py  # ALREADY EXISTS: RequestDataProvider (Protocol) + StubRequestDataProvider

backend/app/integrations/firebase/   # TO ADD when Firebase lands
├── __init__.py
├── reader.py         # FirebaseRealtimeReader — implements RequestDataProvider, read-only
├── schemas.py        # DeviceReading (DTO normalisé de ce que le Raspberry écrit)
└── config.py         # settings Firebase (URL, credentials) — via env, jamais commit
```

> L'interface s'appelle `RequestDataProvider` dans le code (pas `FirebaseReader`)
> pour ne pas coupler le nom du contrat à une techno. Le futur
> `FirebaseRealtimeReader` l'implémente.

Modèle : ajouter **`firebase_device_id`** (nullable, unique) sur `Hotel`
(migration dédiée). Mapping hôtel → device.

Snapshot : à la création, la Collection Request est renseignée **entièrement
depuis Firebase** — quantité **et** scores. On ajoutera :
- `source` (`manual` | `firebase`) : provenance de la donnée,
- `firebase_reading_at` : horodatage de la lecture d'origine,
- `firebase_raw` (JSONB) : la lecture brute complète, pour la traçabilité.

Les colonnes `ai_*` existantes (qualité, méthane, priorité…) sont désormais
**remplies depuis Firebase**, plus par le scorer local.

## 4. Interface (le point de couture)

On dépend d'une **interface**, pas de Firebase directement — le service reste
testable et le vrai client est branchable sans toucher au métier. Le
`DeviceReading` porte **KPI bruts + scores** (pas d'images).

```python
class FirebaseReader(Protocol):
    async def latest_reading(self, device_id: str) -> DeviceReading | None: ...

class DeviceReading(BaseSchema):
    device_id: str
    recorded_at: datetime
    # --- KPI bruts capteurs ---
    weight_kg: float
    humidity: float | None = None
    temperature_c: float | None = None
    density: float | None = None
    # --- Scores déjà calculés EN AMONT (pas par notre backend) ---
    quality_score: float | None = None
    organic_purity: float | None = None
    contamination: float | None = None
    estimated_methane_m3: float | None = None
    estimated_energy_kwh: float | None = None
    estimated_co2_kg: float | None = None
    priority_score: float | None = None
    # champs exacts À FIGER avec l'équipe hardware/IA (voir §6.1)
```

- **`StubFirebaseReader`** : renvoie une lecture déterministe (hash du device_id),
  bruts + scores plausibles. Utilisé en dev/tests jusqu'à livraison du contrat.
  Il **remplace** le rôle de l'actuel `ai_stub.py`.
- **`FirebaseRESTReader`** : lit `GET {FIREBASE_DB_URL}/devices/{device_id}/latest.json`
  (Realtime DB) ou un doc Firestore. **Aucune méthode d'écriture exposée.**

## 5. Flux à la création d'une Collection Request

```
Hotel crée une demande
        │
        ▼
  hotel.firebase_device_id renseigné ?
        │
   ┌────┴─────┐
   │ oui      │ non
   ▼          ▼
FirebaseReader     Fallback : saisie manuelle
.latest_reading()  (declared_weight_kg du body ; scores IA vides)
   │
   ├─ lecture trouvée → snapshot COMPLET depuis Firebase :
   │     • declared_weight_kg = reading.weight_kg
   │     • ai_quality_score / ai_estimated_methane_m3 / ... = reading.<scores>
   │     • source="firebase", firebase_reading_at, firebase_raw
   │
   └─ rien / erreur  → selon politique (voir §6)
        │
        ▼
  suite normale : distance, file opérateur…
  (PAS de scoring local : les scores viennent de Firebase)
```

## 6. Décisions à figer avant implémentation

1. **Contrat de données Raspberry** : chemin exact + schéma du document Firebase
   — quels champs bruts **et** quels scores, avec leurs noms/unités (ex.
   `/devices/{id}/latest = {weight_kg, humidity, quality_score, methane_m3, …}`).
   **Bloquant.**
2. **Firebase indisponible / device muet** : bloquer la création (erreur) OU
   retomber sur la saisie manuelle ? (recommandé : fallback manuel, non bloquant).
3. **Fraîcheur** : rejeter une lecture trop ancienne (seuil configurable) ?
4. **Auth Firebase** : clé de service (Firestore/Realtime DB REST) — stockée en
   env/secret, **jamais** commitée. Realtime DB vs Firestore ?
5. **Manuel vs Firebase** : le champ manuel disparaît-il du formulaire hôtel une
   fois Firebase en place, ou reste-t-il en fallback ? (impacte l'UI).

**Résolu (2026-07-08) :**
- ✅ **Le Raspberry pousse des KPI, pas d'images.** Les photos restent un upload
  manuel séparé.
- ✅ **Firebase contient bruts capteurs ET scores calculés en amont.** Le backend
  ne calcule aucun score → **pas d'IA côté backend**, `ai_stub.py` à retirer au
  branchement.

## 7. Tests prévus

- `StubFirebaseReader` déterministe (unitaire).
- Création avec device mappé → snapshot correct : **quantité ET scores** repris
  de Firebase (weight, quality, methane…), source/timestamp/raw renseignés.
- Création sans device → fallback manuel inchangé (scores vides).
- Lecture Firebase absente/en erreur → politique §6.2 respectée (pas de 500).
- **Garantie read-only** : le client n'expose aucune méthode d'écriture (test
  d'interface / revue).
- **Non-régression scoring** : vérifier que le backend n'appelle plus le scorer
  local quand une lecture Firebase est présente.

## 8. Effort estimé

~1 à 1,5 jour une fois le contrat Firebase (§6.1) figé : migration
`firebase_device_id` + colonnes de provenance, interface + stub + client REST,
branchement dans `RequestService.create`, tests. Sans le contrat, on ne code que
l'interface + le stub (~2 h) pour débloquer le reste.
